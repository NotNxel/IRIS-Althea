# Functional verification — 21 September 2026

The local application was checked in the browser and through its HTTP API, with real public-data results. The application remains an exploratory research prototype; functional checks do not validate clinical usefulness.

## Verified

- Submitted a real breast-cancer analysis through the homepage with the default parameters. Run `c0bfd41a-f07b-4a07-a12d-0327a7a360d8` completed with 20 tumor and 20 normal samples, 17,362 tested genes, 300 signature genes, and 1,705 ranked compounds.
- All 38 backend tests passed against that new run. The same suite passed against saved PRAD run `dc34a0d7-f02a-4c83-aca0-3163087041c2`. Integration checks verify checksums, sample independence, and reconstruction of every context and compound score from exported gene contributions.
- All 14 advertised artifacts were downloaded through the frontend proxy and checked for integrity, CSV headers, row counts, gzip contents, and sample column order. Expected missing-resource responses were checked. The recorded BRCA result is in `experiments/final-live-verification.json`.
- Browser checks covered form validation and submission, live status, saved-report navigation, candidate filtering and pagination controls, candidate drawers and standalone evidence pages, perturbation selection, Escape dismissal, signature/robustness/validation/audit tabs, and a signature CSV download.
- Browser comparison of the new BRCA run and saved PRAD run completed as `91af52a1-be34-424d-80c3-a5e0c65ef63d`: 9 common top-20 compounds, Jaccard 0.290, 1,040 common ranked compounds. Its downloadable CSV was checked independently.
- Duplicate completed cancer-project selections are blocked. Changing selections removes obsolete comparisons. Failed and nonexistent analyses show recovery links.
- Mobile evidence layout was inspected at 390 × 844; document width remained within the viewport. The temporary viewport override was reset.
- TypeScript and optimized frontend production build passed. Both local services were restarted with the fixes.

## Fixes

- Cancel obsolete report and compound requests, clear prior run state, and avoid displaying evidence for a different selected compound.
- Distinguish permanent missing-report errors from transient connection failures; add candidate retry and clear loading states.
- Align form bounds with backend validation, reject blank names, and reveal invalid advanced settings.
- Refresh notebook statuses; enforce the comparison selection bounds; keep comparisons consistent with the selected runs.
- Serve results only for completed runs, serialize queue admission, persist worker submission failures, and avoid concurrent temporary-file collisions.
- Preserve headers in empty comparison exports and save the comparison's ID and download URL in its record.

## Repeat the checks

```sh
IRIS_REAL_RUN="$PWD/data/analyses/c0bfd41a-f07b-4a07-a12d-0327a7a360d8" .venv311/bin/python -m pytest -c backend/pytest.ini backend/tests -q
npm run typecheck --prefix frontend
npm run build --prefix frontend
.venv311/bin/python scripts/verify-live-api.py c0bfd41a-f07b-4a07-a12d-0327a7a360d8 --base-url http://127.0.0.1:3000/api/v1 --comparison-id 91af52a1-be34-424d-80c3-a5e0c65ef63d
```

Checks cover the local workflows and two verified cancer projects, not every TCGA project or every possible input. New analyses still depend on public data-service availability and sufficient normal samples. The backend test suite emits one dependency deprecation warning from the test client; no test failed.
