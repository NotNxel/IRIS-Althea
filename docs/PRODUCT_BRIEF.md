# BUILD THIS PRODUCT FROM SCRATCH — CANCER DRUG REPURPOSING RESEARCH PLATFORM

You are the lead full-stack engineer + computational biology researcher.

Build a complete, working research product from scratch. Do NOT create a mockup, fake dashboard, placeholder pipeline, or hardcoded demo. The application must perform the actual computational workflow on real public datasets.

The goal is to build a research-grade prototype suitable for demonstrating a high-school computational biology research project at IRIS/ISEF level.

---

# 1. PRODUCT CONCEPT

Build a web application where a user enters a cancer type, for example:

> Breast cancer

The system should then:

1. Identify the corresponding cancer dataset in TCGA/GDC.
2. Download/retrieve real public RNA-seq expression data.
3. Separate tumor and normal samples where available.
4. Preprocess the expression data.
5. Identify genes significantly associated with the cancer.
6. Construct a cancer-specific molecular signature:

   * UP genes
   * DOWN genes
7. Retrieve publicly available drug-induced gene-expression signatures from LINCS/L1000.
8. Compare every compatible drug perturbation against the cancer signature.
9. Calculate a transcriptomic reversal score.
10. Rank compounds by how strongly they reverse the cancer-associated expression pattern.
11. Perform robustness analysis.
12. Display the results in a polished scientific web interface.
13. Clearly distinguish:

* observed data
* calculated measurements
* computational predictions
* biological interpretation

The system MUST NOT claim that a ranked compound is clinically effective.

The output is a computational hypothesis-generation system for drug repurposing.

---

# 2. CORE RESEARCH QUESTION

Use this as the central research question:

> Can transcriptomic reversal be used to prioritize compounds whose gene-expression effects oppose a cancer-specific molecular signature?

Do not change this into:

> Which drug cures cancer?

Do not make clinical efficacy claims.

---

# 3. DATA SOURCES

## TCGA / GDC

Use the public NIH/NCI Genomic Data Commons API.

The application should dynamically resolve cancer names to TCGA projects.

Examples:

Breast cancer → TCGA-BRCA

Lung adenocarcinoma → TCGA-LUAD

Prostate cancer → TCGA-PRAD

The user should be able to enter natural-language cancer names.

Do not hardcode only BRCA.

Build a reusable project-resolution system.

Retrieve real RNA-seq expression data.

Prefer STAR Counts or another appropriate raw-count representation available through GDC.

Cache downloaded data locally so repeated analyses do not repeatedly download the same files.

Implement:

* retries
* timeouts
* API error handling
* caching
* clear progress states
* logging

---

# 4. TCGA PREPROCESSING

Implement a transparent, reproducible preprocessing pipeline.

Required steps:

### Sample identification

Separate:

* primary tumor
* solid tissue normal

using GDC sample metadata.

Do not randomly label samples.

### Gene filtering

Remove extremely low-expression genes using a configurable threshold.

### Normalization

Use an appropriate normalization strategy for the selected expression representation.

Keep both:

* raw counts
* normalized expression

where useful.

### Differential expression

Calculate for each gene:

* effect size / log2 fold change
* statistical significance
* adjusted p-value / FDR

Use an appropriate RNA-seq statistical method if practical.

If a simpler method is used initially, document the limitation explicitly.

Do NOT hide methodological limitations.

---

# 5. CANCER SIGNATURE

Construct an auditable cancer molecular signature.

For example:

UPREGULATED:

genes increased in tumor relative to normal

DOWNREGULATED:

genes decreased in tumor relative to normal

Make thresholds configurable.

For example:

* FDR threshold
* minimum absolute effect size
* maximum number of signature genes

The UI should show:

* number of genes tested
* number significant
* number selected
* top upregulated genes
* top downregulated genes

Allow the user to inspect the actual gene list.

---

# 6. PUBLIC LINCS / L1000 DATA

DO NOT REQUIRE A CLUE ACCOUNT.

DO NOT REQUIRE A CLUE API KEY.

Use a public LINCS/L1000 resource that can be downloaded and processed locally.

The system must:

