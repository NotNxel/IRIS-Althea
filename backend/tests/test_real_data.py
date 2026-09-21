"""No synthetic biological claims: checks a completed public-data run and its actual artifacts."""
import json
import os
from pathlib import Path
import pandas as pd
import pytest
from app.io import digest

@pytest.mark.integration
def test_saved_real_data_run():
    folder=os.environ.get('IRIS_REAL_RUN')
    if not folder:
        pytest.skip('Set IRIS_REAL_RUN to a completed real-data analysis directory')
    path=Path(folder)
    result=json.loads((path/'results.json').read_text())
    audit=json.loads((path/'analysis_metadata.json').read_text())
    assert result['status']=='complete'
    assert audit['project']['project_id'].startswith('TCGA-')
    samples=audit['discovery']['selected_samples']
    assert len({s['case_id'] for s in samples})==len(samples)
    assert result['summary']['tumor_samples']>=3 and result['summary']['normal_samples']>=3
    for source in audit['gdc_sources']:
        assert source['url'].startswith('https://api.gdc.cancer.gov/data/')
        assert len(source['sha256'])==64 and source['expected_md5']
    assert len(audit['lincs']['sources'])==2 and audit['lincs']['parsed_terms']>0
    for name,checksum in audit['artifacts'].items():
        assert digest(path/name)==checksum
    signature=pd.read_csv(path/'signature.csv')
    assert set(signature.direction)=={'up','down'}
    differential = pd.read_csv(path/'differential_expression.csv').set_index('gene_id')
    assert set(signature.gene).issubset(set(differential.gene.str.strip().str.upper()))
    for row in signature.itertuples():
        assert row.gene == differential.loc[row.gene_id, 'gene'].strip().upper()
        assert row.log2fc == pytest.approx(differential.loc[row.gene_id, 'log2fc'])
    ranking=pd.read_csv(path/'candidate_rankings.csv')
    assert ranking.score.is_monotonic_increasing
    evidence=pd.read_csv(path/'gene_level_scores.csv')
    assert evidence.contribution.between(-1,1).all()
    # Independently reconstruct every compound's aggregate from exported gene contributions.
    per_term=evidence.groupby(['compound','term']).contribution.sum()
    for candidate in result['candidates']:
        contexts=[]
        for context in candidate['context_details']:
            mean=sum(per_term.loc[candidate['compound'],t] for t in context['terms'])/len(context['terms'])
            assert mean==pytest.approx(context['score'],abs=1e-10)
            contexts.append(mean)
        assert float(pd.Series(contexts).median())==pytest.approx(candidate['score'],abs=1e-10)
    assert result['robustness']['configurations']['baseline']['status']=='evaluated'
