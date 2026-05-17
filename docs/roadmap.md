# Roadmap

## Phase 0 — This week
Build infrastructure. No public posts yet.

**Do:**
- [ ] Write positioning document — do not publish
- [ ] Write LinkedIn headline and about section — do not publish
- [ ] Create GitHub repository, write and publish README
- [ ] Draw architecture diagram in Excalidraw, add to README
- [ ] Write `/docs/scientific-rationale.md` — biology, data model, limitations
- [ ] Write `/docs/business-case.md` — costs, use cases, disease landscape
- [ ] Send three warm contact messages — conversation not pitch
- [ ] Begin GCP course

**Read:**
- [FDA Clinical Trial Phases](https://fda.gov/patients/drug-development-process/step-3-clinical-research)
- [Certara CDISC Explainer](https://certara.com/blog/demystifying-cdisc-sdtm-and-adam)
- Read three completed Duchenne trial results on ClinicalTrials.gov manually

---

## Module 1 — Weeks 1–7
Build in private. Warm outreach only. No public posts.

### Week 1–2 — GCP and ClinicalTrials.gov

**Do:**
- [ ] Complete GCP course — mandatory before any public content
- [ ] Read ClinicalTrials.gov API documentation fully
- [ ] Explore 10 Duchenne trials manually before writing code
- [ ] Build paginated ingestion pipeline
- [ ] Bronze layer: raw API responses
- [ ] Silver layer: structured typed columns, incremental update logic
- [ ] Data quality checks: missing eligibility, missing dates, missing phase
- [ ] Document every data quality problem found
- [ ] Delta tables: `bronze_clinical_trials_raw`, `silver_clinical_trials_dmd`, `silver_trial_quality_metrics`

**Read:**
- [FreeGCP](https://freegcp.com/tracks/gcp) *(pick one)*
- [Global Health Network GCP](https://globalhealthtrainingcentre.tghn.org/ich-good-clinical-practice)
- [Novartis GCP — Coursera](https://coursera.org/learn/good-clinical-practice-novartis)
- [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/api)
- [Study Data Structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure)

**Post (publish at week 8):**
- "What Duchenne clinical trial data actually looks like: findings from ingesting 150 trials"

---

### Week 3 — OMOP

**Do:**
- [ ] Read 21 CFR Part 11 guidance document
- [ ] Read Book of OHDSI chapters 1–5
- [ ] Read Databricks OMOP solution accelerator
- [ ] Download CDISC pilot dataset — open DM and AE domains
- [ ] Set up OMOP 5.3.1 schema on Delta Lake
- [ ] Map trial conditions to OMOP Condition domain using Athena SNOMED concepts
- [ ] Map trial interventions to OMOP Drug domain
- [ ] Document mapping gaps explicitly
- [ ] Delta tables: `omop_condition_occurrence_dmd`, `omop_drug_exposure_dmd`, `omop_mapping_coverage_report`

**Read:**
- [Book of OHDSI](https://ohdsi.github.io/TheBookOfOhdsi)
- [Databricks OMOP Accelerator](https://github.com/databricks-industry-solutions/omop-cdm)
- [OHDSI Athena](https://athena.ohdsi.org)
- [OHDSI Forums](https://forums.ohdsi.org)
- [21 CFR Part 11](https://fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application)

**Post (publish at week 8):**
- "Mapping Duchenne clinical trial data to OMOP CDM on Databricks: what maps, what doesn't, and what rare disease reveals about OMOP's limits"

---

### Week 4 — Mutation Registry Exploration and EU AI Act
Groundwork for the genomics layer. No pipeline code this week — exploration and schema planning only.

**Do:**
- [ ] Read EU AI Act overview
- [ ] Explore LOVD DMD database manually — understand export format, field structure, identifier conventions
- [ ] Download LOVD DMD export and inspect raw data
- [ ] Explore TREAT-NMD registry documentation — understand what data is publicly accessible
- [ ] Read HGVS nomenclature basics — understand `c.`, `p.`, `g.` notation and how LOVD uses it
- [ ] Draft bronze schema for LOVD ingestion: field names, types, nullability, known quality issues
- [ ] Document open questions about LOVD data before building in Module 2

**Read:**
- [EU AI Act](https://artificialintelligenceact.eu)
- [LOVD DMD Database](https://databases.lovd.nl/shared/genes/DMD)
- [HGVS Nomenclature](https://varnomen.hgvs.org)
- [TREAT-NMD Registry](https://treat-nmd.org/research-overview/dmd-research-overview)

*Note: FHIR integration is deferred to Module 4 as an architecture decision record. FHIR is relevant for future EHR integration but is not on the critical path for Products 1 or 2.*

---

### Week 5 — CDISC and Delta Live Tables

**Do:**
- [ ] Read SDTM implementation guide introduction
- [ ] Open CDISC pilot dataset DM, AE, CM, EX domains — read the actual data
- [ ] Build SDTM to OMOP mapping for DM and CM domains
- [ ] Refactor ClinicalTrials.gov pipeline as DLT pipeline
- [ ] Add DLT expectations: NCT ID format, date ranges, required fields, eligibility criteria length
- [ ] Implement quarantine table for failed records
- [ ] Delta tables: `sdtm_dm_mapped`, `sdtm_cm_mapped`, `sdtm_omop_lineage`, `quarantine_failed_trials`

**Read:**
- [CDISC SDTM](https://cdisc.org/standards/foundational/sdtm)
- [CDISC Pilot Datasets](https://github.com/cdisc-org/sdtm-adam-pilot-project)
- [Delta Live Tables Documentation](https://docs.databricks.com/en/delta-live-tables/index.html)

**Posts (publish at weeks 9–10):**
- "CDISC SDTM for data engineers: mapping clinical trial submission data to OMOP on Databricks"
- "Using Delta Live Tables for clinical data quality: enforcing expectations on biomedical pipelines"

---

### Week 6 — Compliant GenAI Extraction
Most important week. This builds Product 1.

**Do:**
- [ ] Hand-label 20 Duchenne eligibility criteria — do this before writing any code
- [ ] Build extraction pipeline: mutation requirements, exon numbers, therapy eligibility, functional status, age, exclusion criteria
- [ ] Ground extracted entities to controlled vocabulary
- [ ] Add confidence scoring per field using secondary verification prompt
- [ ] Flag low-confidence extractions for human review
- [ ] Evaluate against gold standard: precision and recall per field
- [ ] Version the prompt: store prompt hash, model version, extraction timestamp in every record
- [ ] Write model card: what it does, error rates, human review requirement, intended use, EU AI Act positioning
- [ ] Write Product 1 specification: schema, update frequency, license terms, limitation statement
- [ ] Delta tables: `silver_trial_eligibility_structured`, `extraction_evaluation_metrics`

**Read:**
- [Anthropic Prompt Engineering](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
- [Model Card Format (Mitchell et al., 2019)](https://arxiv.org/abs/1810.03993)

**Posts (publish at week 10):**
- "Building compliant GenAI pipelines for clinical text: confidence scoring, validation, and audit trails"
- "Using LLMs to extract structured eligibility criteria from clinical trials: methodology, evaluation, and lessons"

---

### Week 7 — Governance and Module 1 Completion

**Do:**
- [ ] Implement Unity Catalog governance across all Module 1 tables
- [ ] Column-level access controls on sensitive fields
- [ ] Data lineage tracking source to output
- [ ] Tags: sensitivity, source, clinical relevance
- [ ] Implement 21 CFR Part 11 compatible audit trail
- [ ] Write data contracts for three core datasets
- [ ] Write five architecture decision records
- [ ] Write `/docs/model-card.md`
- [ ] Write `/docs/data-products.md` with Product 1 specification
- [ ] Write `/docs/data-quality.md` covering Module 1 sources
- [ ] Set up Claude Code automation for changelog and data quality updates
- [ ] Delta table: `data_quality_monitoring`

**Read:**
- [Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Bitol Open Data Contract Standard](https://bitol-io.github.io/open-data-contract-standard)
- [ADR Format](https://adr.github.io)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

**Posts:**
- "Five decisions I made designing a compliant rare disease data platform — and why" (publish at week 10)
- "Unity Catalog for biomedical data governance: implementing 21 CFR Part 11 audit trail requirements on Databricks" (publish later)

---

### Week 8 — Public Launch
Everything goes live simultaneously.

**Do:**
- [ ] Publish LinkedIn profile
- [ ] Publish positioning post
- [ ] Launch Product 1 — structured Duchenne trial eligibility catalogue (scope: trial eligibility criteria only; patient-trial matching requires Product 2)
- [ ] Cross-post OMOP content to OHDSI forums
- [ ] Send direct outreach to warm contacts referencing the launch

**Posts published this week:**
- Post 1: "I've spent seven weeks building a compliant clinical data platform for Duchenne — here's what I learned and what I'm launching"
- Post 2: ClinicalTrials.gov findings
- Product 1 launch post

---

### Weeks 9–10 — Remaining Module 1 Posts

**Posts published:**
- Post 3: OMOP mapping on Databricks — cross-post to OHDSI
- Post 4: GCP and compliance for data engineers
- Post 5: Compliant GenAI for clinical text
- Post 6: Five architecture decisions

**Outreach:** After Post 3 is live on OHDSI forums, begin direct LinkedIn outreach to clinical data managers, data leads at rare disease foundations, research data engineers at academic consortia. Three messages per week minimum.

---

## Module 2 — Weeks 8–12
Genomics layer. One lesson per week. One post per lesson.

**Do:**
- [ ] FASTA and reference genomes — Ensembl REST API, assembly detection function
- [ ] LOVD DMD ingestion — build bronze ingestion pipeline, handle export format, document data quality issues
- [ ] VCF ingestion in PySpark — ClinVar DMD variants, multi-allelic handling, partitioning
- [ ] HGVS normalisation — Mutalyzer API, mixed format inputs, quality report
- [ ] Ensembl VEP annotation — CSQ field parsing, MANE Select flagging
- [ ] gnomAD frequency enrichment — API, novel variants, popmax, rate limiting
- [ ] ACMG classification modelling — conflict detection, star ratings, multi-submitter handling
- [ ] BED/GTF exon annotations — DMD exon coordinates, reading frame, skipping amenability
- [ ] Delta tables: `bronze_lovd_variants_raw`, `silver_lovd_variants_dmd`

**Read:**
- [HGVS Nomenclature](https://varnomen.hgvs.org)
- [Mutalyzer](https://mutalyzer.nl)
- [GATK VCF Format](https://gatk.broadinstitute.org/hc/en-us/articles/360035531692-VCF-Variant-Call-Format)
- [Annotating Variation with VEP — EBI Webinar](https://ebi.ac.uk/training/events/annotating-your-own-variation-data-ensembl-variant-effect-predictor-vep)
- [Ensembl REST API](https://rest.ensembl.org)
- [gnomAD](https://gnomad.broadinstitute.org)
- [ClinVar](https://ncbi.nlm.nih.gov/clinvar)
- [ACMG Guidelines](https://ncbi.nlm.nih.gov/pmc/articles/PMC4544753)
- [Johns Hopkins Genomics — Coursera](https://coursera.org/learn/genomic-tools)
- [CBW Bioinformatics Materials](https://bioinformaticsdotca.github.io)

**Posts:**
- "The reference genome problem: why GRCh37 vs GRCh38 is the silent data quality killer"
- "Building a production VCF ingestion pipeline in PySpark on Databricks"
- "Variant naming as a data quality problem: HGVS normalisation in rare disease genomics"
- "Annotating DMD variants with Ensembl VEP: what the data engineer needs to know"
- "gnomAD as a data engineering problem: production frequency annotation pipeline"
- "Modelling ClinVar classification conflicts: why flattening to a single value is wrong"
- "The coordinate system trap: why off-by-one errors are so expensive in clinical genomics"

---

## Module 3 — Weeks 13–17
Linkage layer. Product 2 built here.

**Do:**
- [ ] Read TREAT-NMD DMD mutation database documentation
- [ ] Understand reading frame rule and exon skipping amenability in depth
- [ ] Build reading frame calculator
- [ ] Validate reading frame calculator against published reference set (Aartsma-Rus et al., 2009) before building linkage layer — do not proceed until this passes
- [ ] Build exon skipping amenability classifier
- [ ] Build variant-to-trial eligibility linkage layer
- [ ] Build OMOP extension for genomic data
- [ ] Write Product 2 specification and model card
- [ ] Launch Product 2 after centrepiece post
- [ ] Delta tables: `reference_exon_skipping_amenability`, `gold_variant_trial_eligibility`, `gold_eligibility_summary`, `omop_ext_genomic_variant`

**Read:**
- [TREAT-NMD](https://treat-nmd.org/research-overview/dmd-research-overview)
- [PPMD Approved Drugs](https://parentprojectmd.org/care/for-adults/fda-approved-drugs)
- [LOVD DMD](https://databases.lovd.nl/shared/genes/DMD)
- [OHDSI Genomics Working Group](https://ohdsi.org/web/wiki/doku.php?id=projects:workgroups:genomics-wg)

**Posts:**
- "Encoding the reading frame rule as a data model: the biology behind Duchenne therapy eligibility" *(TREAT-NMD outreach trigger)*
- "Linking genetic variants to clinical trial eligibility: the complete data model for Duchenne exon skipping" *(centrepiece post)*
- "Extending OMOP CDM for rare disease genomics: a practical approach for Duchenne" *(OHDSI forum post)*
- Product 2 launch post

**Outreach trigger:** After the reading frame post is published, initiate TREAT-NMD outreach.

---

## Module 4 — Weeks 18–20
Platform architecture. Final documentation.

**Do:**
- [ ] Write formal data contracts for all three core datasets
- [ ] Implement schema enforcement in Delta Lake
- [ ] Complete Unity Catalog governance implementation
- [ ] Write all five ADRs — include FHIR integration as ADR: future EHR integration via FHIR R4, deferred from Module 1 critical path
- [ ] Write `/docs/contributing.md`
- [ ] Write `/docs/glossary.md`
- [ ] Write `/docs/changelog.md`
- [ ] Write `/docs/setup.md`
- [ ] Write `/docs/ecosystem-map.md`

**Posts:**
- "Writing data contracts for biomedical datasets: what clinical and genomic data requires"
- "The biomedical data landscape for data engineers: a practical map of what exists"
- "Five architecture decisions I made building a Duchenne biomedical data platform"

---

## Complete Post Sequence

| # | Title | When |
|---|---|---|
| 1 | Project announcement and launch | Week 8 |
| 2 | ClinicalTrials.gov findings | Week 8 |
| P1 | Product 1 launch | Week 8 |
| 3 | OMOP mapping on Databricks | Week 9 |
| 4 | GCP and compliance for data engineers | Week 9 |
| 5 | Compliant GenAI for clinical text | Week 10 |
| 6 | Five architecture decisions | Week 10 |
| 7 | Reference genome problem | Module 2 |
| 8 | Production VCF ingestion on Databricks | Module 2 |
| 9 | Variant naming as data quality | Module 2 |
| 10 | Annotating DMD variants with VEP | Module 2 |
| 11 | gnomAD as data engineering | Module 2 |
| 12 | ClinVar classification conflicts | Module 2 |
| 13 | Coordinate system trap | Module 2 |
| 14 | Reading frame rule as data model | Module 3 |
| 15 | Linking variants to trial eligibility | Module 3 |
| 16 | Extending OMOP for rare disease genomics | Module 3 |
| P2 | Product 2 launch | Module 3 |
| 17 | Data contracts for biomedical datasets | Module 4 |
| 18 | Biomedical data landscape map | Module 4 |
| 19 | Unity Catalog for 21 CFR Part 11 | Module 4 |
| 20 | FHIR for data engineers: future EHR integration | Module 4 |
