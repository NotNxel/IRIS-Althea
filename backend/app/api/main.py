import json
import os
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from threading import Lock
from typing import List
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from app.config import RUNS, VERSION
from app.io import now, write_json
from app.pipeline.runner import execute
from app.tcga.client import projects
from app.cross_cancer.compare import compare

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='iris-analysis')
queue_lock = Lock()

@asynccontextmanager
async def lifespan(app):
    for path in RUNS.glob('*/state.json'):
        state = json.loads(path.read_text())
        if state['status'] in ['queued', 'running']:
            state.update(status='interrupted', message='Server restarted during analysis. Start a new analysis; cached downloads will be reused.')
            write_json(path, state)
    yield
    executor.shutdown(wait=False, cancel_futures=True)

app = FastAPI(title='IRIS Molecular Reversal', version=VERSION, lifespan=lifespan)
_default_origins = ['http://localhost:3000', 'http://127.0.0.1:3000']
_cors_origins = [o.strip() for o in os.environ.get('IRIS_CORS_ORIGINS', '').split(',') if o.strip()] or _default_origins
app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

class AnalysisRequest(BaseModel):
    cancer: str = Field(min_length=2, max_length=150)
    samples_per_group: int = Field(default=20, ge=3, le=200)
    min_cpm: float = Field(default=1, ge=.01, le=100)
    min_fraction: float = Field(default=.2, gt=0, le=1)
    fdr: float = Field(default=.05, gt=0, le=.25)
    effect: float = Field(default=1, gt=0, le=5)
    max_genes: int = Field(default=150, ge=5, le=500)
    min_overlap: int = Field(default=5, ge=2, le=100)
    permutations: int = Field(default=100, ge=20, le=1000)
    seed: int = Field(default=42, ge=0, le=2**32-1)
    top_k: int = Field(default=20, ge=5, le=100)

    @field_validator('cancer', mode='before')
    @classmethod
    def trim_cancer(cls, value):
        return value.strip() if isinstance(value, str) else value

class ComparisonRequest(BaseModel):
    analysis_ids: List[str] = Field(min_length=2, max_length=10)
    top_k: int = Field(default=20, ge=5, le=100)

def folder_for(id):
    try:
        if str(uuid.UUID(id)) != id:
            raise ValueError()
    except ValueError:
        raise HTTPException(404, 'Analysis not found')
    folder = RUNS / id
    if not (folder / 'state.json').exists():
        raise HTTPException(404, 'Analysis not found')
    return folder

def result_for(id):
    folder = folder_for(id)
    state = json.loads((folder / 'state.json').read_text())
    if state['status'] != 'complete' or not (folder / 'results.json').exists():
        raise HTTPException(409, 'Results not available; inspect analysis status')
    return json.loads((folder / 'results.json').read_text())

@app.get('/api/v1/health')
def health():
    return {'status': 'ok', 'version': VERSION}

@app.get('/api/v1/projects')
def get_projects():
    return projects()

@app.post('/api/v1/analyses', status_code=202)
def create_analysis(request: AnalysisRequest):
    # API handlers run concurrently even though analyses use one worker.
    with queue_lock:
        queued = sum(json.loads(p.read_text())['status'] in ['queued', 'running'] for p in RUNS.glob('*/state.json'))
        if queued >= 10:
            raise HTTPException(429, 'Analysis queue is full; try again after a run finishes')
        id = str(uuid.uuid4())
        folder = RUNS / id
        folder.mkdir()
        state = dict(id=id, cancer=request.cancer, status='queued', stage='queued', message='Waiting for analysis worker', created_at=now(), events=[], parameters=request.model_dump())
        write_json(folder / 'state.json', state)
        try:
            executor.submit(execute, id, request.model_dump())
        except RuntimeError:
            message = 'Analysis worker is unavailable. Restart the server and try again.'
            state.update(status='failed', message=message, error=message, updated_at=now())
            write_json(folder / 'state.json', state)
            raise HTTPException(503, message)
    return state

@app.get('/api/v1/analyses')
def list_analyses():
    return sorted([json.loads(p.read_text()) for p in RUNS.glob('*/state.json')], key=lambda r: r['created_at'], reverse=True)

@app.get('/api/v1/analyses/{id}')
def status(id: str):
    return json.loads((folder_for(id) / 'state.json').read_text())

@app.get('/api/v1/analyses/{id}/results')
def results(id: str):
    return result_for(id)

@app.get('/api/v1/analyses/{id}/robustness')
def robustness(id: str):
    return result_for(id)['robustness']

@app.get('/api/v1/analyses/{id}/candidates/{compound:path}')
def candidate(id: str, compound: str):
    result = result_for(id)
    selected = next((c for c in result['candidates'] if c['compound'] == compound), None)
    if selected is None:
        raise HTTPException(404, 'Compound not found')
    evidence = pd.read_csv(folder_for(id) / 'gene_level_scores.csv')
    rows = json.loads(evidence[evidence.compound == compound].to_json(orient='records'))
    return dict(**selected, gene_evidence=rows, signature=result['signature'])

@app.get('/api/v1/analyses/{id}/artifacts/{name}')
def artifact(id: str, name: str):
    folder = folder_for(id)
    allowed = {'signature.csv', 'differential_expression.csv', 'candidate_rankings.csv', 'robustness.csv',
        'cross_cancer.csv', 'analysis_metadata.json', 'gene_level_scores.csv', 'results.json',
        'raw_counts.csv.gz', 'normalized_cpm.csv.gz', 'signature_baseline.csv', 'signature_relaxed.csv',
        'signature_stringent.csv', 'signature_multi-context.csv'}
    if name not in allowed or not (folder / name).is_file():
        raise HTTPException(404, 'Artifact not found')
    return FileResponse(folder / name, filename=name)

@app.post('/api/v1/comparisons')
def comparison(request: ComparisonRequest):
    if len(set(request.analysis_ids)) != len(request.analysis_ids):
        raise HTTPException(422, 'Select distinct analyses')
    records = {}
    for id in request.analysis_ids:
        folder = folder_for(id)
        state = json.loads((folder / 'state.json').read_text())
        records[id] = result_for(id) if state['status'] == 'complete' else state
    completed_projects = [r['project']['project_id'] for r in records.values() if r['status'] == 'complete']
    if len(completed_projects) != len(set(completed_projects)):
        raise HTTPException(422, 'Cross-cancer comparison requires distinct TCGA projects; select one completed run per cancer')
    result = compare(records, request.top_k)
    # Comparison is a separate artifact; never mutate a previously checksummed analysis.
    from app.config import DATA
    target = DATA / 'comparisons' / str(uuid.uuid4())
    target.mkdir(parents=True)
    result['id'] = target.name
    result['csv_url'] = '/api/v1/comparisons/' + target.name + '/cross_cancer.csv'
    write_json(target / 'comparison.json', result)
    columns = ['a', 'b', 'top_k', 'overlap', 'jaccard', 'rank_correlation', 'common_candidates']
    pd.DataFrame(result['comparisons'], columns=columns).to_csv(target / 'cross_cancer.csv', index=False)
    return result

@app.get('/api/v1/comparisons/{id}/cross_cancer.csv')
def comparison_csv(id: str):
    from app.config import DATA
    try:
        uuid.UUID(id)
    except ValueError:
        raise HTTPException(404)
    path = DATA / 'comparisons' / id / 'cross_cancer.csv'
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, filename='cross_cancer.csv')
