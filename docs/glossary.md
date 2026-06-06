Back to [README.md](../README.md)
# Glossary

Definitions of key terms used across this platform, grouped by domain. Each entry includes the term, its definition, and where applicable a source for further reading.

**Jump to:** [Data Engineering](#data-engineering) · [Biological](#biological) · [Clinical & Standards](#clinical--standards)

---

## Data Engineering

### Data Contract
A formal agreement between a data producer and data consumer that specifies the structure, semantics, quality guarantees, and access rules for a dataset. Serves as the authoritative reference for how a data product behaves.

**Source:** [datacontract.com](https://datacontract.com)

---

### Data Mesh
An organisational and architectural approach to data that treats data as a product, distributes ownership to domain teams, and provides a self-serve infrastructure platform.

**Source:** Dehghani, Z. (2022). *Data Mesh*. O'Reilly Media. [datacontract.com/data-mesh](https://datacontract.com/data-mesh)

---

### Data Product
A dataset that is treated with product thinking: it has an owner, a defined purpose, documented quality, versioning, and a clear access mechanism. The primary unit of value in a data mesh.

---

### Unity Catalog
Databricks' unified governance layer for data and AI assets. Provides centralised access control, auditing, and lineage across all data in a Databricks workspace.

**Source:** [Databricks Unity Catalog documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)

---

### Schema
The formal definition of the structure of a dataset: its fields, data types, and constraints. Does not include the data itself.

---

### Lineage
A record of where data comes from, how it has been transformed, and where it flows to. Used to understand data provenance and debug quality issues.

---

## Biological

### Variant
A difference in DNA sequence compared to a reference genome. Variants range from single nucleotide changes (SNVs) to large structural rearrangements.

**Source:** [National Human Genome Research Institute — Variant](https://www.genome.gov/genetics-glossary/Variant)

---

### Germline Variant
A variant present in reproductive cells (egg or sperm) and therefore heritable — it can be passed from parent to child. Distinct from somatic variants, which arise only in body cells.

**Source:** [National Cancer Institute — Germline](https://www.cancer.gov/publications/dictionaries/genetics-dictionary/def/germline)

---

### Somatic Variant
A variant that arises in a body cell after fertilisation and is not inherited. Common in cancer biology. This platform focuses on germline variants unless stated otherwise.

---

### Gene
A segment of DNA that encodes the instructions for building a protein or functional RNA molecule. Genes are identified by standardised symbols maintained by HGNC.

**Source:** [HGNC — HUGO Gene Nomenclature Committee](https://www.genenames.org)

---

### Phenotype
The observable characteristics of an organism resulting from the interaction of its genotype with its environment. In a clinical context, often refers to the set of symptoms or features associated with a disease.

**Source:** [Online Mendelian Inheritance in Man (OMIM) — Glossary](https://omim.org/help/faq)

---

### Pathogenicity Classification
A standardised assessment of how likely a genetic variant is to cause disease. The most widely used framework defines five classes: Pathogenic, Likely Pathogenic, Variant of Uncertain Significance (VUS), Likely Benign, and Benign.

**Source:** Richards, S. et al. (2015). Standards and guidelines for the interpretation of sequence variants. *Genetics in Medicine*, 17(5), 405–424. [doi:10.1038/gim.2015.30](https://doi.org/10.1038/gim.2015.30)

---

### Rare Disease
Typically defined as a disease affecting fewer than 1 in 2,000 people (EU definition) or fewer than 200,000 people in the US (Orphan Drug Act). The majority of rare diseases have a genetic basis.

**Source:** [Orphanet — About Rare Diseases](https://www.orpha.net/en/about-rare-diseases)

---

## Clinical & Standards

### OMIM (Online Mendelian Inheritance in Man)
A continuously updated catalogue of human genes and genetic disorders, with a focus on the relationship between genotype and phenotype. A primary reference for Mendelian disease.

**Source:** [omim.org](https://omim.org)

---

### Orphanet
A reference portal for information on rare diseases and orphan drugs. Maintains the ORPHA nomenclature, a standardised classification system for rare diseases.

**Source:** [orpha.net](https://www.orpha.net)

---

### HGNC (HUGO Gene Nomenclature Committee)
The body responsible for approving unique and standardised symbols and names for human genes. All gene symbols used on this platform follow HGNC conventions.

**Source:** [genenames.org](https://www.genenames.org)

---

### HPO (Human Phenotype Ontology)
A standardised vocabulary of human phenotypic abnormalities used to describe clinical features of disease in a computable, interoperable way.

**Source:** [hpo.jax.org](https://hpo.jax.org)

---

### ICD (International Classification of Diseases)
A global standard for recording, reporting, and grouping diseases and health conditions, maintained by the World Health Organisation. Currently in its 11th revision (ICD-11).

**Source:** [WHO — ICD](https://www.who.int/standards/classifications/classification-of-diseases)

---

### SNOMED CT
A comprehensive, multilingual clinical terminology used to represent clinical information in electronic health records in a consistent, machine-readable way.

**Source:** [snomed.org](https://www.snomed.org)

---

*To add a term, follow the format above: heading, definition, and a **Source:** line with a link or citation.*