1. Download the public dataset automatically when needed.
2. Cache it locally.
3. Verify the downloaded file.
4. Record:

   * source
   * dataset name
   * URL/source identifier
   * download date
   * file size
   * checksum where practical
5. Parse the drug perturbation signatures.
6. Keep compound identity and perturbation metadata.

Focus on small-molecule/drug perturbations.

Do not mix unrelated genetic perturbations into the drug ranking.

The exact dataset actually used must be documented in the research audit.

---

# 7. DRUG–CANCER MATCHING

This is the central computational method.

For every compatible drug perturbation:

Compare:

CANCER SIGNATURE

vs.

DRUG-INDUCED TRANSCRIPTOMIC SIGNATURE

The desired direction is reversal.

Example:

Cancer:

Gene A ↑
Gene B ↑
Gene C ↓

Drug:

Gene A ↓
Gene B ↓
Gene C ↑

This is a strong reversal pattern.

Implement a mathematically defined reversal score.

Do NOT simply count matching gene names.

The score should consider directionality.

At minimum:

* cancer-up genes matching drug-down genes
* cancer-down genes matching drug-up genes
* optionally weighted by effect magnitude/rank where the dataset supports it

Produce a reproducible numerical score.

Document the exact equation.

---

# 8. CONTEXT HANDLING

LINCS signatures may contain different:

* cell lines
* doses
* time points
* replicates
* perturbation contexts

Do NOT blindly combine incompatible experiments.

Aggregate only when the metadata makes scientific sense.

Keep context-level information available.

For every candidate show:

* compound
* number of supporting signatures
* contexts
* score
* directionality
* supporting evidence

---

# 9. RANKING

Create a final ranked candidate table.

Each candidate should include:

* rank
* compound name
* reversal score
* number of supporting signatures
* number of contexts
* consistency across contexts
* explanation

Example:

> Rank #1 — Compound X
> Reversal score: -0.73
> Supporting contexts: 4/5
> Interpretation: strong computational reversal of the cancer-associated expression signature.

Do NOT say:

> This drug will treat breast cancer.

Instead say:

> This compound is prioritized as a computational candidate for further investigation.

---

# 10. ROBUSTNESS ANALYSIS

This is extremely important for the research component.

Do not rely on one arbitrary threshold.

Run multiple declared parameter configurations.

For example:

### Baseline

Standard FDR/effect thresholds.

### Relaxed

Broader gene signature.

### Stringent

More conservative signature.

### Multi-context

Require reversal across multiple independent perturbation contexts.

For every configuration calculate:

* ranked candidates
* top-k overlap
* Jaccard similarity
* rank correlation
* candidate frequency
* mean rank
* rank variability

The UI should have a "Robustness" section.

Show whether top candidates remain stable when reasonable methodological choices change.

---

# 11. CROSS-CANCER ANALYSIS

Allow the same pipeline to be run across multiple cancers.

Example:

* BRCA
* LUAD
* PRAD

Compare:

* cancer signatures
* candidate drugs
* top-k overlap
* rank correlations
* cancer-specific candidates
* compounds appearing across multiple cancers

Do NOT force results when data are insufficient.

Explicitly report:

> Insufficient data

rather than silently dropping a cancer.

---

# 12. SCIENTIFIC VALIDATION

Build validation into the architecture.

The application should make it possible to test questions such as:

* Are candidates stable across reasonable thresholds?
* Do candidates reproduce across contexts?
* Are some candidates cancer-specific?
* Do known compounds appear among computationally prioritized candidates?
* How does the method compare with a simple baseline?

Create a baseline method where practical.

For example:

* naive overlap
* random/signature permutation baseline

Then compare the proposed reversal method against it.

The goal is NOT merely to produce a ranked list.

The goal is to demonstrate that the computational method contains meaningful signal.

---

# 13. IMPORTANT SCIENTIFIC BOUNDARIES

The application MUST clearly state:

LINCS measures transcriptional responses to perturbations.

TCGA describes molecular characteristics of tumors.

The matching algorithm identifies computationally interesting similarities/oppositions.

This does NOT establish:

