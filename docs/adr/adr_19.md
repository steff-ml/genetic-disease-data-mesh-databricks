# ADR-19: Silver and Gold Layer Data Modelling Approach

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-02 (Databricks — platform shapes which modelling patterns perform well), ADR-03 (domain boundaries — scope of what must be modelled)
**Blocks:** ADR-07 (eligibility representation), ADR-08 (versioning), ADR-09 (medallion layer invariants), ADR-10 (GenAI extraction scope), ADR-11 (computability classification)

---

## The Decision Space

Four paradigms are in scope. They are not mutually exclusive across layers — Silver and Gold may use different approaches.

**Data Vault 2.0** (Linstedt): Hub/Link/Satellite structure. Hubs hold business keys (trial ID, mutation ID, patient ID); Links hold relationships; Satellites hold time-stamped descriptive attributes. Excellent audit trail, naturally handles late-arriving data and schema evolution. Queries are verbose — every analytical query requires multiple joins across hubs, links, and satellites.

**Kimball dimensional modelling**: Fact and dimension tables in a star schema. Purpose-built for analytical queries; well understood by biostatisticians. Requires more upfront design; less flexible to schema evolution than Data Vault.

**One Big Table (OBT)**: Fully denormalized table per analytical use case. Databricks-recommended pattern for Gold layer; excellent query performance; no joins at query time. Schema management is harder — every change requires a rewrite of the wide table.

**Plain normalised (3NF)**: Traditional relational approach. Good data integrity, simple to reason about. Not optimised for the large-scale analytical joins this project requires.

---

## Knowledge Required

Delta Lake and Databricks modelling best practices — what patterns perform well on Delta: partition pruning, Z-order clustering, file compaction. OBT and wide Gold tables are specifically recommended by Databricks for analytical workloads. Data Vault adds join overhead that Delta does not eliminate.

Data Vault 2.0 (Linstedt & Olschimke, 2016) — the full hub/link/satellite methodology. Relevant primarily for Silver, where auditability and late-arriving data handling are most important. Understand the raw vault vs business vault distinction and where the transformation boundary sits.

Kimball (The Data Warehouse Toolkit, 3rd ed.) — dimensional modelling fundamentals: fact grain definition, slowly changing dimensions, conformed dimensions. The star schema at Gold is a well-understood interface for biostatisticians using SAS or R.

OMOP CDM 5.3.1 schema — the clinical data model this project aspires to align with for the Clinical domain. OMOP uses a specific structure for clinical concepts, measurements, and observations. Gold layer design in the Clinical domain should map cleanly to OMOP or be derivable from it. Tension: OMOP is designed for EHR data, not for trial eligibility catalogues — the mapping is partial.

Slowly changing dimensions (SCD Type 2) — trial eligibility criteria change over time when a trial amends its protocol. The Silver layer must track historical versions of eligibility records, not just the current one. SCD Type 2 (versioned rows with valid_from / valid_to timestamps) is the standard approach; Delta Lake time travel is an alternative.

The specific query patterns this project must support, which should drive Gold layer design:
- Patient-trial eligibility join: one patient mutation profile against all active trials — requires efficient broadcast or range joins
- Mutation catalogue lookup: by exon number, deletion class, reading frame effect — requires clustered access on genomic coordinates
- Cohort sizing aggregation: count eligible patients per therapy or trial — GROUP BY over Gold tables, no patient-level joins needed at query time
- Delta computation: newly eligible patients when trial criteria change — requires comparison of two eligibility snapshots

---

## References

**Books**
- DDIA ch2: data models and query languages — relational, document, and graph models; the conceptual basis for choosing between normalised, dimensional, and wide-table approaches; explains the trade-offs that motivate OBT at Gold
- FDE ch6–8: pipeline architecture and data modelling in the context of medallion layers; physical design considerations for analytical workloads on a Lakehouse
- Kimball & Ross, *The Data Warehouse Toolkit* (3rd ed.) — the primary reference for dimensional modelling: fact grain, slowly changing dimensions, star schema design; the standard interface biostatisticians expect at Gold layer
- Linstedt & Olschimke, *Building a Scalable Data Warehouse with Data Vault 2.0* — the full hub/link/satellite methodology; relevant for Silver layer design if auditability and late-arriving data handling are the primary constraints

**Databricks documentation**
- [Delta Lake best practices](https://docs.databricks.com/en/delta/best-practices.html) — file size management, compaction, and the One Big Table pattern specifically recommended by Databricks for Gold-layer analytical tables
- [Photon engine](https://docs.databricks.com/en/optimizations/photon.html) — the vectorised query engine; understanding its performance characteristics informs whether wide OBT tables or normalised star schemas are more cost-effective at query time

**Standards references**
- [OMOP CDM 5.3.1 documentation](https://ohdsi.github.io/CommonDataModel/cdm53.html) — the OHDSI Common Data Model; defines the concept, measurement, observation, and drug exposure structures that the Gold Clinical domain should align with or be derivable from; read before designing Gold table column names and value sets

---

## Decision (to be filled in before Silver layer build)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the Silver schema is designed.*