# Architecture

```text
Browser / Next.js + TypeScript + Tailwind (127.0.0.1:3000)
  └─ /api/* same-origin proxy
      └─ FastAPI (127.0.0.1:8000), Pydantic validation
          ├─ persistent JSON status, live progress via polling
          ├─ bounded local queue / one thread worker
          └─ pipeline
              ├─ GDC project + file discovery → verified cached STAR counts
              ├─ preprocessing → CPM
              ├─ Welch DE + BH → directional signature
              ├─ Enrichr chemical UP/DOWN GMT → paired perturbations
              ├─ sparse score + seeded null
              ├─ within-context means → across-context median → rankings
              ├─ parameter robustness + naive baseline
              └─ JSON/CSV/gzip artifacts + SHA-256 audit
```

Modules are separated under `backend/app/{tcga,preprocessing,differential,signature,perturbations,scoring,ranking,robustness,cross_cancer,pipeline,api}`. `io.py` provides bounded retries, timeouts, streamed downloads, file locks, checksum checks, and atomic JSON writes. `config.py` controls paths and software version. Dependencies are pinned in lock files.

## Routes

- POST `/api/v1/analyses`: validate parameters, create UUID and queued state, submit actual work, return 202.
- GET `/api/v1/analyses`: stored run history.
- GET `/api/v1/analyses/{id}`: status and actual progress events.
- GET `/api/v1/analyses/{id}/results`: calculated results, 409 before completion.
- GET `/api/v1/analyses/{id}/robustness`: configuration rankings and comparisons.
- GET `/api/v1/analyses/{id}/candidates/{compound}`: exact identity, context metadata, signature and contributions.
- GET `/api/v1/analyses/{id}/artifacts/{name}`: explicit allowlisted downloads.
- POST `/api/v1/comparisons`: selected run comparisons, including unavailable states.
- GET `/api/v1/comparisons/{id}/cross_cancer.csv`: separate comparison export.
- GET `/api/v1/projects`: live/cached TCGA catalog.
- GET `/api/v1/health`: local service status.
- `/docs`: generated OpenAPI documentation.

The frontend has `/`, `/analysis/[id]`, `/candidate/[id]?compound=...`, `/methodology`, `/research`, `/about`. Candidate page ID is the analysis UUID; compound identity remains the exact URL-encoded dataset label.

## Persistence and concurrency

`data/cache/` contains raw verified downloads and adjacent source manifests. `data/analyses/{uuid}/` contains state and outputs. `data/comparisons/{uuid}/` contains separate cross-cancer exports. JSON writes use same-directory temporary files followed by replacement. Download locks prevent duplicate partial writers. The backend executes one job at a time and caps queued/running runs at ten.

Restart marks unfinished runs interrupted instead of claiming completion; start a fresh run to reuse downloaded files. Jobs are not automatically resumed and cancellation is not implemented. This local prototype has no database, cloud worker, multi-process scheduler, authentication, or public deployment. Bind to loopback, use a single backend worker, and keep runs local. Raw downloads are cached; computed results are saved and displayed without rerunning, but new submissions recompute statistics rather than reusing an old inference result.
