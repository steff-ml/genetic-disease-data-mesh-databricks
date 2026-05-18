# Roadmap

The roadmap is organized around **data products**, not technology topics. Each gold-layer table is a data product. No product is considered complete until it has a DLT pipeline with expectations, a data contract, Unity Catalog governance, a 21 CFR Part 11 audit trail, and a published specification in `/docs/data-products.md`. Technology is learned in context as each product requires it.

**Data products in build order:**
1. [`clinical.gold.trial_eligibility_catalogue`](#product-1--clinicalgoldtrial_eligibility_catalogue) — structured trial eligibility rules
2. [`discovery.gold.dmd_mutation_catalogue`](#product-2--discoverygolddmd_mutation_catalogue) — known DMD variants, classified
3. [`discovery.gold.patient_mutation_profile`](#product-3--discoverygoldpatient_mutation_profile--discoverygoldexon_skipping_eligibility) + [`discovery.gold.exon_skipping_eligibility`](#product-3--discoverygoldpatient_mutation_profile--discoverygoldexon_skipping_eligibility) — per-patient mutation classification and AON eligibility
4. [`clinical.gold.patient_trial_eligibility`](#product-4--clinicalgoldpatient_trial_eligibility) — cross-domain patient-trial matching
5. [`clinical.gold.therapy_addressable_population`](#product-5--remaining-clinical-domain-products) — cohort sizing per therapy
6. [`clinical.gold.mutation_coverage_gaps`](#product-5--remaining-clinical-domain-products) — unmet need by mutation class
7. [`clinical.gold.patient_trial_eligibility_delta`](#product-5--remaining-clinical-domain-products) — proactive trial alerts

See [`scientific_background.md`](scientific_background.md) for the full data model and domain map. See [`business_case.md`](business_case.md) for the use cases each product addresses.

---

## Phase 0 — This week
Build infrastructure. No public posts yet.

**Do:**
- [X] Write positioning document — do not publish
- [X] Write LinkedIn headline and about section — do not publish
- [X] Create GitHub repository, write and publish README
- [O] Draw architecture diagram in Excalidraw, add to README
- [-] Write `/docs/scientific_background.md` — biology, data model, limitations
- [-] Write `/docs/business_case.md` — costs, use cases, disease landscape
- [ ] Send three warm contact messages — conversation not pitch
- [X] Begin GCP course

**Read:**
- [FDA Clinical Trial Phases](https://fda.gov/patients/drug-development-process/step-3-clinical-research)
- [Certara CDISC Explainer](https://certara.com/blog/demystifying-cdisc-sdtm-and-adam)
- Read three completed Duchenne trial results on ClinicalTrials.gov manually

---

## Product 1 — `clinical.gold.trial_eligibility_catalogue`

**What it is:** A versioned, structured catalogue of DMD trial eligibility criteria — mutation requirements, patient-level criteria, phase, status, and intervention type — extracted from ClinicalTrials.gov, the EU register, and FDA approval records. This is the first published data product and the foundation for all clinical domain matching. See [`scientific_background.md` — Clinical domain gold layer](scientific_background.md) and [`business_case.md` — Patient-Trial Matching](business_case.md).

**Build in private. Launch publicly at Week 8. Scope: trial eligibility catalogue only — patient-trial matching (which requires the discovery domain) is Product 4.**

### Definition of Done
- [ ] DLT pipeline with expectations and quarantine table
- [ ] Data contract: schema, update frequency (weekly), SLA, license terms
- [ ] Unity Catalog: access controls, sensitivity tags, lineage source → gold
- [ ] 21 CFR Part 11 compatible audit trail on all write operations
- [ ] Data quality monitoring table
- [ ] Model card for GenAI extraction component (EU AI Act positioning, error rates, human review requirement)
- [ ] Entry in `/docs/data-products.md`
- [ ] Changelog entry

### Week 1–2 — GCP and bronze ingestion

**Do:**
- [ ] Complete GCP course — mandatory before any public content
- [ ] Read ClinicalTrials.gov API documentation fully
- [ ] Explore 10 Duchenne trials manually before writing code
- [ ] Build paginated ClinicalTrials.gov ingestion pipeline
- [ ] Bronze layer: raw API responses, incremental by last-updated date
- [ ] Document every data quality problem found
- [ ] Delta tables: `bronze.clinicaltrials_raw`, `bronze.eu_trials_raw`, `bronze.fda_approvals_raw`

**Read:**
- [FreeGCP](https://freegcp.com/tracks/gcp) *(pick one)*
- [Global Health Network GCP](https://globalhealthtrainingcentre.tghn.org/ich-good-clinical-practice)
- [Novartis GCP — Coursera](https://coursera.org/learn/good-clinical-practice-novartis)
- [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/api)
- [Study Data Structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure)

### Week 3 — Silver layer and clinical standards

**Do:**
- [ ] Read 21 CFR Part 11 guidance document
- [ ] Read Book of OHDSI chapters 1–5
- [ ] Filter to DMD trials; extract intervention type, phase, status
- [ ] Set up OMOP 5.3.1 schema on Delta Lake
- [ ] Map trial conditions to OMOP Condition domain using Athena SNOMED concepts
- [ ] Map trial interventions to OMOP Drug domain
- [ ] Document mapping gaps explicitly — note where OMOP has no concept for rare disease terms
- [ ] Explore CDISC pilot dataset DM and AE domains — understand the standard before encountering it in D-RSC data
- [ ] Delta tables: `silver.trials_dmd`, `omop.condition_occurrence_dmd`, `omop.drug_exposure_dmd`, `omop.mapping_coverage_report`

**Read:**
- [Book of OHDSI](https://ohdsi.github.io/TheBookOfOhdsi)
- [Databricks OMOP Accelerator](https://github.com/databricks-industry-solutions/omop-cdm)
- [OHDSI Athena](https://athena.ohdsi.org)
- [21 CFR Part 11](https://fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application)
- [CDISC Pilot Datasets](https://github.com/cdisc-org/sdtm-adam-pilot-project)

### Week 4 — Mutation registry exploration and EU AI Act
*No pipeline code this week — exploration and schema planning only. Groundwork for Product 2.*

**Do:**
- [ ] Read EU AI Act overview
- [ ] Explore LOVD DMD database manually — understand export format, field structure, identifier conventions
- [ ] Download LOVD DMD export and inspect raw data
- [ ] Explore TREAT-NMD registry documentation — understand what is publicly accessible
- [ ] Read HGVS nomenclature basics — `c.`, `p.`, `g.` notation and how LOVD uses it
- [ ] Draft bronze schema for LOVD ingestion: field names, types, nullability, known quality issues
- [ ] Document open questions about LOVD data before building in Product 2

**Read:**
- [EU AI Act](https://artificialintelligenceact.eu)
- [LOVD DMD Database](https://databases.lovd.nl/shared/genes/DMD)
- [HGVS Nomenclature](https://varnomen.hgvs.org)
- [TREAT-NMD Registry](https://treat-nmd.org/research-overview/dmd-research-overview)

*Note: FHIR integration is deferred to the platform phase as an architecture decision record. FHIR is relevant for future EHR integration but is not on the critical path for any of the first four products.*

### Week 5 — GenAI extraction pipeline
*Most important week. This extracts structured eligibility rules from free-text criteria.*

**Do:**
- [ ] Hand-label 20 Duchenne eligibility criteria — do this before writing any code
- [ ] Build extraction pipeline: mutation requirements, exon numbers, therapy eligibility, functional status, age, exclusion criteria
- [ ] Ground extracted entities to controlled vocabulary (OMOP, HPO, Layer 1 mutation taxonomy)
- [ ] Add confidence scoring per field using secondary verification prompt
- [ ] Flag low-confidence extractions for human review
- [ ] Evaluate against gold standard: precision and recall per field
- [ ] Version the prompt: store prompt hash, model version, extraction timestamp in every record
- [ ] Delta tables: `silver.eligibility_criteria`, `silver.extraction_evaluation_metrics`

**Read:**
- [Anthropic Prompt Engineering](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
- [Model Card Format (Mitchell et al., 2019)](https://arxiv.org/abs/1810.03993)

### Week 6 — DLT pipeline and data quality

**Do:**
- [ ] Refactor all silver pipelines as DLT pipelines
- [ ] Add DLT expectations: NCT ID format, date ranges, required fields, eligibility criteria length, extraction confidence thresholds
- [ ] Implement quarantine table for failed records
- [ ] Build data quality monitoring table with freshness, completeness, and extraction confidence metrics
- [ ] Delta tables: `quarantine.failed_trials`, `monitoring.data_quality_trial_eligibility`

**Read:**
- [Delta Live Tables Documentation](https://docs.databricks.com/en/delta-live-tables/index.html)
- [CDISC SDTM](https://cdisc.org/standards/foundational/sdtm)

### Week 7 — Gold layer, governance, and Product 1 completion

**Do:**
- [ ] Publish `clinical.gold.trial_eligibility_catalogue` with versioning and lineage
- [ ] Implement Unity Catalog governance: access controls, sensitivity tags, lineage tracking
- [ ] Implement 21 CFR Part 11 compatible audit trail on all write operations
- [ ] Write data contract for `trial_eligibility_catalogue`: schema, SLA, update frequency, license terms
- [ ] Write model card for the GenAI extraction component
- [ ] Write Product 1 specification in `/docs/data-products.md`
- [ ] Write two architecture decision records: GenAI extraction approach; OMOP standard selection
- [ ] Write `/docs/data-quality.md` covering Product 1 sources
- [ ] Changelog entry

**Read:**
- [Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Bitol Open Data Contract Standard](https://bitol-io.github.io/open-data-contract-standard)
- [ADR Format](https://adr.github.io)

### Week 8 — Public launch

**Do:**
- [ ] Publish LinkedIn profile
- [ ] Publish positioning post
- [ ] Launch Product 1 — `clinical.gold.trial_eligibility_catalogue` (trial eligibility catalogue; patient-trial matching requires Product 4)
- [ ] Cross-post OMOP content to OHDSI forums
- [ ] Send direct outreach to warm contacts referencing the launch

**Posts published this week:**
- "I've spent seven weeks building a compliant clinical data platform for Duchenne — here's what I learned and what I'm launching"
- "What Duchenne clinical trial data actually looks like: findings from ingesting 150 trials"
- Product 1 launch post

**Posts queued (publish weeks 9–10):**
- "Mapping Duchenne clinical trial data to OMOP CDM on Databricks: what maps, what doesn't, and what rare disease reveals about OMOP's limits" *(cross-post to OHDSI forums)*
- "Building compliant GenAI pipelines for clinical text: confidence scoring, validation, and audit trails"
- "Using LLMs to extract structured eligibility criteria from clinical trials: methodology, evaluation, and lessons"
- "GCP and compliance for data engineers"
- "Unity Catalog for biomedical data governance: implementing 21 CFR Part 11 audit trail requirements on Databricks"

**Outreach:** After OMOP post is live on OHDSI forums, begin direct LinkedIn outreach to clinical data managers, data leads at rare disease foundations, research data engineers at academic consortia. Three messages per week minimum.

---

## Product 2 — `discovery.gold.dmd_mutation_catalogue`

**What it is:** A clean, deduplicated, annotated catalogue of all known DMD variants — normalized to HGVS, mapped to exon reference coordinates, classified for pathogenicity, and enriched with population frequency. This is the foundation for all discovery domain products. See [`scientific_background.md` — Discovery domain gold layer](scientific_background.md) and [`business_case.md` — Therapy Eligibility Gaps](business_case.md).

### Definition of Done
- [ ] DLT pipeline with expectations and quarantine table
- [ ] Data contract: schema, update frequency, SLA, license terms
- [ ] Unity Catalog: access controls, sensitivity tags, lineage
- [ ] 21 CFR Part 11 compatible audit trail
- [ ] Data quality monitoring table
- [ ] Reading frame calculator validated against [Aartsma-Rus et al. (2009)](https://pubmed.ncbi.nlm.nih.gov/19156838/) reference set — do not proceed to Product 3 until this passes
- [ ] Entry in `/docs/data-products.md`
- [ ] Changelog entry

### Weeks 9–10 — Genomic reference foundation and LOVD bronze ingestion

**Do:**
- [ ] Ingest DMD transcript and exon coordinates from Ensembl REST API
- [ ] Build exon reference table: exon number, genomic coordinates, size (bp), reading frame contribution (0/1/2 mod 3)
- [ ] Build and unit-test reading frame calculator: given a list of deleted/duplicated exon numbers, return in-frame / out-of-frame
- [ ] Cross-validate reading frame calculator against Leiden MD pages and Aartsma-Rus et al. (2009) — **hard gate before Product 3**
- [ ] FASTA and reference genomes — Ensembl REST API, assembly detection, GRCh38 alignment
- [ ] Build LOVD DMD bronze ingestion pipeline — handle export format, document quality issues
- [ ] Delta tables: `bronze.ensembl_exons_raw`, `bronze.lovd_variants_raw`, `silver.exon_reference`

**Read:**
- [GATK VCF Format](https://gatk.broadinstitute.org/hc/en-us/articles/360035531692-VCF-Variant-Call-Format)
- [Ensembl REST API](https://rest.ensembl.org)
- [Leiden MD Pages — exon sizes and reading frame table](https://www.dmd.nl)
- [Johns Hopkins Genomics — Coursera](https://coursera.org/learn/genomic-tools)

### Weeks 11–12 — ClinVar ingestion, HGVS normalization, variant enrichment

**Do:**
- [ ] VCF ingestion in PySpark — ClinVar DMD variants, multi-allelic handling, partitioning
- [ ] HGVS normalisation — Mutalyzer API, mixed format inputs, quality report
- [ ] Deduplicate variants across LOVD and ClinVar — handle identifier conflicts
- [ ] Ensembl VEP annotation — CSQ field parsing, MANE Select flagging
- [ ] gnomAD frequency enrichment — API, novel variants, popmax, rate limiting
- [ ] ACMG classification modelling — conflict detection, star ratings, multi-submitter handling
- [ ] Delta tables: `bronze.clinvar_submissions_raw`, `silver.dmd_variants`, `silver.variant_classification`

**Read:**
- [Mutalyzer](https://mutalyzer.nl)
- [Annotating Variation with VEP — EBI Webinar](https://ebi.ac.uk/training/events/annotating-your-own-variation-data-ensembl-variant-effect-predictor-vep)
- [gnomAD](https://gnomad.broadinstitute.org)
- [ClinVar](https://ncbi.nlm.nih.gov/clinvar)
- [ACMG Guidelines](https://ncbi.nlm.nih.gov/pmc/articles/PMC4544753)
- [CBW Bioinformatics Materials](https://bioinformaticsdotca.github.io)

### Week 13 — DLT, governance, and Product 2 completion

**Do:**
- [ ] Refactor all Product 2 silver pipelines as DLT pipelines with expectations and quarantine
- [ ] DQ expectations: HGVS format validation, exon number range, ClinVar star rating, gnomAD frequency bounds
- [ ] Publish `discovery.gold.dmd_mutation_catalogue`
- [ ] Implement Unity Catalog governance for discovery domain
- [ ] Write data contract for `dmd_mutation_catalogue`
- [ ] Write two architecture decision records: HGVS normalization approach; variant deduplication strategy
- [ ] Update `/docs/data-products.md` with Product 2 specification
- [ ] Delta tables: `discovery.gold.dmd_mutation_catalogue`, `monitoring.data_quality_mutation_catalogue`

**Posts that come out of Product 2 (publish weeks 9–13):**
- "The reference genome problem: why GRCh37 vs GRCh38 is the silent data quality killer"
- "Building a production VCF ingestion pipeline in PySpark on Databricks"
- "Variant naming as a data quality problem: HGVS normalisation in rare disease genomics"
- "Annotating DMD variants with Ensembl VEP: what the data engineer needs to know"
- "gnomAD as a data engineering problem: production frequency annotation pipeline"
- "Modelling ClinVar classification conflicts: why flattening to a single value is wrong"
- "The coordinate system trap: why off-by-one errors are so expensive in clinical genomics"

---

## Product 3 — `discovery.gold.patient_mutation_profile` + `discovery.gold.exon_skipping_eligibility`

**What it is:** Per-patient mutation classification using the Layer 1 schema from [`scientific_background.md`](scientific_background.md) — variant class, exons affected, computed reading frame effect, hotspot region, stop codon type — plus computed boolean AON eligibility flags for each of the four approved exon-skipping targets (51, 53, 45, 44). This is the cross-domain interface data product consumed by all clinical domain matching products.

*Prerequisite: reading frame calculator validated (Product 2 Definition of Done gate).*

### Definition of Done
- [ ] DLT pipeline with expectations and quarantine
- [ ] Data contract for `patient_mutation_profile` — schema, versioning policy, breaking-change protocol (the Clinical domain depends on this contract)
- [ ] Unity Catalog: access controls, sensitivity tags, lineage
- [ ] 21 CFR Part 11 compatible audit trail
- [ ] Data quality monitoring
- [ ] OMOP Genomic CDM extension tables populated
- [ ] Entry in `/docs/data-products.md`
- [ ] Changelog entry

### Weeks 14–15 — Layer 1 classification and exon skipping eligibility

**Do:**
- [ ] Apply Layer 1 classification to each variant in `dmd_mutation_catalogue`: variant class, exons affected, hotspot region, stop codon type
- [ ] Compute `reading_frame_effect` using validated calculator — this must be a computed field, never manually annotated
- [ ] Compute exon skipping eligibility flags for exons 51, 53, 45, 44 with reasoning trace per patient
- [ ] Build OMOP Genomic CDM extension: `GENOMIC_TEST`, `TARGET_GENE`, `VARIANT_OCCURRENCE`, `VARIANT_ANNOTATION`
- [ ] Publish `discovery.gold.patient_mutation_profile` and `discovery.gold.exon_skipping_eligibility`
- [ ] Write data contract for `patient_mutation_profile` — including versioning and breaking-change notification protocol for Clinical domain consumers
- [ ] Write one architecture decision record: OMOP G-CDM vs HGVS/GA4GH VRS for variant representation
- [ ] Update `/docs/data-products.md`

**Read:**
- [OHDSI Genomics Working Group](https://ohdsi.org/web/wiki/doku.php?id=projects:workgroups:genomics-wg)
- [OMOP Genomic CDM](https://github.com/OHDSI/Genomic-CDM)
- [GA4GH VRS](https://vrs.ga4gh.org)
- [PPMD Approved Drugs](https://parentprojectmd.org/care/for-adults/fda-approved-drugs)
- [LOVD DMD](https://databases.lovd.nl/shared/genes/DMD)

**Posts that come out of Product 3:**
- "Encoding the reading frame rule as a data model: the biology behind Duchenne therapy eligibility" *(TREAT-NMD outreach trigger)*
- "Extending OMOP CDM for rare disease genomics: a practical approach for Duchenne" *(OHDSI forum post)*

**Outreach trigger:** After the reading frame post is published, initiate TREAT-NMD outreach.

---

## Product 4 — `clinical.gold.patient_trial_eligibility`

**What it is:** The primary cross-domain data product. Per-patient, per-trial eligibility verdict — mutation-eligible flag, patient-eligible flag (nullable until clinical record input), evidence level (approved / active trial / completed / experimental), and exclusion reasons. Consumes `discovery.gold.patient_mutation_profile` as a cross-domain dependency. Enables the Patient-Trial Matching and Patient-Therapy Matching use cases from [`business_case.md`](business_case.md).

### Definition of Done
- [ ] DLT pipeline with expectations and quarantine
- [ ] Data contract: schema, cross-domain dependency on `patient_mutation_profile` v{n} pinned, SLA
- [ ] Unity Catalog: access controls, sensitivity tags, lineage across domain boundary
- [ ] 21 CFR Part 11 compatible audit trail
- [ ] Data quality monitoring
- [ ] Entry in `/docs/data-products.md`
- [ ] Changelog entry

### Weeks 16–17 — Cross-domain join and eligibility rule engine

**Do:**
- [ ] Subscribe to `discovery.gold.patient_mutation_profile` as a cross-domain data product — pin contract version
- [ ] Apply Layer 2 mutation eligibility rules from `trial_eligibility_catalogue` against patient profiles
- [ ] Add Layer 3 patient-level criteria fields (AAV antibody status, age, ambulatory status) — initially nullable, to be populated from clinical records
- [ ] Add `evidence_level` field and `exclusion_reasons[]` array
- [ ] Implement versioned output — each run produces a new version for delta computation in Product 7
- [ ] Publish `clinical.gold.patient_trial_eligibility`
- [ ] Write data contract pinning the cross-domain dependency
- [ ] Write one architecture decision record: cross-domain data product subscription pattern
- [ ] Update `/docs/data-products.md`

**Posts that come out of Product 4:**
- "Linking genetic variants to clinical trial eligibility: the complete data model for Duchenne exon skipping" *(centrepiece post)*
- Product 4 launch post

---

## Product 5 — Remaining Clinical Domain Products

**What they are:** Three analytical products built on top of Products 1–4. Each addresses a distinct business case use case from [`business_case.md`](business_case.md).

| Product | Use case | Cross-domain dependencies |
|---------|----------|--------------------------|
| `clinical.gold.therapy_addressable_population` | Therapeutic Cohort Sizing | `discovery.gold.dmd_mutation_catalogue` + `gold.trial_eligibility_catalogue` |
| `clinical.gold.mutation_coverage_gaps` | Mutation Gap Analysis | `discovery.gold.dmd_mutation_catalogue` + `gold.trial_eligibility_catalogue` |
| `clinical.gold.patient_trial_eligibility_delta` | Proactive Trial Alerts | `gold.patient_trial_eligibility` (versioned) |

### Definition of Done (each product)
- [ ] DLT pipeline with expectations and quarantine
- [ ] Data contract with pinned upstream dependencies
- [ ] Unity Catalog: access controls, lineage
- [ ] 21 CFR Part 11 compatible audit trail
- [ ] Data quality monitoring
- [ ] Entry in `/docs/data-products.md`
- [ ] Changelog entry

### Weeks 18–19 — Build, govern, and publish

**Do:**
- [ ] Build `therapy_addressable_population`: reverse-direction eligibility query from therapy inward against `dmd_mutation_catalogue`
- [ ] Build `mutation_coverage_gaps`: aggregate by mutation class, flag zero-approved and zero-active-trial classes
- [ ] Build `patient_trial_eligibility_delta`: row-level diff between consecutive versions of `patient_trial_eligibility` — new matches, lost eligibility, criteria revisions
- [ ] Apply Definition of Done checklist to each product
- [ ] Update `/docs/data-products.md`

**Posts that come out of Product 5:**
- "Writing data contracts for biomedical datasets: what clinical and genomic data requires"
- "Five architecture decisions I made building a Duchenne biomedical data platform"

---

## Platform and Open Access — Week 20+

**Goal:** make the non-patient-level products available externally; complete platform documentation and ADRs.

**Do:**
- [ ] Package `clinical.gold.trial_eligibility_catalogue` and `discovery.gold.dmd_mutation_catalogue` for Databricks Marketplace
- [ ] Publish open-source reading frame calculator and eligibility rule engine to GitHub
- [ ] Define API access layer for programmatic consumption
- [ ] Write all five ADRs — include FHIR integration as ADR: future EHR integration via FHIR R4, deferred from critical path
- [ ] Write `/docs/ecosystem-map.md`
- [ ] Write `/docs/glossary.md` (if not already complete)
- [ ] Write `/docs/setup.md` (if not already complete)
- [ ] Set up Claude Code automation for changelog and data quality updates

**Posts:**
- "The biomedical data landscape for data engineers: a practical map of what exists"
- "FHIR for data engineers: future EHR integration and why it was not on the critical path"
- Platform launch / open access announcement

---

## Complete Post Sequence

| # | Title | Product |
|---|---|---|
| 1 | Project announcement and launch | Product 1 launch |
| 2 | ClinicalTrials.gov findings | Product 1 |
| P1 | Product 1 launch — trial eligibility catalogue | Product 1 |
| 3 | OMOP mapping on Databricks *(cross-post to OHDSI)* | Product 1 |
| 4 | Compliant GenAI for clinical text | Product 1 |
| 5 | Using LLMs to extract structured eligibility criteria | Product 1 |
| 6 | GCP and compliance for data engineers | Product 1 |
| 7 | Unity Catalog for 21 CFR Part 11 | Product 1 |
| 8 | Reference genome problem | Product 2 |
| 9 | Production VCF ingestion on Databricks | Product 2 |
| 10 | Variant naming as data quality | Product 2 |
| 11 | Annotating DMD variants with VEP | Product 2 |
| 12 | gnomAD as data engineering | Product 2 |
| 13 | ClinVar classification conflicts | Product 2 |
| 14 | Coordinate system trap | Product 2 |
| 15 | Reading frame rule as data model *(TREAT-NMD outreach trigger)* | Product 3 |
| 16 | Extending OMOP for rare disease genomics *(OHDSI forum post)* | Product 3 |
| 17 | Linking variants to trial eligibility *(centrepiece post)* | Product 4 |
| P4 | Product 4 launch — patient-trial eligibility | Product 4 |
| 18 | Data contracts for biomedical datasets | Product 5 |
| 19 | Five architecture decisions | Product 5 |
| 20 | Biomedical data landscape map | Platform |
| 21 | FHIR for data engineers: future EHR integration | Platform |
