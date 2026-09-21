import importlib.metadata
import json
import logging
import platform
import traceback
from pathlib import Path
import pandas as pd
from app.config import RUNS, VERSION, GDC
from app.io import write_json, now, request_json, digest
from app.tcga.client import projects, resolve, discover, select_samples, retrieve, InsufficientData
from app.preprocessing.normalize import normalize
from app.differential.analyze import differential
from app.signature.build import build, match_symbols
from app.perturbations.lincs import load
from app.scoring.reversal import Scorer
from app.ranking.aggregate import rank
from app.robustness.compare import compare_rankings

LIMITATIONS = [
    'Exploratory Welch tests on log2(CPM+1), not a count-model differential expression analysis; no covariate or batch adjustment.',
    'Deterministically capped, independent patient groups are not the full TCGA cohort and may not represent cancer subtypes.',
    'Library-size CPM does not correct RNA composition bias. Normal tissue may differ in cellular composition.',
    'LINCS GMTs are thresholded directional gene sets, not full L1000 expression matrices. Missing genes have zero contribution, not measured zero effect.',
    'Exact uppercase gene-symbol matching only; outdated aliases can reduce coverage. Ambiguous duplicate TCGA symbols are excluded.',
    'Dose units and replicate counts are not supplied by this GMT export. Contexts are cell/time/dose-label groups, not independent biological replicates.',
    'Equal-weight median across contexts summarizes heterogeneous experiments; tissue relevance and pharmacological feasibility are not established.',
    'Gene-label permutations are an exploratory null and do not preserve gene correlation or correct selection bias from overlap eligibility.',
    'Clinical efficacy, safety, dosage, patient benefit, and literature validation are not evaluated.'
]

