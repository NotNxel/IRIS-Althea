# Research audit — actual verification on 2026-09-19

The local application was built and exercised against public data. The browser acceptance flow was performed: open the home page, enter **breast cancer**, click **Analyze Cancer**, observe real progress, and view computed results. No biological result was supplied by a fixture or hardcoded API response.

## Verified complete runs

| Project | Tumor / normal | Genes tested | Selected signature | Eligible perturbations | Ranked compounds |
|---|---:|---:|---:|---:|---:|
| TCGA-BRCA | 20 / 20 | 17,362 | 300 (194 mapped) | 11,160 | 1,705 |
| TCGA-PRAD | 20 / 20 | 17,113 | 300 (140 mapped) | 6,721 | 1,185 |

Both runs use the requested default 20 independent patients per group, FDR 0.05, effect cutoff 1, at most 150 genes per arm, minimum overlap 5, and 100 gene-label permutations (seed 42). Both report GDC **Data Release 46.0 — August 10, 2026**. The downloaded LINCS pair contains 33,133 shared term labels, of which **33,132** parse as chemical perturbation experiments. One empty label was excluded and recorded. Both arms of every accepted perturbation are available; no unmatched term labels were found.

- Browser-submitted BRCA: `data/analyses/d666985b-28b2-462f-a33e-211b4790c99b/`
- PRAD: `data/analyses/09ffe0fc-4b11-4c9d-8dc8-7df8cc7dc0d6/`
- First complete BRCA acquisition: `data/analyses/23b2e92e-d3c2-435f-9721-3abcc0bc2f6d/`
- Pinned replay: `data/analyses/e3d3987b-e808-4a17-9187-cfbd3e4067bb/`
- Browser-created cross-cancer comparison: `data/comparisons/1f940900-5cf0-49bd-a4b2-4dddc4fce0b6/`

The first complete run downloaded the GDC and LINCS inputs from public services. The replay used the same pinned manifest and verified cached files with network access restricted, producing **identical summary, signature, candidates, robustness and validation values**. The subsequently browser-submitted run reproduced these values after fresh GDC resolution. Cached browser execution took approximately 66 seconds in this environment; this is an observation, not a promised runtime.

## What the numerical checks actually show

For BRCA, the baseline and relaxed top-20 lists share **11** compounds (Jaccard 0.3793). Baseline/stringent share **13** (0.4815); baseline/multi-context share **19** (0.9048). The overlap-only baseline shares **13** of the reversal top 20, with all-shared-candidate rank correlation approximately 0.2912. These differences do not establish superiority of the directional method.

The BRCA and PRAD top-20 lists share **9** compounds (Jaccard **0.2903**). Rank correlation over **1,040** common candidates is **0.2889**. This is list comparison, not proof of biological cancer specificity.

**Neither run contains a candidate with permutation BH-adjusted p < 0.05 at the default 100 permutations.** These coarse, gene-label permutation diagnostics are exploratory and additionally limited by gene correlation and fixed observed context eligibility. Ranked results are hypotheses, not validated discoveries.

Known-compound literature validation, clinical benefit, safety, dose selection, pharmacokinetics, animal validation, and experimental validation: **Not evaluated**.

## Verification performed

- 25 unit/API tests covering project resolution (including ambiguity), metadata-based sample selection and independence, STAR parsing, preserved PAR_Y suffixes, CPM/filtering, Welch direction, BH correction, signatures, symbol matching, GMT parsing, hyphenated compound names, reversal, overlap filtering, seeded permutations, context aggregation, rankings, robustness, cross-cancer missingness, verified cache reuse, atomic JSON behavior, API validation/status/results/artifacts, and order-preserving parallel retrieval.
- Real-data integration test run with BRCA and PRAD: source identifiers and checksums; patient uniqueness; gene-ID/symbol provenance; signature membership; sorted rankings; every exported perturbation's gene contributions summed independently and reconstructed into every context mean and compound median. Each full test-suite invocation reports **26 passed** (25 unit/API plus one real-data run).
- Live HTTP smoke checks: health, status, results, robustness, candidate evidence, signature CSV, audit JSON, and cross-cancer CSV all returned 200 and passed content assertions. See `experiments/live-api-verification.json`.
- TypeScript check and optimized Next.js production build pass. Frontend dependency audit reports zero known vulnerabilities after patched packages/overrides.
- Browser checks: actual submission, live progress, completed results, candidate evidence, robustness, cross-cancer calculation; mobile 390-pixel layout had document width 390 with internal table scrolling.
- One dependency deprecation warning appears in the test client (AnyIO portal alias); it does not fail tests.

## Issues found and corrected during development

The first GDC parsing attempt stripped chromosome-specific Ensembl suffixes too aggressively and stopped on duplicate IDs. The corrected parser preserves PAR_Y and has a regression test. That failed run remains visible in history rather than being concealed. Browser testing caught an HTML numeric step/min mismatch that blocked default form submission; it was fixed and the complete browser flow rerun. The PRAD integration check initially compared original mixed-case gene symbols with normalized uppercase symbols; it now verifies the declared normalization as well as original gene IDs and unchanged effect sizes. GDC transient connection resets were handled by retries.

## Remaining methodological and operational boundaries

This is an exploratory local research prototype, not a production multi-user deployment or a publication-validated inference method. See [METHODS.md](METHODS.md), [LIMITATIONS.md](LIMITATIONS.md), and the limitations embedded in each run. LUAD resolution is covered by unit tests and the dynamic catalog, but a full LUAD real-data run was not performed in this verification session. The completed real-data verification covers BRCA and PRAD.

The machine-readable verification summary is `experiments/real-data-verification.json`. Exact inputs, dataset URLs, source hashes, parameters, runtime versions, and original outputs remain under each run's `analysis_metadata.json`.
