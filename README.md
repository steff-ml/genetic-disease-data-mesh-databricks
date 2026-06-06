# Genetic Disease Data Mesh for Databricks DRAFT
A governed, continuously updated data platform linking genetic mutation profiles to therapeutic eligibility for Duchenne Muscular Dystrophy built on the Databricks medallion architecture, designed to extend to other rare genetic diseases.

---

## The Problem

The four FDA-approved exon-skipping therapies for DMD cover only 27% of patients by mutation alone ([Leckie et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11593839/)). The remaining 73% have options (investigational antisense oligonucleotides, CRISPR-based approaches, gene therapy, base and prime editing) but identifying which approach a specific patient qualifies for requires manually cross-referencing mutation registries, the reading frame rule, and free-text trial eligibility criteria across systems that do not interoperate. That process does not scale across a patient registry and does not update when new trials open.

This platform makes it queryable.

---

## Data Products (Planned)

Each gold-layer table is a versioned, governed data product with a published schema, data contract, and quality SLA. Products are built in dependency order.

| Product | Domain | Description | Status |
|---------|--------|-------------|--------|
| `clinical.gold.trial_eligibility_catalogue` | Clinical | Structured DMD trial eligibility rules extracted from ClinicalTrials.gov, EU register, and FDA approvals | In build |
| `discovery.gold.dmd_mutation_catalogue` | Discovery | All known DMD variants, normalized to HGVS, classified, and enriched with population frequency | Planned |
| `discovery.gold.patient_mutation_profile` | Discovery | Per-patient Layer 1 classification with computed reading frame effect and hotspot region | Planned |
| `discovery.gold.exon_skipping_eligibility` | Discovery | Boolean AON eligibility flags per patient for approved exon-skip targets (51, 53, 45, 44) | Planned |
| `clinical.gold.patient_trial_eligibility` | Clinical | Per-patient, per-trial eligibility verdict with mutation-eligible flag, evidence level, and exclusion reasons | Planned |
| `clinical.gold.therapy_addressable_population` | Clinical | For each therapy, count and breakdown of mutation-eligible patients | Planned |
| `clinical.gold.mutation_coverage_gaps` | Clinical | Mutation classes with no approved therapy and no active trial, by patient count | Planned |
| `clinical.gold.patient_trial_eligibility_delta` | Clinical | Newly eligible patients when trial criteria or status change | Planned |

See [docs/data-products.md](docs/data-products.md) for schemas, access methods, update cadences, and licence terms.

---

## Architecture (Planned)

The platform follows the Databricks medallion architecture across two data mesh domains.
```

┌─────────────────────────────────┐     ┌──────────────────────────────────┐
│        DISCOVERY DOMAIN         │     │          CLINICAL DOMAIN          │
│  (genetic & variant data)       │     │  (trial eligibility & matching)   │
│                                 │     │                                   │
│  Bronze  Silver  Gold           │     │  Bronze    Silver    Gold         │
│  ──────  ──────  ────           │     │  ──────    ──────    ────         │
│  LOVD  ──► norm ──► mutation ───────►──► CTgov ──► eligib ──► patient_  │
│  ClinVar    variant   catalogue │     │  FDA/EMA    rules     trial_      │
│                                 │     │                       eligibility  │
│  Ensembl ──► exon ──► patient_ ──────►  (consumed by Clinical gold)      │
│  dmd.nl       ref    mutation_  │     │                                   │
│               data   profile    │     │                                   │
└─────────────────────────────────┘     └──────────────────────────────────┘
```

The Discovery domain publishes `patient_mutation_profile` as a cross-domain data product under a versioned contract. The Clinical domain subscribes to it to produce `patient_trial_eligibility` — the primary analytical output.

---

## Data Domains (Planned)