def execute(run_id, parameters, replay=None):
    folder = RUNS / run_id
    state_path = folder / 'state.json'
    state = json.loads(state_path.read_text())
    def progress(stage, message, **values):
        state.update(status='running', stage=stage, message=message, updated_at=now(), **values)
        state.setdefault('events', []).append(dict(at=now(), stage=stage, message=message))
        write_json(state_path, state)
        logging.getLogger('iris').info('%s %s %s', run_id, stage, message)
    audit = dict(id=run_id, created_at=state['created_at'], input=parameters['cancer'], parameters=parameters,
                 software_version=VERSION, python=platform.python_version(), limitations=LIMITATIONS,
                 dependencies={name: importlib.metadata.version(name) for name in ['numpy', 'pandas', 'scipy', 'fastapi', 'httpx']})
    source_root = Path(__file__).resolve().parents[1]
    audit['source_checksums'] = {str(p.relative_to(source_root)): digest(p) for p in source_root.rglob('*.py')}
    try:
        progress('resolving', 'Resolving cancer against the public TCGA project catalog')
        if replay:
            project = replay['project']
            samples = replay['discovery']['selected_samples']
            available_files = replay['discovery']['available_files']
            audit['gdc_release'] = replay['gdc_release']
            audit['replay_of'] = replay['id']
            audit['replay_policy'] = 'Pinned sample manifest and source checksums; no cohort rediscovery'
        else:
            project = resolve(parameters['cancer'], projects())
            audit['gdc_release'] = request_json(GDC + '/status')
            progress('retrieving', 'Discovering open-access STAR counts', project=project)
            hits = discover(project['project_id'])
            available_files = len(hits)
            samples = select_samples(hits, parameters['samples_per_group'])
        audit['project'] = project
        progress('retrieving', 'Retrieving selected independent patient samples', project=project)
        audit['discovery'] = dict(available_files=available_files, selected_samples=samples,
                                  policy='Normal first; unique case across both groups; sort case, sample, file UUID; cap each group')
        write_json(folder / 'analysis_metadata.json', audit)
        counts, annotations, sources = retrieve(samples, progress)
        if replay:
            expected = {r['file_id']: r['sha256'] for r in replay['gdc_sources']}
            if any(expected.get(r['file_id']) != r['sha256'] for r in sources):
                raise ValueError('Replay aborted: a GDC file differs from the pinned snapshot')
        audit['gdc_sources'] = sources
        counts.to_csv(folder / 'raw_counts.csv.gz', compression='gzip')
        progress('preprocessing', 'Filtering low-expression genes and calculating library-size CPM')
        cpm, logcpm, sizes = normalize(counts, parameters['min_cpm'], parameters['min_fraction'])
        cpm.to_csv(folder / 'normalized_cpm.csv.gz', compression='gzip')
        audit['library_sizes'] = sizes.to_dict()
        progress('differential', 'Calculating effect sizes, Welch tests, and Benjamini–Hochberg FDR', genes_tested=len(cpm))
        de = differential(cpm, logcpm, annotations, samples)
        de.to_csv(folder / 'differential_expression.csv', index=False)
        signature = build(de, parameters['fdr'], parameters['effect'], parameters['max_genes'])
        signature.to_csv(folder / 'signature.csv', index=False)
        if not (signature.direction == 'up').any() or not (signature.direction == 'down').any():
            raise InsufficientData('Insufficient data: thresholds did not produce both UP and DOWN genes. Inspect differential_expression.csv or change thresholds.')
        records, lincs_audit = load(progress)
        if replay:
            expected = {r['dataset']: r['sha256'] for r in replay['lincs']['sources']}
            if any(expected.get(r['dataset']) != r['sha256'] for r in lincs_audit['sources']):
                raise ValueError('Replay aborted: LINCS differs from the pinned snapshot; restore original cache files')
        audit['lincs'] = lincs_audit
        scorer = Scorer(records, match_symbols(de).gene)
        audit['scoring'] = dict(equation='S_j = sum_g(log2FC_g * d_jg) / sum_g(abs(log2FC_g)); g in signature intersect tested LINCS universe',
            drug_direction={'up': 1, 'down': -1, 'absent': 0}, gene_universe=scorer.genes,
            aggregation='Mean within compound/cell/time/dose label, median across contexts', negative_means='reversal',
            min_overlap=parameters['min_overlap'], requires_overlap_in_both_arms=True)
        progress('scoring', f'Scoring {len(records):,} paired chemical signatures; running gene-label permutations', perturbations=len(records))
        scored = scorer.score(signature, parameters['min_overlap'], parameters['permutations'], parameters['seed'])
        candidates = rank(records, scored)
        if not candidates:
            raise InsufficientData('Insufficient data: no perturbations met gene-overlap requirements.')
        signature_records = json.loads(signature.to_json(orient='records'))
        progress('robustness', 'Recalculating rankings under relaxed, stringent, and multi-context configurations')
        configs = {
            'baseline': dict(fdr=parameters['fdr'], effect=parameters['effect'], max_genes=parameters['max_genes']),
            'relaxed': dict(fdr=min(.25, parameters['fdr'] * 2), effect=parameters['effect'] * .5, max_genes=parameters['max_genes'] * 2),
            'stringent': dict(fdr=parameters['fdr'] * .2, effect=parameters['effect'] * 1.5, max_genes=max(5, parameters['max_genes'] // 2)),
            'multi-context': dict(fdr=parameters['fdr'], effect=parameters['effect'], max_genes=parameters['max_genes'], min_contexts=2)}
        rankings, config_status = {'baseline': candidates}, {}
        for name, config in configs.items():
            try:
                sig = build(de, config['fdr'], config['effect'], config['max_genes'])
                if name != 'baseline':
                    rankings[name] = rank(records, scorer.score(sig, parameters['min_overlap']), config.get('min_contexts', 1))
                config_status[name] = dict(parameters=config, signature_genes=len(sig), candidates=len(rankings[name]),
                    status='evaluated' if rankings[name] else 'Insufficient data')
                sig.to_csv(folder / ('signature_' + name + '.csv'), index=False)
            except InsufficientData as exc:
                config_status[name] = dict(parameters=config, status='Insufficient data', reason=str(exc))
        robustness = dict(**compare_rankings(rankings, parameters['top_k']), configurations=config_status,
                          rankings={key: [{k: c[k] for k in ['compound', 'rank', 'score']} for c in value] for key, value in rankings.items()})
        naive = sorted(candidates, key=lambda r: (-r['naive_overlap'], r['compound']))
        naive = [dict(r, rank=i + 1) for i, r in enumerate(naive)]
        validation = dict(permutations=parameters['permutations'], seed=parameters['seed'],
            null='Shuffle signed cancer weights across tested, uniquely mapped genes in the LINCS union; retain observed eligible contexts.',
            baseline=compare_rankings({'reversal': candidates, 'naive-overlap': naive}, parameters['top_k'])['comparisons'],
            known_compound_validation='Not evaluated', clinical_validation='Not evaluated',
            minimum_attainable_p=1 / (parameters['permutations'] + 1))
        progress('exporting', 'Saving rankings, context evidence, robustness results, and reproducibility audit')
        evidence = []
        by_term = {r['term']: r for r in records}
        for candidate in candidates:
            # Context-level evidence is stored for all eligible candidate signatures.
            for context in candidate['context_details']:
                for term in context['terms']:
                    evidence.extend(dict(row, compound=candidate['compound']) for row in scorer.gene_evidence(by_term[term], signature, scored['denominator']))
        pd.DataFrame(evidence).to_csv(folder / 'gene_level_scores.csv', index=False)
        simple = [{k: v for k, v in r.items() if k != 'context_details'} for r in candidates]
        pd.DataFrame(simple).to_csv(folder / 'candidate_rankings.csv', index=False)
        pd.DataFrame([{**{k: v for k, v in r.items() if k != 'ranks'}, **r['ranks']} for r in robustness['stability']]).to_csv(folder / 'robustness.csv', index=False)
        pd.DataFrame(columns=['analysis_a', 'analysis_b', 'top_k', 'overlap', 'jaccard', 'rank_correlation']).to_csv(folder / 'cross_cancer.csv', index=False)
        result = dict(id=run_id, status='complete', project=project, parameters=parameters,
            summary=dict(tumor_samples=sum(r['sample_type'] == 'Primary Tumor' for r in samples),
                normal_samples=sum(r['sample_type'] == 'Solid Tissue Normal' for r in samples), available_files=available_files,
                genes_tested=len(de), significant_genes=int(((de.fdr <= parameters['fdr']) & (de.log2fc.abs() >= parameters['effect'])).sum()),
                signature_genes=len(signature), up_genes=int((signature.direction == 'up').sum()), down_genes=int((signature.direction == 'down').sum()),
                mapped_signature_genes=scored['mapped_signature_genes'], perturbations=len(records), eligible_perturbations=int(scored['eligible'].sum()), compounds=len(candidates)),
            signature=signature_records, candidates=candidates, robustness=robustness, validation=validation, limitations=LIMITATIONS,
            artifacts=[p.name for p in folder.iterdir() if p.suffix in ['.csv', '.gz']] + ['analysis_metadata.json', 'results.json'],
            cross_cancer_status='Not evaluated until at least two completed analyses are compared')
        write_json(folder / 'results.json', result)
        audit.update(completed_at=now(), summary=result['summary'], signature=signature_records,
                     robustness_configurations=config_status, validation=validation,
                     artifacts={p.name: digest(p) for p in folder.iterdir() if p.name not in ['analysis_metadata.json', 'state.json']})
        write_json(folder / 'analysis_metadata.json', audit)
        progress('complete', 'Analysis complete; all displayed results calculated from public data')
        state.update(status='complete', completed_at=now())
        write_json(state_path, state)
    except Exception as exc:
        logging.getLogger('iris').exception('Analysis %s failed', run_id)
        audit.update(failed_at=now(), error=str(exc), traceback=traceback.format_exc())
        write_json(folder / 'analysis_metadata.json', audit)
        state.update(status='insufficient_data' if isinstance(exc, InsufficientData) else 'failed', error=str(exc), message=str(exc), updated_at=now())
        write_json(state_path, state)