* clinical efficacy
* patient benefit
* safety
* dosage
* pharmacokinetics
* animal efficacy
* clinical trial efficacy

Never use language such as:

"cures"

"proven treatment"

"guaranteed effective"

"best cancer drug"

Instead use:

"computational candidate"

"prioritized compound"

"hypothesis"

"candidate for further investigation"

---

# 14. PRODUCT UI

Make this look like a serious scientific research platform, NOT a generic SaaS dashboard.

Design direction:

* dark scientific interface
* very clean
* restrained colors
* excellent typography
* lots of whitespace
* subtle scientific visualizations
* no unnecessary gradients
* no excessive glassmorphism
* no fake metrics
* no stock imagery

Think:

computational biology laboratory + modern research software.

---

# 15. HOME SCREEN

Hero:

> Discover Molecular Drug Reversal Candidates

Subtitle:

> A computational framework for identifying compounds whose transcriptional effects oppose cancer-associated molecular signatures.

Input:

> Enter a cancer type...

Example:

> Breast cancer

Button:

> Analyze Cancer

Below the input:

"Powered by public TCGA and LINCS/L1000 datasets."

Also include a small research disclaimer.

---

# 16. ANALYSIS EXPERIENCE

After clicking Analyze, DO NOT immediately show fake results.

Show real progress.

Example:

### Resolving cancer

TCGA-BRCA

✓ Cancer project identified

### Retrieving molecular data

1,098 cases available

✓ Tumor/normal samples identified

### Building molecular signature

18,521 genes analyzed

✓ Differential expression calculated

### Matching perturbations

5,000+ drug signatures analyzed

✓ Transcriptomic reversal calculated

### Ranking candidates

✓ Analysis complete

Use real values from the backend.

---

# 17. RESULTS PAGE

Top section:

Cancer analyzed

TCGA project

Number of samples

Number of genes

Signature size

Then show:

## Molecular Signature

Two columns:

UPREGULATED

DOWNREGULATED

Allow expanding the full gene list.

---

# 18. TOP CANDIDATES

Create a visually strong ranked table.

Columns:

Rank

Compound

Reversal Score

Supporting Contexts

Consistency

Interpretation

Clicking a candidate opens a detail panel.

---

# 19. CANDIDATE DETAIL

For each compound show:

Compound name

Reversal score

Cancer signature

Drug signature

Opposing genes

Supporting contexts

Score calculation

Number of signatures

Consistency

Research interpretation

Important limitation:

> Computational prioritization does not establish therapeutic efficacy.

Include a visualization showing:

Cancer expression direction

vs.

Drug perturbation direction.

---

# 20. VISUALIZATIONS

Include scientifically meaningful visualizations.

Examples:

### Signature distribution

Upregulated vs downregulated genes.

### Reversal score distribution

Distribution across compounds.

### Candidate comparison

Top candidates ranked by reversal score.

### Gene-level reversal

Heatmap or directional comparison for selected candidates.

### Robustness

Candidate rank across different parameter configurations.

### Cross-cancer

Candidate overlap matrix.

Avoid decorative charts.

Every chart must represent actual computed data.

---

# 21. RESEARCH AUDIT

Every analysis must save a reproducibility artifact.

Store:

* timestamp
* cancer input
* resolved TCGA project
* dataset versions
* sample IDs or identifiers where appropriate
* preprocessing parameters
* statistical thresholds
* signature genes
* LINCS dataset version
* scoring parameters
* ranking configuration
* robustness configurations
* software version
* results

Make the analysis reproducible.

---

# 22. BACKEND

Use:

Python

FastAPI

Modular architecture.

Suggested structure:

backend/

app/

tcga/

perturbations/

preprocessing/

differential/

signature/

scoring/

ranking/

robustness/

cross_cancer/

pipeline/

api/

experiments/

tests/

docs/

Keep modules separated.

Do NOT put the entire project in one giant Python file.

---

# 23. FRONTEND

Use:

Next.js

TypeScript

Tailwind CSS

Build a polished responsive interface.

Suggested pages:

/

/analysis/[id]

/candidate/[id]

/methodology

/research

/about

---

# 24. API

Implement at minimum:

POST /api/v1/analyses