**Discovery domain** — genetic and variant data
- Variant registries: [LOVD DMD](https://databases.lovd.nl/shared/genes/DMD), [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/)
- Genomic reference: [Ensembl](https://www.ensembl.org), [Leiden MD pages](https://www.dmd.nl)
- Standards: HGVS variant notation, GA4GH VRS, OMOP Genomic CDM extension

**Clinical domain** — trial eligibility and patient-therapy matching
- Trial sources: [ClinicalTrials.gov](https://clinicaltrials.gov), [EU Clinical Trials Register](https://www.clinicaltrialsregister.eu), FDA/EMA approval records
- Standards: OMOP CDM, CDISC SDTM (for D-RSC sourced data), HPO, OMIM
- GenAI extraction pipeline for structured eligibility rules from free-text criteria

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Platform | Databricks (Unity Catalog) |
| Pipeline | Delta Live Tables |
| Variant standard | HGVS, GA4GH VRS |
| Clinical standard | OMOP CDM 5.3.1, CDISC SDTM |
| Phenotype | HPO (Human Phenotype Ontology) |
| Disease reference | OMIM, Orphanet |
| Gene reference | HGNC |
| Governance | Unity Catalog, Bitol data contracts, 21 CFR Part 11 audit trail |
| GenAI | structured eligibility extraction with confidence scoring |
| Data distribution | Databricks Marketplace, API |

---

## Project Status

**Early stage — Product 1 in build.** The trial eligibility catalogue (`clinical.gold.trial_eligibility_catalogue`) is the first data product in development. Patient-level matching products require the genomics layer and follow in later build phases.

---

## Navigating the Repo

genetic-disease-data-mesh-databricks/
│
├── README.md                          # This file — start here
│
├── docs/
│   │
│   │   -- For everyone --
│   ├── glossary.md                    # Biological, clinical, and data engineering terms
│   ├── data-products.md               # Available datasets, schemas, access methods, licences
│   │
│   │   -- For researchers and domain scientists --
│   ├── scientific_background.md       # DMD biology, classification system, data model, prior art
│   ├── data_quality_and_coverage.md   # What data is included, reliability, known gaps
│   ├── papers  # References for the scientific knowledge encoded in the platform.
│   │
│   │   -- For decision makers and stakeholders --
│   ├── business_case.md               # Use cases, value proposition, disease extension
│   │
│   │   -- For data engineers and developers --
│   ├── adr                            # Architectural Decision Records contain the reasoning for the different choices made in this project
│   ├── setup.md                       # Local and Databricks dev environment setup
│   ├── model-card.md                  # GenAI extraction pipeline documentation
│   ├── contributing.md                # How to contribute (currently closed)
│   └── changelog.md                   # Version history
│
└── (source code folders to be added)



---

## Getting Started

See [docs/setup.md](docs/setup.md) for prerequisites, step-by-step environment setup, and troubleshooting. The platform runs on Databricks; a working Unity Catalog and compute cluster are required.

---

## Data Access and Licencing

Relevant in case end users require a deployed and managed data product.
See [docs/data-products.md](docs/data-products.md) for access methods (Databricks Marketplace, API), usage terms, and how to request commercial access.

---

## Architectural Decision Records
To understand more the why and how behind certain architectural decisions, see [docs/adr/adr_decision_sequencing_framework.md](docs/adr/adr_decision_sequencing_framework.md)

## Collaboration and Contact

This project is currently early stage and not open for external contribution. See [docs/contributing.md](docs/contributing.md) for how to report issues or propose changes once the project opens. For research collaboration or data access enquiries, contact via the repository.

---

*Built by [Synapse Data] — biomedical data engineering at scientific depth.*
Synapse Data's mission is building biomedical data infrastructure where expert reasoning is present at every design choice. This project illustrates why this matters: Without a deep understanding of how Duchenne works and what therapies work for whom, it is very difficult to effectively link the right patient to the right trial or therapy, leading to communication overhead and manual processes where every month matters for disease prognosis. I hope this project will stimulate open innovation in the area of biomedical data infrastructure design, help patients get the care they need and allow drug developers to focus on promising therapeutic opportunities.

