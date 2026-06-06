Back to [Scientific background](scientific_background.md) | Back to [README.md](../README.md)

# Implementation Roadmap

The roadmap prioritises the **Clinical domain first** — ingesting and structuring trial eligibility data before building the mutation matching layer. This delivers immediate analytical value (which trials exist for DMD?) and provides an early, concrete encounter with the clinical data standards (CDISC, OMOP, ICD, HPO) that will govern the rest of the data model.

---

## Phase 1 — Clinical trial catalogue *(Clinical domain, Bronze → Gold)*

**Goal**: produce `gold.trial_eligibility_catalogue` as the first published data product.

| Step | Task | Output |
|------|------|--------|
| 1.1 | Ingest ClinicalTrials.gov API for all DMD trials (condition: "Duchenne Muscular Dystrophy") | `bronze.clinicaltrials_raw` |
| 1.2 | Filter active, recruiting, and completed trials; extract intervention type and phase | `silver.trials_dmd` |
| 1.3 | Parse eligibility criteria text — identify mutation-related criteria (exon, deletion type, frame) and patient-level criteria (age, ambulatory, AAV antibodies) using structured extraction | `silver.eligibility_criteria` |
| 1.4 | Map extracted terms to standard vocabularies (OMIM, HPO, ICD, mutation type taxonomy from Layer 1) | Enriched `silver.eligibility_criteria` |
| 1.5 | Publish trial eligibility catalogue with versioning | `gold.trial_eligibility_catalogue` |

**What you learn in this phase**: ClinicalTrials.gov eligibility criteria are largely free text. Step 1.3 is where a GenAI extraction pipeline is needed — this is the first concrete use case for the structured extraction service. You will encounter CDISC SDTM in D-RSC-derived data, HPO terms in phenotype criteria, and OMIM IDs in genetic eligibility fields. This phase maps the clinical standards landscape before any patient data is introduced.

**Milestone**: a queryable catalogue of DMD trials with structured mutation eligibility rules, usable independently of the mutation matching layer.

---

## Phase 2 — Genomic reference foundation *(Discovery domain, Bronze → Silver)*

**Goal**: build the reference tables that make reading frame computation deterministic.

| Step | Task | Output |
|------|------|--------|
| 2.1 | Ingest DMD transcript and exon coordinates from Ensembl REST API | `bronze.ensembl_exons_raw` |
| 2.2 | Build exon reference table: exon number, genomic coordinates, size (bp), reading frame contribution (0/1/2) | `silver.exon_reference` |
| 2.3 | Implement and test reading frame calculator: given a list of deleted/duplicated exon numbers, return in-frame / out-of-frame | Validated function, unit-tested against [Aartsma-Rus et al. 2009](https://pubmed.ncbi.nlm.nih.gov/19156838/) |

**What you learn**: the reading frame contribution of each exon is fixed and can be cross-validated against the Leiden MD pages and the published Aartsma-Rus eligibility tables. This phase produces no patient-facing data product but is the computational foundation everything else depends on.

---

## Phase 3 — Variant catalogue *(Discovery domain, Silver → Gold)*

**Goal**: produce `gold.dmd_mutation_catalogue` — a clean, deduplicated, annotated catalogue of known DMD variants.

| Step | Task | Output |
|------|------|--------|
| 3.1 | Ingest LOVD DMD-specific database (API or bulk export) | `bronze.lovd_variants_raw` |
| 3.2 | Ingest ClinVar submissions for the DMD gene | `bronze.clinvar_submissions_raw` |
| 3.3 | Normalise variants to HGVS; map to exon reference; deduplicate across sources | `silver.dmd_variants` |
| 3.4 | Join with ClinVar pathogenicity classifications | `silver.variant_classification` |
| 3.5 | Publish mutation catalogue | `gold.dmd_mutation_catalogue` |

**What you learn**: HGVS normalisation across sources is non-trivial — LOVD and ClinVar use different conventions. This phase is the first encounter with genomic data quality issues: conflicting classifications, missing exon annotations, and variant representation differences between databases.

---

## Phase 4 — Patient mutation profiles *(Discovery domain, Gold)*

**Goal**: produce `gold.patient_mutation_profile` — the cross-domain interface data product.

| Step | Task | Output |
|------|------|--------|
| 4.1 | Apply Layer 1 classification to each patient's variant from the mutation catalogue | Variant class, exons affected, hotspot region, stop codon type |
| 4.2 | Compute `reading_frame_effect` using the Phase 2 calculator | In-frame / out-of-frame per patient |
| 4.3 | Compute exon skipping eligibility flags for each approved AON (exons 51, 53, 45, 44) | `gold.exon_skipping_eligibility` |
| 4.4 | Define and publish data contract for `patient_mutation_profile` | Data contract document; versioned schema |

**What you learn**: defining the data contract for this product — what schema the Clinical domain can depend on — forces decisions about what counts as a breaking change. This is the governance exercise that makes the mesh real.

---

## Phase 5 — Cross-domain patient-trial matching *(Clinical domain, Gold)*

**Goal**: produce `gold.patient_trial_eligibility` — the primary analytical output of the platform.

| Step | Task | Output |
|------|------|--------|
| 5.1 | Consume `discovery.gold.patient_mutation_profile` as a cross-domain data product | |
| 5.2 | Apply mutation eligibility rules from `gold.trial_eligibility_catalogue` against patient profiles | Layer 2 eligibility flags per patient-trial pair |
| 5.3 | Add Layer 3 patient-level criteria fields (AAV antibody status, age, ambulatory status) — initially as nullable fields to be populated from clinical records | `gold.patient_trial_eligibility` |
| 5.4 | Add `evidence_level` field (approved / active trial / completed trial / experimental) and `exclusion_reasons[]` | Final data product |

---

## Phase 6 — Data product publishing and open access

**Goal**: make the non-patient-level data products (mutation catalogue, trial eligibility catalogue, exon skipping eligibility) available via Databricks Marketplace and API.

| Step | Task |
|------|------|
| 6.1 | Package `gold.dmd_mutation_catalogue` and `gold.trial_eligibility_catalogue` for Databricks Marketplace |
| 6.2 | Publish open-source implementation (reading frame calculator, eligibility rule engine) to GitHub |
| 6.3 | Define API access layer for programmatic consumption by small biotechs and academic groups |
