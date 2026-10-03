# IRIS — Molecular Reversal Research

A local, working research prototype that retrieves public TCGA/GDC RNA-seq counts, calculates a cancer signature, scores public LINCS chemical perturbation gene sets, and exports ranked computational candidates and robustness analyses. No CLUE account, API key, demo rankings, or simulated biological data are used in the application.

**Research question:** Can transcriptomic reversal be used to prioritize compounds whose gene-expression effects oppose a cancer-specific molecular signature?

This is hypothesis generation, not a treatment recommendation. The implemented statistics are exploratory; see [METHODS.md](METHODS.md) and [LIMITATIONS.md](LIMITATIONS.md).

## Run locally

Requirements: Python 3.11+, Node.js 20.9+, npm, internet access to api.gdc.cancer.gov and maayanlab.cloud. Commands below run from the repository root.

```sh
python3.11 -m venv .venv311
.venv311/bin/python -m pip install -r backend/requirements.lock.txt
npm ci --prefix frontend
```

In one terminal:

```sh
.venv311/bin/python -m uvicorn app.api.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
npm run dev --prefix frontend
```

Open **http://localhost:3000**. Enter `breast cancer` and click **Analyze Cancer**. The browser submits a real background analysis. Default selection is up to 20 tumor and 20 normal patients, not the full TCGA cohort. The first run downloads approximately 170 MB of GDC files plus the LINCS libraries; time depends on the public services. Later runs verify and reuse cached downloads.

For a production frontend build:

```sh
npm run build --prefix frontend
npm run start --prefix frontend
```

Use one backend process/worker: the local job queue is deliberately single-worker. Do not start with multiple Uvicorn workers. Both services bind to loopback; this prototype is not an authenticated public hosting deployment.

Optional settings: `IRIS_DATA_DIR` changes the absolute cache/output root. `BACKEND_URL` changes Next.js's backend origin (default `http://127.0.0.1:8000`). No secrets are required.

## Reproducible command-line analysis

```sh
.venv311/bin/python scripts/run-analysis.py 'breast cancer' --samples 20
.venv311/bin/python scripts/run-analysis.py 'lung adenocarcinoma' --samples 20
.venv311/bin/python scripts/run-analysis.py 'prostate cancer' --samples 20
```

Use the Research page to select runs and compare them. Missing/failed analyses are retained explicitly. Cross-cancer exports are stored under `data/comparisons/`.

## Tests

```sh
.venv311/bin/python -m pytest -c backend/pytest.ini backend/tests -m 'not integration' -q
IRIS_REAL_RUN=/absolute/path/to/data/analyses/RUN_ID .venv311/bin/python -m pytest -c backend/pytest.ini backend/tests -m integration -q
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

The real-data integration test verifies a completed actual analysis and independently reconstructs every candidate's context and aggregate scores from exported gene contributions. It skips unless explicitly given a real run; synthetic unit fixtures do not count as biological validation. Actual verification results are recorded in [RESEARCH_AUDIT.md](RESEARCH_AUDIT.md).

## Main files

- `backend/app/api/main.py`: validated FastAPI routes and local queue.
- `backend/app/tcga/client.py`: project resolution, metadata-based sample selection, STAR downloads/parser.
- `backend/app/preprocessing/normalize.py`: CPM and low-expression filtering.
- `backend/app/differential/analyze.py`: Welch tests, effect size, BH adjustment.
- `backend/app/signature/build.py`: symbol mapping and directional signatures.
- `backend/app/perturbations/lincs.py`: verified public GMT acquisition, parsing, context labels.
- `backend/app/scoring/reversal.py`: sparse directional scoring and seeded permutations.
- `backend/app/ranking/aggregate.py`: context and compound aggregation.
- `backend/app/robustness/compare.py`: parameter sensitivity and rank comparisons.
- `backend/app/cross_cancer/compare.py`: signatures and candidates across runs.
- `backend/app/pipeline/runner.py`: end-to-end orchestration and exports.
- `backend/tests/`: focused unit/API tests and real-data artifact integration test.
- `frontend/app/`: home, analysis, candidate, methodology, research, and about pages.
- `frontend/components/`: polling, candidate evidence, charts/tables, API client, shell.
- `data/`: locally generated, ignored caches and results.


Further documentation: [ARCHITECTURE.md](ARCHITECTURE.md), [DATA_SOURCES.md](DATA_SOURCES.md), [REPRODUCIBILITY.md](REPRODUCIBILITY.md), [DEMO.md](DEMO.md),[Seed and parameters](configs/althea_config.json), [results by cancer](RUN_INDEX.md).
