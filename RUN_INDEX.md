# Run index

Where each cancer's outputs live. Each folder holds `differential_expression.csv`, `signature.csv`, `candidate_rankings.csv`, `robustness.csv` and `analysis_metadata.json`, which records the seed and all parameters. Folder path: `frontend/data/analyses/<run id>/`.

| Cancer | In paper's 10 | Run id | Samples per group | min_overlap | Permutations | Seed |
|---|---|---|---|---|---|---|
| TCGA-BLCA | no | `43242610-084e-436a-9de8-b25799db4b21` | 5 | 5 | 100 | 42 |
| TCGA-BRCA | yes | `23b2e92e-d3c2-435f-9721-3abcc0bc2f6d` | 20 | 5 | 100 | 42 |
| TCGA-COAD | yes | `fa1e5648-7a53-40b8-89a4-35000545ffe1` | 20 | 5 | 100 | 42 |
| TCGA-GBM | yes | `ace56a5c-d51c-4f75-a04f-9c2048f8e8cd` | 5 | 5 | 100 | 42 |
| TCGA-HNSC | yes | `caf32707-c74f-4257-894c-970bb02fd95b` | 20 | 3 | 100 | 42 |
| TCGA-KIRC | yes | `a2c457b7-ad07-4290-a3ae-ed64b5c883ff` | 20 | 3 | 100 | 42 |
| TCGA-LIHC | yes | `6cfe0331-0f10-4dd8-96ad-44895fe1aea0` | 20 | 3 | 100 | 42 |
| TCGA-LUAD | yes | `47893997-9504-4acb-89f7-66ccc0526fad` | 20 | 5 | 100 | 42 |
| TCGA-LUSC | yes | `8a33c13e-ec42-4107-a139-a9c3f32722ae` | 20 | 5 | 100 | 42 |
| TCGA-PAAD | no | `805c9154-21fa-4664-821d-ed87d81139bd` | 5 | 5 | 100 | 42 |
| TCGA-PRAD | yes | `09ffe0fc-4b11-4c9d-8dc8-7df8cc7dc0d6` | 20 | 5 | 100 | 42 |
| TCGA-THCA | yes | `9d62cb83-7625-4d8b-852d-519cf5167d24` | 20 | 3 | 100 | 42 |

Seed 42 is also the default in `backend/app/api/main.py` and `backend/app/scoring/reversal.py` (`np.random.default_rng(seed)`). To reproduce a run: `python scripts/run-analysis.py --replay frontend/data/analyses/<run id>/analysis_metadata.json`.
