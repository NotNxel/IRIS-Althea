# Implemented methods — version 0.1.0

## Sampling and expression

The live GDC project catalog resolves TCGA identifiers, known common-language aliases, and unique matches against project name/site/disease metadata. Ambiguous queries fail with project choices rather than silently choosing a cancer. Metadata discovery paginates open-access `Gene Expression Quantification` files with `STAR - Counts` workflow. Only files linked to exactly one case and one primary-tumor or solid-tissue-normal sample qualify.

Selection sorts by case UUID, sample UUID, file UUID. Select normal patients first, then tumor patients not already selected. Limit defaults to 20 in each group, configurable 3–200. At least three independent patients per group are required. This intentionally uses independent groups for Welch testing and is not a matched-pairs design. Available file count is not a patient count. Deterministic UUID ordering is not a random representative sample.

Use unstranded STAR counts from Ensembl rows. Remove numeric Ensembl version components, preserving `_PAR_Y` suffixes. Align the gene-ID intersection across files. Reject negative counts, duplicate normalized IDs, empty/invalid files. Raw counts are saved before filtering. Library CPM uses the sum of all Ensembl counts in the common gene intersection. Keep genes with CPM ≥ min_cpm in at least max(2, ceil(min_fraction × sample_count)) samples (defaults 1 and 0.2). Save filtered CPM and raw counts. No pseudocount is added to raw counts.

## Differential expression and signature

Welch independent-sample t-test on log2(CPM+1). Undefined tests become p=1. Benjamini–Hochberg over **all tested Ensembl rows**, before symbol filtering or signature selection. Effect is log2((mean tumor CPM+1)/(mean normal CPM+1)). This is a ratio of arithmetic means, not the difference of mean log expression. Statistical and effect-size summaries intentionally differ.

Drop empty gene symbols; uppercase exact symbols; exclude all duplicated symbols, avoiding significance-driven duplicate selection. No HGNC alias expansion is performed. Default FDR ≤0.05, |effect| ≥1; select at most 150 per arm sorted by FDR then symbol. Both arms must survive and map to LINCS. Significant-gene counts refer to tested Ensembl rows before duplicate-symbol removal; selected counts refer to unambiguous symbols.

This method is exploratory and lacks count-dispersion modeling, covariate/batch adjustment, composition correction, subtype stratification, and tumor-purity adjustment. It is not DESeq2, edgeR, or limma-voom.

## LINCS resource and contexts

Download the full Enrichr `LINCS_L1000_Chem_Pert_up` and `_down` GMT exports locally, without credentials. Verify nonempty downloads, parseable tab-separated rows, unique term keys, paired experiment labels, and locally recorded SHA-256 on cache reuse. Enrichr does not supply an upstream checksum/version for these endpoints; the first download's checksum pins the snapshot but does not provide independent upstream authenticity verification beyond HTTPS.

Pair exact term labels. Parse batch, cell, time, compound, and terminal numeric dose label from `BATCH CELL TIME-compound-dose`. Preserve hyphens/spaces in compound names. Unparseable labels are excluded and enumerated; unpaired labels are counted. Remove genes present in both arms of one perturbation. This named chemical-only resource excludes genetic perturbation libraries. Dose units and replicate counts are unavailable; never infer them.

## Score and ranking

Let U be uniquely mapped tested cancer genes intersected with the union of genes in the paired, parsed LINCS signatures. Let C be selected cancer signature genes intersected with U. For g∈C, w_g=log2FC_g. Let d_jg=+1 if drug-up, −1 if drug-down, and 0 if absent.

`S_j = sum(g in C, w_g * d_jg) / sum(g in C, abs(w_g))`

Range [-1,1]. Negative means opposition. Absent genes are zero contribution, **not an observed absence of drug response**. This is a directional, effect-weighted gene-set score, not CMap connectivity or full-expression correlation. No raw L1000 magnitudes or ranks are invented.

Require minimum 5 shared signature genes and at least one from each cancer arm per perturbation (minimum overlap configurable). This helps prevent extreme scores with tiny coverage; all paired parsed signatures are scored, but only compatible ones enter ranking. The denominator is shared across drug signatures, penalizing sparse evidence. Report mapped signature size and eligible perturbation count.

Average signatures only within the exact same compound/cell/time/dose-label context (batch may differ). Median of context means defines compound score. Rank ascending, breaking ties by exact compound label. Report all eligible compounds; non-negative aggregates explicitly lack aggregate reversal. Supporting contexts have negative means; consistency is supporting / total eligible contexts. Supporting signatures are those in negative-mean contexts, not necessarily individually negative. Contexts are distinct labels, not statistically independent replicates. Compound aliases/salts are not merged.

## Robustness

- Baseline: supplied FDR/effect/gene-cap thresholds.
- Relaxed: min(0.25, 2×FDR), 0.5×effect, 2×gene cap.
- Stringent: 0.2×FDR, 1.5×effect, max(5, floor(gene cap/2)).
- Multi-context: baseline signature; require at least two negative contexts.

Recompute eligibility and ranking for every configuration. Save every configuration's signature and ranking, including unavailable statuses. Top-k defaults to 20. Pairwise top-k intersection count and Jaccard use the available lists. Spearman uses the intersection of all eligible candidate identities, not missing-rank imputation. Fewer than two shared identities or undefined correlation yields null. Appearance frequency is top-k count; mean and population SD use present ranks only. Do not interpret a low SD for a candidate present once as reproducibility.

## Exploratory validation

Naive baseline: rank the same baseline-eligible compounds by mean shared-gene count across signatures, ignoring direction; ties break by name. Compare with reversal ranks using the same overlap/correlation metrics. No claim of superiority follows merely from different rankings.

Seeded gene-label null: shuffle the full vector of signed signature weights (including zeros) across U; default 100 permutations, seed 42. Recalculate each perturbation, context, and compound using observed eligible contexts. Lower-tail empirical p = (1 + number of null aggregate scores ≤ observed aggregate score)/(B+1). BH-correct across baseline-ranked compounds. Coverage eligibility is fixed from observed data, not reselected under the null: conditional selection can bias p-values. Correlation structure is not preserved. These are exploratory diagnostics, not confirmatory inferential evidence. Resolution at B=100 is 1/101; increase permutations for finer granularity.

Known-compound literature validation and experimental validation are not evaluated. No efficacy, safety, dosage, or clinical interpretation is made.

## Cross-cancer

Use saved independent analyses; no cancer is silently dropped from the status record. Calculate up/up and down/down signature Jaccard, top-k compound overlap, shared-candidate Spearman, and top-k appearance matrix. Exclusivity means exclusive to the selected top-k lists only. Run parameters and differing power must be considered before biological interpretation. Comparison artifacts are separate from immutable analysis artifacts.
