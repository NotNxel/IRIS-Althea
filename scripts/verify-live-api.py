"""Read-only verification of a completed analysis and every advertised download."""
import argparse
import codecs
import csv
import hashlib
import json
import sys
import zlib
from pathlib import Path
from urllib.parse import quote

import httpx


def text_lines(chunks):
    """Decode CSV one line at a time without retaining the download body."""
    decoder = codecs.getincrementaldecoder('utf-8')()
    pending = ''
    for chunk in chunks:
        pending += decoder.decode(chunk)
        lines = pending.split('\n')
        pending = lines.pop()
        yield from (line + '\n' for line in lines)
    pending += decoder.decode(b'', final=True)
    if pending:
        yield pending


def gunzip_chunks(chunks):
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    for chunk in chunks:
        yield decoder.decompress(chunk)
    yield decoder.flush()
    assert decoder.eof, 'Truncated gzip download'


def inspect_download(client, base, path, checks, checksum=None, required_columns=None,
                     expected_rows=None, minimum_rows=None, sample_ids=None):
    digest = hashlib.sha256()
    length = 0
    with client.stream('GET', base + path) as response:
        response.raise_for_status()

        def chunks():
            nonlocal length
            for chunk in response.iter_bytes(chunk_size=65536):
                digest.update(chunk)
                length += len(chunk)
                yield chunk

        record = {'path': path, 'status': response.status_code}
        if path.endswith(('.csv', '.csv.gz')):
            data = gunzip_chunks(chunks()) if path.endswith('.gz') else chunks()
            reader = csv.reader(text_lines(data))
            header = next(reader, None)
            assert header, 'CSV header missing: ' + path
            if required_columns:
                assert set(required_columns).issubset(header), 'CSV columns missing: ' + path
            if sample_ids is not None:
                assert header[1:] == sample_ids, 'Sample columns differ from audit: ' + path
            rows = 0
            for row in reader:
                assert len(row) == len(header), 'Malformed CSV row: ' + path
                rows += 1
            if expected_rows is not None:
                assert rows == expected_rows, f'CSV row count differs: {path}: {rows} != {expected_rows}'
            if minimum_rows is not None:
                assert rows >= minimum_rows, 'Too few CSV rows: ' + path
            record.update(rows=rows, columns=len(header))
        else:
            for _ in chunks():
                pass
        assert length > 0, 'Empty artifact: ' + path
        if response.headers.get('content-length') is not None:
            assert length == int(response.headers['content-length']), 'Content length differs: ' + path
        if checksum:
            assert digest.hexdigest() == checksum, 'Artifact checksum differs: ' + path
        record.update(bytes=length, checksum_verified=bool(checksum))
        checks.append(record)


