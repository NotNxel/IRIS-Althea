import sys, json, uuid, shutil, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.api.main import AnalysisRequest
from app.config import RUNS
from app.io import now, write_json
from app.pipeline.runner import execute

TESTS = [
    ("liver cancer", 20, 1.0, 0.05, 150, 3),
    ("thyroid cancer", 20, 0.5, 0.05, 150, 3),
    ("kidney renal clear cell carcinoma", 20, 1.0, 0.05, 150, 3),
    ("head and neck cancer", 20, 1.0, 0.05, 150, 3),
]

FRONTEND_DATA = Path(__file__).resolve().parents[1] / "frontend" / "data" / "analyses"

for cancer, samples, effect, fdr, max_genes, min_overlap in TESTS:
    print("\n" + "="*60)
    print("STARTING: " + cancer + " (samples=" + str(samples) + ")")
    print("="*60)
    try:
        params = AnalysisRequest(
            cancer=cancer,
            samples_per_group=samples,
            effect=effect,
            fdr=fdr,
            max_genes=max_genes,
            min_overlap=min_overlap
        ).model_dump()
        run_id = str(uuid.uuid4())
        folder = RUNS / run_id
        folder.mkdir()
        write_json(folder / "state.json", dict(id=run_id, cancer=cancer, status="queued", created_at=now(), events=[], parameters=params))
        execute(run_id, params)
        state = json.loads((folder / "state.json").read_text())
        status = state["status"]
        print("FINISHED: " + cancer + " -> " + status + " (" + run_id + ")")

        if status == "complete":
            for old_id in os.listdir(FRONTEND_DATA):
                old_state_file = FRONTEND_DATA / old_id / "state.json"
                if old_state_file.exists():
                    try:
                        old_state = json.loads(old_state_file.read_text())
                        if old_state.get("cancer", "").lower() == cancer.lower():
                            print("Removing older run " + old_id + " for " + cancer)
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
            print("SAVED analysis to frontend/data/analyses/" + run_id)
    except Exception as e:
        print("FAILED: " + cancer + " -> " + str(e))

print("\n" + "="*60)
print("BATCH RUN COMPLETE!")
print("="*60)
