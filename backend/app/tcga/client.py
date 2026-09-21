import json
import re
from pathlib import Path
import pandas as pd
from app.config import CACHE, GDC
from app.io import request_json, download, write_json

class InsufficientData(ValueError):
    pass

class AmbiguousCancer(ValueError):
    pass

def projects():
    path = CACHE / 'projects.json'
    # Save the actual project response in each run; refreshing here keeps resolution current.
    try:
        rows = request_json(GDC + '/projects', {'size': 500, 'fields': 'project_id,name,primary_site,disease_type,summary.case_count'})['data']['hits']
        rows = [r for r in rows if r['project_id'].startswith('TCGA-')]
        write_json(path, rows)
        return rows
    except Exception:
        if path.exists():
            return json.loads(path.read_text())
        raise

def resolve(query, catalog):
    query = query.strip().lower()
    aliases = {'breast cancer': 'BRCA', 'lung adenocarcinoma': 'LUAD', 'prostate cancer': 'PRAD',
               'lung squamous cell carcinoma': 'LUSC', 'colon cancer': 'COAD', 'ovarian cancer': 'OV',
               'glioblastoma': 'GBM', 'pancreatic cancer': 'PAAD', 'bladder cancer': 'BLCA',
               'liver cancer': 'LIHC', 'melanoma': 'SKCM', 'thyroid cancer': 'THCA'}
    code = aliases.get(query, query).upper()
    for row in catalog:
        if code in [row['project_id'], row['project_id'].replace('TCGA-', '')]:
            return row
    tokens = set(re.findall(r'[a-z]+', query)) - {'cancer', 'tumor', 'carcinoma', 'of', 'the'}
    matches = []
    for row in catalog:
        text = ' '.join([row['name']] + row.get('primary_site', []) + row.get('disease_type', [])).lower()
        if tokens and all(token in text for token in tokens):
            matches.append(row)
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise AmbiguousCancer('Choose a more specific cancer or TCGA code: ' + ', '.join(r['project_id'] + ' (' + r['name'] + ')' for r in matches))
    raise ValueError('No matching TCGA project. Try a specific cancer name or TCGA project code.')

def classify(hit):
    cases = hit.get('cases', [])
    if len(cases) != 1:
        return None
    samples = cases[0].get('samples', [])
    if len(samples) != 1 or samples[0].get('sample_type') not in ['Primary Tumor', 'Solid Tissue Normal']:
        return None
    return dict(file_id=hit['file_id'], file_name=hit['file_name'], md5sum=hit['md5sum'],
                case_id=cases[0]['case_id'], sample_id=samples[0]['sample_id'],
                sample_type=samples[0]['sample_type'])

def discover(project_id):
    filters = {'op': 'and', 'content': [
        {'op': '=', 'content': {'field': 'cases.project.project_id', 'value': project_id}},
        {'op': '=', 'content': {'field': 'data_type', 'value': 'Gene Expression Quantification'}},
        {'op': '=', 'content': {'field': 'analysis.workflow_type', 'value': 'STAR - Counts'}},
        {'op': '=', 'content': {'field': 'access', 'value': 'open'}}]}
    rows = []
    offset = 0
    while True:
        result = request_json(GDC + '/files', {'filters': json.dumps(filters), 'size': 1000, 'from': offset,
            'fields': 'file_id,file_name,md5sum,cases.case_id,cases.samples.sample_id,cases.samples.sample_type', 'sort': 'file_id:asc'})['data']
        rows.extend(result['hits'])
        offset += len(result['hits'])
        if offset >= result['pagination']['total'] or not result['hits']:
            break
    return rows

def select_samples(hits, limit):
    classified = [r for r in (classify(h) for h in hits) if r]
    selected, seen = [], set()
    # Independent groups: normal patients are reserved before selecting tumor patients.
    for kind in ['Solid Tissue Normal', 'Primary Tumor']:
        count = 0
        for row in sorted(classified, key=lambda r: (r['case_id'], r['sample_id'], r['file_id'])):
            if row['sample_type'] == kind and row['case_id'] not in seen:
                selected.append(row)
                seen.add(row['case_id'])
                count += 1
                if count >= limit:
                    break
        if count < 3:
            raise InsufficientData('Insufficient data: fewer than 3 independent ' + kind + ' samples.')
    return selected

def parse_counts(path):
    frame = pd.read_csv(path, sep='\t', comment='#')
    required = {'gene_id', 'gene_name', 'unstranded'}
    if not required.issubset(frame.columns):
        raise ValueError('Not a GDC STAR counts file: ' + str(path))
    frame = frame[frame.gene_id.str.startswith('ENSG')].copy()
    frame['gene_id'] = frame.gene_id.str.replace(r'\.\d+', '', regex=True)
    frame['unstranded'] = pd.to_numeric(frame.unstranded, errors='raise')
    if frame.gene_id.duplicated().any() or (frame.unstranded < 0).any():
        raise ValueError('Invalid gene IDs or negative counts')
    return frame.set_index('gene_id')[['gene_name', 'unstranded']]

def retrieve(samples, progress):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def fetch(sample):
        path = CACHE / (sample['file_id'] + '.tsv')
        source = download(GDC + '/data/' + sample['file_id'], path, sample['md5sum'])
        return parse_counts(path), dict(source, **sample)
    frames, sources = [None] * len(samples), [None] * len(samples)
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix='gdc-download') as pool:
        futures = {pool.submit(fetch, sample): i for i, sample in enumerate(samples)}
        for completed, future in enumerate(as_completed(futures), 1):
            index = futures[future]
            frames[index], sources[index] = future.result()
            progress('retrieving', f'Retrieved {completed}/{len(samples)} verified STAR count files',
                     downloaded=completed, selected_samples=len(samples))
    annotations = frames[0]['gene_name']
    counts = [frame.unstranded.rename(sample['sample_id']) for frame, sample in zip(frames, samples)]
    matrix = pd.concat(counts, axis=1, join='inner')
    if matrix.empty or matrix.isna().any().any():
        raise InsufficientData('Insufficient data: incompatible expression files')
    return matrix, annotations.reindex(matrix.index), sources
