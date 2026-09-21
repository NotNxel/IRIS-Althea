# Reproducibility

Each run has a UUID and immutable research outputs. Preserve the complete run directory, its cache files and `.source.json` manifests, the source tree, and dependency locks.

`analysis_metadata.json` records UTC timestamps, user input, resolved project, GDC release, selected sample/case/file UUIDs, download URLs/checksums/sizes/dates, cohort policy, normalization parameters and library sizes, thresholds, full signature, LINCS sources and exclusions, score equation and gene universe, robustness configurations, permutation count/seed, Python/library/software versions, backend source checksums, artifact checksums, and limitations. Failures save error details and tracebacks without fabricated results.

Artifacts:

| File | Meaning |
|---|---|
| raw_counts.csv.gz | Actual aligned Ensembl counts before expression filtering |
| normalized_cpm.csv.gz | Filtered library-size CPM |
| differential_expression.csv | All tested gene effects, p-values, BH FDR, group CPM means |
| signature.csv | Selected baseline genes and directions |
| signature_baseline/relaxed/stringent/multi-context.csv | Selected genes for each available configuration |
| candidate_rankings.csv | All eligible compound rankings and exploratory null diagnostics |
| gene_level_scores.csv | Actual gene contributions for every eligible baseline perturbation |
| robustness.csv | Candidate frequency and rank summary; missing ranks stay empty |
| results.json | Complete UI results, contexts, validation, all configuration rankings |
| analysis_metadata.json | Reproducibility audit and artifact checksums |
| cross_cancer.csv | Header-only within a single run; no comparison has yet occurred |
| data/comparisons/{id}/cross_cancer.csv | Actual pairwise comparison when explicitly computed |

To reproduce the input snapshot, keep cached files (do not overwrite them) and run:

```sh
.venv311/bin/python scripts/run-analysis.py --replay data/analyses/RUN_ID/analysis_metadata.json
```

Replay pins the original project, sample manifest and parameters, skips live cohort discovery, and rejects any GDC or LINCS file whose SHA-256 differs from the original audit. Use the recorded software/dependency versions. Replay creates a new auditable run and does not overwrite the original. To start a fresh run with the same CLI defaults, run `scripts/run-analysis.py`; the live GDC discovery can change after a release, so fresh discovery alone is not guaranteed to reproduce an older sample manifest. The artifact integration test independently recomputes aggregate scores from saved contributions without any network request.

Gene-label permutations use NumPy's seeded default generator and the sorted saved gene universe. The sparse matrix is constructed from signed set membership. Set iteration order does not affect sums of exact ±1 membership. Candidate ordering ties use compound names. Sorting, thresholds and independent-patient sampling rules are specified in METHODS.md.

The research notebook exports comparisons separately rather than modifying previously checksummed analysis outputs. Single-run cross_cancer.csv is deliberately empty apart from headers; the UI labels this as not evaluated.
