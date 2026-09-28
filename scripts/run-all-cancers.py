"""Run all cancer analyses sequentially, then copy results to frontend/data/analyses."""
import sys, json, uuid, shutil, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.api.main import AnalysisRequest
from app.config import RUNS
from app.io import now, write_json
from app.pipeline.runner import execute

CANCERS = [
    'lung adenocarcinoma',
    'colon cancer',
    'ovarian cancer',
    'glioblastoma',
    'liver cancer',
    'melanoma',
    'thyroid cancer',
    'bladder cancer',
    'pancreatic cancer',
    'lung squamous cell carcinoma',
]

FRONTEND_DATA = Path(__file__).resolve().parents[1] / 'frontend' / 'data' / 'analyses'

results = []
for cancer in CANCERS:
    print(f'\n{"="*60}')
    print(f'STARTING: {cancer}')
    print(f'{"="*60}')
    try:
        params = AnalysisRequest(cancer=cancer, samples_per_group=5).model_dump()
        run_id = str(uuid.uuid4())
        folder = RUNS / run_id
        folder.mkdir()
        write_json(folder / 'state.json', dict(id=run_id, cancer=cancer, status='queued', created_at=now(), events=[], parameters=params))
        execute(run_id, params)
        state = json.loads((folder / 'state.json').read_text())
        status = state['status']
        print(f'FINISHED: {cancer} -> {status} (id: {run_id})')
        results.append((cancer, run_id, status))

        # Copy to frontend/data/analyses (skip large .csv.gz files)
        dst = FRONTEND_DATA / run_id
        dst.mkdir(parents=True, exist_ok=True)
        for fname in os.listdir(folder):
            if fname.endswith('.csv.gz'):
                continue
            src_file = folder / fname
            if src_file.is_file():
                shutil.copy2(src_file, dst / fname)
        print(f'COPIED to frontend/data/analyses/{run_id}')
    except Exception as e:
        print(f'FAILED: {cancer} -> {e}')
        results.append((cancer, 'N/A', f'error: {e}'))

print(f'\n{"="*60}')
print('SUMMARY')
print(f'{"="*60}')
for cancer, run_id, status in results:
    print(f'  {cancer}: {status} ({run_id})')
