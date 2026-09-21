import numpy as np
import pandas as pd
import pytest
from app.tcga.client import resolve, classify, select_samples, parse_counts, InsufficientData, AmbiguousCancer
from app.preprocessing.normalize import normalize
from app.differential.analyze import bh, differential
from app.signature.build import build, match_symbols
from app.perturbations.lincs import parse_gmt, metadata
from app.scoring.reversal import Scorer
from app.ranking.aggregate import rank
from app.robustness.compare import compare_rankings
from app.cross_cancer.compare import compare

CATALOG = [dict(project_id='TCGA-BRCA', name='Breast Invasive Carcinoma', primary_site=['Breast']),
           dict(project_id='TCGA-LUAD', name='Lung Adenocarcinoma', primary_site=['Lung']),
           dict(project_id='TCGA-LUSC', name='Lung Squamous Cell Carcinoma', primary_site=['Lung']),
           dict(project_id='TCGA-PRAD', name='Prostate Adenocarcinoma', primary_site=['Prostate'])]

@pytest.mark.parametrize('query,expected',[('breast cancer','BRCA'),('lung adenocarcinoma','LUAD'),('Prostate cancer','PRAD'),('TCGA-BRCA','BRCA'),('breast','BRCA')])
def test_resolver(query, expected):
    assert resolve(query,CATALOG)['project_id']=='TCGA-'+expected

def test_ambiguous_resolution():
    with pytest.raises(AmbiguousCancer): resolve('lung cancer', CATALOG)
    with pytest.raises(ValueError): resolve('not a disease', CATALOG)

def hit(case, kind, number=0):
    return dict(file_id=f'f{case}{number}', file_name='counts.tsv', md5sum='abc', cases=[dict(case_id=case,samples=[dict(sample_id=f's{case}{kind}',sample_type=kind)])])

def test_metadata_and_independence():
    assert classify(hit('x','Metastatic')) is None
    ambiguous=hit('x','Primary Tumor'); ambiguous['cases'][0]['samples'].append(dict(sample_id='y',sample_type='Solid Tissue Normal'))
    assert classify(ambiguous) is None
    hits=[hit(str(i),'Solid Tissue Normal') for i in range(3)]+[hit(str(i),'Primary Tumor') for i in range(8)]
    selected=select_samples(hits,3)
    assert len(selected)==6 and len({r['case_id'] for r in selected})==6
    with pytest.raises(InsufficientData): select_samples(hits[:2],3)

def test_star_par_y_preserved(tmp_path):
    path=tmp_path/'counts.tsv'
    path.write_text('# annotation\ngene_id\tgene_name\tunstranded\nN_unmapped\tNA\t15\nENSG01.2\tA\t10\nENSG01.2_PAR_Y\tA\t5\n')
    data=parse_counts(path)
    assert list(data.index)==['ENSG01','ENSG01_PAR_Y']
    assert data.unstranded.sum()==15

def test_normalization_and_filter():
    counts=pd.DataFrame({'a':[10,90,0],'b':[20,180,0]},index=['A','B','C'])
    cpm,log,sizes=normalize(counts)
    assert list(cpm.index)==['A','B']
    np.testing.assert_allclose(cpm.a,cpm.b)
    np.testing.assert_allclose(log,np.log2(cpm+1))
    with pytest.raises(ValueError): normalize(pd.DataFrame({'a':[0,0]}))

def test_fdr_known_values():
    np.testing.assert_allclose(bh([.01,.04,.03,.002]),[.02,.04,.04,.008])
    assert bh([np.nan])[0]==1

def test_differential_sign():
    names=['t1','t2','t3','n1','n2','n3']
    cpm=pd.DataFrame([[100,120,110,1,2,3],[1,2,3,100,120,110]],columns=names,index=['e1','e2'])
    samples=[dict(sample_id=n,sample_type='Primary Tumor' if n.startswith('t') else 'Solid Tissue Normal') for n in names]
    de=differential(cpm,np.log2(cpm+1),pd.Series({'e1':'A','e2':'B'}),samples).set_index('gene')
    assert de.loc['A','log2fc']>0 and de.loc['B','log2fc']<0
    assert (de.fdr<.05).all()

def test_signature_threshold_and_ambiguity():
    de=pd.DataFrame({'gene_id':['a','b','c','d'],'gene':['A','B','C','C'],'fdr':[.01,.02,.001,.5],'log2fc':[2,-2,3,0]})
    assert set(match_symbols(de).gene)=={'A','B'}
    sig=build(de,max_genes=1)
    assert list(sig.direction)==['up','down']
    assert len(build(de,effect=3))==0

