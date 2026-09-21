# Demonstrating the actual product

1. Start the backend and frontend using README.md; open http://localhost:3000.
2. Type `breast cancer`. Expand analysis parameters to inspect the exploratory defaults. Click **Analyze Cancer**.
3. The analysis page shows actual backend events: project resolution, verified file counts, normalization, differential expression, LINCS acquisition, scoring, robustness, and export. Downloads take time; no progress percentages or results are fabricated.
4. When complete, inspect the observed sample counts, calculated tested/selected genes, and ranked computational candidates.
5. Click a compound. Inspect real source context labels and choose a perturbation to see cancer fold changes, drug directions and score contributions. Missing dose units are explicit.
6. Open **Molecular signature**, **Robustness**, **Validation**, and **Research audit**. Download CSVs and JSON. The permutation statistics and naive baseline are method diagnostics, not drug efficacy validation.
7. Run `lung adenocarcinoma` and `prostate cancer` using the same workflow. In **Research**, select distinct cancers and compute a comparison. If a cancer fails or lacks data, its state stays visible.
8. Use **Methodology** to explain assumptions. State the central research question exactly and describe top compounds as candidates for further investigation.

Research boundaries: transcriptional reversal does not establish clinical efficacy, safety, dosage or patient benefit. Known-compound literature validation is not evaluated. Do not present agreement or rank stability as proof of therapeutic activity.
