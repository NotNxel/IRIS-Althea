"""Run the same pipeline as the API, for reproducible experiments."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.api.main import AnalysisRequest
from app.config import RUNS
from app.io import now, write_json
from app.pipeline.runner import execute
import uuid
import json
parser = argparse.ArgumentParser()
parser.add_argument('cancer', nargs='?')
parser.add_argument('--replay', type=Path, help='Replay an existing analysis_metadata.json with pinned samples/checksums')
parser.add_argument('--samples', type=int, default=20)
args = parser.parse_args()
replay = json.loads(args.replay.read_text()) if args.replay else None
if not replay and not args.cancer:
    parser.error('Provide a cancer name or --replay analysis_metadata.json')
params = AnalysisRequest(**replay['parameters']).model_dump() if replay else AnalysisRequest(cancer=args.cancer, samples_per_group=args.samples).model_dump()
id = str(uuid.uuid4())
folder = RUNS / id
folder.mkdir()
write_json(folder / 'state.json', dict(id=id, cancer=params['cancer'], status='queued', created_at=now(), events=[], parameters=params))
execute(id, params, replay)
state = json.loads((folder / 'state.json').read_text())
print(json.dumps(state, indent=2))
sys.exit(0 if state['status'] == 'complete' else 1)
