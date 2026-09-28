import sys, json, uuid, shutil, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.api.main import AnalysisRequest
from app.config import RUNS
from app.io import now, write_json
from app.pipeline.runner import execute

# Target cancers from the current working set to upgrade to 20 samples
CANCERS = [
    ("lung adenocarcinoma", 20),
    ("colon cancer", 20),
    ("lung squamous cell carcinoma", 20),
]

FRONTEND_DATA = Path(__file__).resolve().parents[1] / "frontend" / "data" / "analyses"

for cancer, samples in CANCERS:
    print(f"\n" + "="*60)
    print(f"STARTING 20-SAMPLE RUN: {cancer}")
    print("="*60)
    try:
        params = AnalysisRequest(cancer=cancer, samples_per_group=samples).model_dump()
        run_id = str(uuid.uuid4())
        folder = RUNS / run_id
        folder.mkdir()
        write_json(folder / "state.json", dict(id=run_id, cancer=cancer, status="queued", created_at=now(), events=[], parameters=params))
        execute(run_id, params)
        state = json.loads((folder / "state.json").read_text())
        status = state["status"]
        print(f"FINISHED: {cancer} -> {status} (id: {run_id})")

        if status == "complete":
            # Remove old analysis folders for this cancer in frontend/data/analyses to keep repo clean
            for old_id in os.listdir(FRONTEND_DATA):
                old_state_file = FRONTEND_DATA / old_id / "state.json"
                if old_state_file.exists():
                    try:
                        old_state = json.loads(old_state_file.read_text())
                        if old_state.get("cancer", "").lower() == cancer.lower():
                            print(f"Replacing older run {old_id} for {cancer}")
                            shutil.rmtree(FRONTEND_DATA / old_id)
                    except Exception:
                        pass

            dst = FRONTEND_DATA / run_id
            dst.mkdir(parents=True, exist_ok=True)
            for fname in os.listdir(folder):
                if fname.endswith(".csv.gz"):
                    continue
                src_file = folder / fname
                if src_file.is_file():
                    shutil.copy2(src_file, dst / fname)
            print(f"SAVED 20-sample analysis to frontend/data/analyses/{run_id}")
    except Exception as e:
        print(f"FAILED: {cancer} -> {e}")

print("\n" + "="*60)
print("ALL 20-SAMPLE RUNS COMPLETE!")
print("="*60)
