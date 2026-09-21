# Real public data sources

## NIH/NCI Genomic Data Commons

- API base: https://api.gdc.cancer.gov
- `/projects`: TCGA catalog and project descriptions.
- `/status`: current data release/API release, saved with every successful run.
- `/files`: open-access STAR - Counts Gene Expression Quantification metadata.
- `/data/{file_uuid}`: public unstranded RNA-seq raw counts, validated against the file's GDC MD5.
- Documentation: https://docs.gdc.cancer.gov/API/Users_Guide/Search_and_Retrieval/
- RNA-seq quantification: https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/Expression_mRNA_Pipeline/

Selected case/sample/file UUIDs and source URLs are saved. Sample type is obtained from GDC metadata. The application does not synthesize normal samples or substitute unrelated GTEx tissues. Public projects without enough normals cannot be analyzed by this workflow.

## Public LINCS/L1000 chemical signatures through Enrichr

- UP: https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName=LINCS_L1000_Chem_Pert_up
- DOWN: https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName=LINCS_L1000_Chem_Pert_down
- Provider: Ma’ayan Lab Enrichr, https://maayanlab.cloud/Enrichr/
- Program: https://lincsproject.org/

These are downloadable processed directional chemical perturbation gene sets, not full L1000 matrices, consensus therapeutic evidence, or an exhaustive current LINCS release. Both complete libraries are loaded locally; only paired parseable terms enter the scoring collection. No CLUE account or key is required. Genetic perturbation libraries are never loaded.

The export is unversioned. Every acquisition records dataset name, URL, download time, byte count, SHA-256, paired term count, parsed term count, unpaired counts, and excluded labels. Store the cached files to reproduce a historical run: deleting the cache and redownloading may acquire changed content. Source GMTs preserve term names with batch, cell line, time, compound name, and dose label. Missing dose units and replicate counts remain unavailable.

## Citation practice

Use the providers' current citation guidance for a research paper. Describe this implementation as an exploratory secondary analysis of public TCGA and processed LINCS gene sets. Do not describe its output as a biological experiment, clinical trial, treatment recommendation, or novel validated discovery.
