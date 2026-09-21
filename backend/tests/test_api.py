import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
import app.api.main as api
from app.io import write_json

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'RUNS',tmp_path)
    return TestClient(api.app)

def test_health_and_validation(client):
    assert client.get('/api/v1/health').json()['status']=='ok'
    assert client.post('/api/v1/analyses',json={'cancer':'x'}).status_code==422
    assert client.post('/api/v1/analyses',json={'cancer':'   '}).status_code==422
    assert client.post('/api/v1/analyses',json={'cancer':'breast','samples_per_group':1}).status_code==422
    assert client.get('/api/v1/analyses/not-a-uuid').status_code==404

def test_post_status_and_results(client,monkeypatch):
    calls=[]
    monkeypatch.setattr(api.executor,'submit',lambda fn,id,params:calls.append((id,params)))
    response=client.post('/api/v1/analyses',json={'cancer':'breast cancer'})
    assert response.status_code==202
    id=response.json()['id']
    assert calls[0][1]['cancer']=='breast cancer'
    assert client.get(f'/api/v1/analyses/{id}').json()['status']=='queued'
    assert client.get(f'/api/v1/analyses/{id}/results').status_code==409
    assert client.get(f'/api/v1/analyses/{id}/artifacts/state.json').status_code==404
    result=dict(robustness={'test':'calculated'},candidates=[],summary={})
    write_json(api.RUNS/id/'results.json',result)
    state=response.json()
    state['status']='complete'
    write_json(api.RUNS/id/'state.json',state)
    assert client.get(f'/api/v1/analyses/{id}/results').json()==result
    assert client.get(f'/api/v1/analyses/{id}/robustness').json()==result['robustness']
    assert client.get(f'/api/v1/analyses/{id}/candidates/absent').status_code==404
    assert client.get(f'/api/v1/analyses/{id}/artifacts/results.json').status_code==200

def test_comparison_validation(client):
    id=str(uuid.uuid4())
    assert client.post('/api/v1/comparisons',json={'analysis_ids':[id,id]}).status_code==422
    assert client.get('/api/v1/comparisons/not-id/cross_cancer.csv').status_code==404


@pytest.mark.parametrize('status',['queued','running','failed','interrupted','insufficient_data'])
def test_unfinished_results_are_not_exposed(client,status):
    id=str(uuid.uuid4())
    folder=api.RUNS/id
    folder.mkdir()
    write_json(folder/'state.json',{'status':status})
    write_json(folder/'results.json',{'status':'complete','robustness':{}})
    assert client.get(f'/api/v1/analyses/{id}/results').status_code==409
    assert client.get(f'/api/v1/analyses/{id}/robustness').status_code==409


def test_parallel_submissions_respect_queue_limit(client,monkeypatch):
    calls=[]
    monkeypatch.setattr(api.executor,'submit',lambda fn,id,params:calls.append(id))
    with ThreadPoolExecutor(max_workers=16) as pool:
        responses=list(pool.map(lambda _:client.post('/api/v1/analyses',json={'cancer':' breast cancer '}),range(16)))
    assert sum(r.status_code==202 for r in responses)==10
    assert sum(r.status_code==429 for r in responses)==6
    assert len(calls)==10
    assert all(r.json()['cancer']=='breast cancer' for r in responses if r.status_code==202)


def test_worker_rejection_does_not_leave_queued_run(client,monkeypatch):
    def reject(*args):
        raise RuntimeError('cannot schedule new futures after shutdown')
    monkeypatch.setattr(api.executor,'submit',reject)
    assert client.post('/api/v1/analyses',json={'cancer':'breast cancer'}).status_code==503
    history=client.get('/api/v1/analyses').json()
    assert len(history)==1 and history[0]['status']=='failed'
    assert 'worker is unavailable' in history[0]['error']


def test_comparison_unavailable_runs_export_headers(client,tmp_path,monkeypatch):
    import app.config as config
    monkeypatch.setattr(config,'DATA',tmp_path)
    ids=[str(uuid.uuid4()) for _ in range(2)]
    for id in ids:
        folder=api.RUNS/id
        folder.mkdir()
        write_json(folder/'state.json',{'status':'insufficient_data','error':'No normals'})
    response=client.post('/api/v1/comparisons',json={'analysis_ids':ids})
    assert response.status_code==200
    result=response.json()
    assert result['comparisons']==[]
    assert len(result['analyses'])==2
    exported=client.get(result['csv_url'])
    assert exported.status_code==200
    assert exported.text.strip()=='a,b,top_k,overlap,jaccard,rank_correlation,common_candidates'
    saved=json.loads((tmp_path/'comparisons'/result['id']/'comparison.json').read_text())
    assert saved==result


def test_comparison_rejects_same_cancer_runs(client):
    ids=[str(uuid.uuid4()) for _ in range(2)]
    for id in ids:
        folder=api.RUNS/id
        folder.mkdir()
        write_json(folder/'state.json',{'status':'complete'})
        write_json(folder/'results.json',{'status':'complete','project':{'project_id':'TCGA-BRCA'}})
    assert client.post('/api/v1/comparisons',json={'analysis_ids':ids}).status_code==422