def verify(args, checks):
    base = args.base_url.rstrip('/')
    analysis_path = '/analyses/' + quote(args.analysis_id, safe='')
    # Identity encoding makes Content-Length and artifact hashes refer to file bytes.
    with httpx.Client(timeout=120, headers={'Accept-Encoding': 'identity'}) as client:
        def get(path, expected_status=200):
            response = client.get(base + path)
            assert response.status_code == expected_status, f'{path}: HTTP {response.status_code}, expected {expected_status}'
            checks.append({'path': path, 'status': response.status_code})
            return response

        assert get('/health').json()['status'] == 'ok'
        assert get(analysis_path).json()['status'] == 'complete'
        result = get(analysis_path + '/results').json()
        assert result['id'] == args.analysis_id and result['status'] == 'complete'
        assert get(analysis_path + '/robustness').json() == result['robustness']
        assert result['candidates'], 'Analysis has no candidates'
        compound = result['candidates'][0]['compound']
        detail = get(analysis_path + '/candidates/' + quote(compound, safe='')).json()
        assert detail['compound'] == compound and detail['gene_evidence']
        assert detail['score'] == result['candidates'][0]['score']
        metadata_response = get(analysis_path + '/artifacts/analysis_metadata.json')
        metadata = metadata_response.json()
        assert metadata['summary'] == result['summary']
        assert metadata['id'] == args.analysis_id
        assert set(metadata['artifacts']).issubset(result['artifacts'])

        summary = result['summary']
        csv_rules = {
            'signature.csv': (['gene_id', 'gene', 'direction', 'log2fc', 'fdr'], summary['signature_genes']),
            'differential_expression.csv': (['gene_id', 'gene', 'log2fc', 'pvalue', 'fdr'], summary['genes_tested']),
            'candidate_rankings.csv': (['compound', 'rank', 'score', 'contexts', 'permutation_fdr'], summary['compounds']),
            'robustness.csv': (['compound', 'configurations_present', 'top_k_frequency', 'mean_rank', 'rank_sd'], len(result['robustness']['stability'])),
            'gene_level_scores.csv': (['gene', 'cancer_log2fc', 'cancer_direction', 'drug_direction', 'contribution', 'opposing', 'term', 'compound'], None),
            'cross_cancer.csv': (['analysis_a', 'analysis_b', 'top_k', 'overlap', 'jaccard', 'rank_correlation'], 0),
            'normalized_cpm.csv.gz': (None, summary['genes_tested']),
        }
        for name, config in result['robustness']['configurations'].items():
            csv_rules['signature_' + name + '.csv'] = (['gene_id', 'gene', 'direction', 'log2fc', 'fdr'], config.get('signature_genes'))
        samples = [row['sample_id'] for row in metadata['discovery']['selected_samples']]
        assert len(samples) == summary['tumor_samples'] + summary['normal_samples']
        assert len(result['artifacts']) == len(set(result['artifacts'])), 'Duplicate advertised artifacts'
        for name in sorted(result['artifacts']):
            columns, rows = csv_rules.get(name, (None, None))
            checksum = metadata['artifacts'].get(name)
            if name == 'analysis_metadata.json':
                checksum = hashlib.sha256(metadata_response.content).hexdigest()
            else:
                assert checksum, 'Advertised artifact has no audit checksum: ' + name
            minimum = None
            if name == 'raw_counts.csv.gz':
                minimum = summary['genes_tested']
            elif name == 'gene_level_scores.csv':
                minimum = sum(c['signatures'] for c in result['candidates']) * result['parameters']['min_overlap']
            inspect_download(client, base, analysis_path + '/artifacts/' + quote(name, safe=''), checks,
                             checksum=checksum, required_columns=columns, expected_rows=rows,
                             minimum_rows=minimum, sample_ids=samples if name.endswith('.csv.gz') else None)

        missing = '00000000-0000-0000-0000-000000000000'
        get('/analyses/' + missing, 404)
        get('/analyses/' + missing + '/results', 404)
        get('/analyses/not-a-uuid', 404)
        get(analysis_path + '/candidates/__iris_missing_compound__', 404)
        get(analysis_path + '/artifacts/state.json', 404)
        get(analysis_path + '/artifacts/missing.csv', 404)
        if args.comparison_id:
            inspect_download(client, base, '/comparisons/' + quote(args.comparison_id, safe='') + '/cross_cancer.csv', checks,
                             required_columns=['a', 'b', 'top_k', 'overlap', 'jaccard', 'rank_correlation', 'common_candidates'], minimum_rows=1)
            get('/comparisons/' + missing + '/cross_cancer.csv', 404)
        return len(result['artifacts'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis_id')
    parser.add_argument('--comparison-id')
    parser.add_argument('--base-url', default='http://127.0.0.1:8000/api/v1')
    parser.add_argument('--output', type=Path, help='Optional path for the JSON report; otherwise only stdout is written')
    args = parser.parse_args()
    checks = []
    record = {'analysis_id': args.analysis_id, 'comparison_id': args.comparison_id,
              'base_url': args.base_url.rstrip('/'), 'checks': checks}
    try:
        record['artifacts_verified'] = verify(args, checks)
        record['status'] = 'passed'
    except Exception as exc:
        record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    record['checks_passed'] = len(checks)
    output = json.dumps(record, separators=(',', ':'))
    if args.output:
        args.output.write_text(output + '\n')
    print(output)
    return 0 if record['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