def test_gmt_context_and_compound_hyphens(tmp_path):
    path=tmp_path/'data.gmt';path.write_text('CPC001 HA1E 24H-ici-89406-10.0\t\ta\tb\n')
    rows=parse_gmt(path)
    meta=metadata(next(iter(rows)))
    assert meta['compound']=='ici-89406' and meta['dose']=='10.0'
    assert meta['replicate_count'] is None and rows[meta['term']]=={'A','B'}
    assert metadata('unrecognized term') is None

def fixtures():
    sig=pd.DataFrame({'gene':['A','B'],'log2fc':[2.,-2.],'direction':['up','down']})
    records=[]
    for compound,up,down in [('reverse',{'B'},{'A'}),('same',{'A'},{'B'})]:
        records.append(dict(compound=compound,up=up,down=down,term=compound,cell_line='MCF7',time='24H',dose='10'))
    return sig,records

def test_reversal_direction_and_evidence():
    sig,records=fixtures();scorer=Scorer(records,['A','B','C'])
    scores=scorer.score(sig,2,20,42)
    np.testing.assert_allclose(scores['scores'],[-1,1])
    assert scores['eligible'].all()
    evidence=scorer.gene_evidence(records[0],sig,scores['denominator'])
    assert sum(r['contribution'] for r in evidence)==-1
    assert all(r['opposing'] for r in evidence)
    np.testing.assert_equal(scores['null'],scorer.score(sig,2,20,42)['null'])

def test_missing_gene_denominator_and_coverage():
    sig,records=fixtures();records[0]['down']=set()
    scorer=Scorer(records,['A','B'])
    scores=scorer.score(sig,2)
    assert scores['scores'][0]==-.5 and not scores['eligible'][0]
    with pytest.raises(InsufficientData): scorer.score(sig.iloc[:1],2)

def test_context_ranking_and_multi_context():
    sig,records=fixtures();records.append(dict(records[0],cell_line='A549',term='second'))
    scored=Scorer(records,['A','B']).score(sig,2,20)
    ranked=rank(records,scored)
    assert ranked[0]['compound']=='reverse' and ranked[0]['supporting_contexts']==2
    assert ranked[0]['consistency']==1
    assert [r['compound'] for r in rank(records,scored,2)]==['reverse']
    assert ranked[0]['permutation_p']>=1/21

def test_duplicate_context_not_independent():
    sig,records=fixtures();records.append(dict(records[0],term='same-context-other-batch'))
    ranked=rank(records,Scorer(records,['A','B']).score(sig,2))
    assert ranked[0]['contexts']==1 and ranked[0]['signatures']==2
    assert rank(records,Scorer(records,['A','B']).score(sig,2),2)==[]

def test_robustness_missing_not_imputed():
    a=[dict(compound='a',rank=1),dict(compound='b',rank=2)]
    b=[dict(compound='b',rank=1),dict(compound='c',rank=2)]
    result=compare_rankings({'a':a,'b':b},2)
    assert result['comparisons'][0]['jaccard']==1/3
    assert result['comparisons'][0]['rank_correlation'] is None
    assert next(r for r in result['stability'] if r['compound']=='a')['ranks']=={'a':1}

def test_cross_cancer_insufficient_preserved():
    results={'x':dict(status='complete',candidates=[dict(compound='a',rank=1)],signature=[dict(gene='A',direction='up')]),'y':dict(status='insufficient_data',error='No normals')}
    result=compare(results)
    assert len(result['analyses'])==2 and result['comparisons']==[]
    results['z']=results['x']
    result=compare(results)
    assert result['comparisons'][0]['jaccard']==1
    assert result['signature_comparisons'][0]['up_jaccard']==1

def test_parallel_retrieval_preserves_sample_order(tmp_path,monkeypatch):
    import app.tcga.client as client
    monkeypatch.setattr(client,'CACHE',tmp_path)
    monkeypatch.setattr(client,'download',lambda url,path,md5:{'sha256':'verified'})
    monkeypatch.setattr(client,'parse_counts',lambda path:pd.DataFrame({'gene_name':['A'],'unstranded':[int(path.stem)]},index=['ENSG1']))
    samples=[dict(file_id=str(i),md5sum='x',sample_id='s'+str(i)) for i in [3,1,2]]
    events=[]
    counts,annotation,sources=client.retrieve(samples,lambda *args,**kw:events.append(kw['downloaded']))
    assert list(counts.columns)==['s3','s1','s2']
    assert list(counts.iloc[0])==[3,1,2]
    assert [s['file_id'] for s in sources]==['3','1','2'] and events==[1,2,3]