GET /api/v1/analyses/{id}

GET /api/v1/analyses/{id}/results

GET /api/v1/analyses/{id}/robustness

GET /api/v1/analyses/{id}/candidates/{compound}

The backend must actually execute the analysis.

Do not return hardcoded JSON.

---

# 25. PERFORMANCE

Because public datasets are large:

* cache everything reasonable
* stream large files where possible
* avoid loading enormous matrices unnecessarily
* use efficient parsing
* save intermediate artifacts
* make repeated analyses fast
* show progress to the user

The first run can take longer.

Subsequent runs should reuse cached datasets.

---

# 26. TESTING

Write real tests.

Test:

* TCGA project resolution
* sample classification
* normalization
* differential expression
* FDR correction
* signature generation
* LINCS parsing
* gene identifier matching
* reversal scoring
* candidate ranking
* robustness
* cross-cancer aggregation
* API endpoints

Include small fixtures for unit tests.

Also run at least one real-data integration test.

---

# 27. DOCUMENTATION

Create:

README.md

METHODS.md

REPRODUCIBILITY.md

RESEARCH_AUDIT.md

ARCHITECTURE.md

DATA_SOURCES.md

LIMITATIONS.md

DEMO.md

The documentation should explain the actual implemented method.

Never document functionality that doesn't exist.

---

# 28. RESEARCH PAPER SUPPORT

The software should automatically produce machine-readable outputs that can later be used for a research paper.

Save:

signature.csv

candidate_rankings.csv

robustness.csv

cross_cancer.csv

analysis_metadata.json

gene_level_scores.csv

This allows the research results to be independently inspected.

---

# 29. NO FAKE SCIENCE

This is critical.

NEVER:

* invent experimental results
* fabricate validation
* fabricate drug efficacy
* fabricate literature evidence
* fabricate clinical trials
* hardcode impressive numbers
* claim novelty without evidence
* pretend a simulation is a biological experiment

If something cannot be calculated, say:

> Not available

or

> Not evaluated

Do not invent it.

---

# 30. DEVELOPMENT STRATEGY

Build incrementally.

PHASE 1:

Create repository structure and basic backend/frontend.

PHASE 2:

Implement real TCGA/GDC retrieval.

PHASE 3:

Implement preprocessing and cancer signature generation.

PHASE 4:

Implement public LINCS/L1000 acquisition and parsing.

PHASE 5:

Implement transcriptomic reversal scoring.

PHASE 6:

Implement candidate ranking.

PHASE 7:

Implement robustness analysis.

PHASE 8:

Implement cross-cancer analysis.

PHASE 9:

Build the frontend around the real backend.

PHASE 10:

Add tests.

PHASE 11:

Run a complete real-data analysis.

PHASE 12:

Audit every displayed number and claim.

---

# 31. FINAL ACCEPTANCE TEST

Do not tell me the project is complete until this works:

I open the website.

I type:

> breast cancer

I click:

> Analyze Cancer

The backend then actually:

TCGA-BRCA

→ retrieves real data

→ identifies tumor/normal samples

→ computes differential expression

→ builds cancer signature

→ loads public LINCS/L1000 data

→ computes drug reversal

→ ranks candidates

→ performs robustness analysis

→ produces artifacts

→ returns the results to the frontend.

The frontend then displays the actual results.

No mocked data.

No placeholder numbers.

No fake progress.

No API keys required for the core public-data workflow.

---

# 32. YOUR ROLE

Do not just write code.

Think like:

* a senior software engineer
* a computational biologist
* a research mentor
* an ISEF project reviewer

Whenever you make a methodological decision, document it.

Whenever a limitation exists, expose it.

Whenever data are unavailable, report that honestly.

Prioritize scientific validity over flashy features.

Start by inspecting the environment and creating the project from scratch.

Then implement the system phase-by-phase and test each phase before moving to the next.

At the end, give me:

1. Exact architecture
2. Files created
3. Commands to run
4. Tests performed
5. Real-data verification results
6. Known limitations
7. Exact URL to open the application

BUILD THE ACTUAL PRODUCT. DO NOT GIVE ME A PLAN ONLY.
