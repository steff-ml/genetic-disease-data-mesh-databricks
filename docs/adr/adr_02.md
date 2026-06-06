# ADR-02: Databricks Platform

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Working Decision
**Depends on:** ADR-01 (paradigm choice constrains platform requirements)
**Blocks:** ADR-03, ADR-09, ADR-21, and all pipeline design decisions

---

## Knowledge Required

Databricks Unity Catalog documentation — governance capabilities, fine-grained access control
Delta Lake documentation — ACID properties, time travel, deletion vectors, the GxP audit story
Databricks Life Sciences reference architecture
Comparative knowledge of alternatives: Snowflake governance model, AWS Lake Formation, Azure Synapse
Understanding of GxP audit trail requirements: what the platform must provide technically

---

## References

**Books**
- FDE ch4: platform evaluation criteria for data engineering
- DDA ch2, ch5–8: data systems trade-offs and the forces that drive platform choice

**Databricks documentation**
- [What is Databricks — lakehouse architecture overview](https://docs.databricks.com/en/introduction/index.html) — read to extract the platform's own positioning claims, then verify against the critical treatment in DDA
- [Lakehouse architecture](https://docs.databricks.com/en/lakehouse/index.html) — the technical basis for the ADR-02 platform rationale

---

## Decision

### Context

The platform choice determines which governance, compute, and storage primitives are available to implement the data mesh defined in ADR-01. The primary requirements are: domain isolation with access control, governed data sharing across domain boundaries, pipeline execution with quality enforcement, and an audit trail compatible with ALCOA+ data integrity principles.

The Databricks Free tier provides full platform functionality including Unity Catalog, removing cost as a constraint during development. This decision covers the production platform target; exploration work is conducted in ungoverned notebooks on the same workspace but outside the governance framework.

### Decision

**Databricks** on the Free tier, using **Unity Catalog** for governance and **Delta Lake** as the storage format throughout all medallion layers in all domains.

**Physical catalog topology:**

| Unity Catalog level | Maps to |
|---------------------|---------|
| Catalog | Domain (`discovery`, `clinical`, `reference`) |
| Schema | Medallion layer (`bronze`, `silver`, `gold`) |
| Table | Data product or internal pipeline table |

Full table identifier pattern: `{domain}.{layer}.{table_name}`
Example: `clinical.silver.eligibility_criteria`, `discovery.gold.patient_mutation_profile`

### Alternatives considered

**Snowflake**: strong governance model, excellent SQL interface, good time-travel support. Proprietary storage format (no Delta Lake), weaker native integration with GenAI extraction pipeline work and the DLT pipeline framework equivalent. Strong for SQL-heavy analytics; does not provide the open lakehouse stack this project requires for genomic data processing and ML pipeline integration.

**AWS Lake Formation + S3 + Glue**: maximum flexibility, lowest storage cost at scale. Requires significantly more assembly to achieve comparable governance: no native pipeline framework with quality expectations, no built-in lineage tracking, no data product primitives. The governance overhead to reach production-grade quality enforcement is high.

**Azure Synapse**: similar trade-offs to AWS Lake Formation. Better Microsoft ecosystem integration. Weaker data product model and no equivalent to DLT's declarative quality expectations.

**Local / dbt + DuckDB**: appropriate for exploration notebooks. Cannot implement the access control, lineage, or audit trail that production requires. This stack is used for exploration; it is not the production platform.

### Rationale

- **Unity Catalog** provides catalog-level domain isolation as a first-class governance primitive. Access grants, automated lineage tracking, tag-based metadata, and audit logging are built in — not assembled from parts.
- **Delta Lake** provides the storage guarantees needed for the medallion architecture: ACID transactions, schema enforcement at write time, time travel for versioned access (ADR-12), and the transaction log that implements Bronze immutability (ADR-09).
- **DLT (Lakeflow Spark Declarative Pipelines)** provides declarative pipeline definitions with `@dlt.expect_or_quarantine` quality enforcement inline — directly implementing the quality layer from ADR-09 and ADR-22 without a separate framework.
- The Free tier provides full Unity Catalog functionality, confirming this is not a compromised platform choice.
- The Databricks life sciences reference architecture provides validated patterns for the clinical and genomics workloads this project implements.

### Consequences

- All storage uses Delta Lake format; Parquet without Delta metadata, Iceberg, and other formats are not used in the production pipeline
- Domain isolation is enforced at the Unity Catalog catalog level; pipelines cannot read across domain boundaries without explicit service principal grants
- Schema map: `discovery.bronze`, `discovery.silver`, `discovery.gold`; `clinical.bronze`, `clinical.silver`, `clinical.gold`; `reference.raw`, `reference.curated`
- **Exploration vs production**: exploration notebooks run in a personal schema (e.g., `personal.exploration`) without governance obligations. Production pipelines start with full governance from the first commit — there is no gradual upgrade path from prototype to production pipeline quality. One well-governed pipeline is preferred over multiple ungoverned ones.

### Compliance implications

- Delta Lake transaction log provides an immutable, auditable record of every write operation, satisfying ALCOA+ Enduring and Attributable requirements
- Unity Catalog audit logs record all access events, satisfying the FDA 21 CFR Part 11 access trail requirement for electronic records
- Schema enforcement at write time (Delta strict mode on Silver and Gold tables) provides the data integrity guarantee required before cross-domain publication

### Assumptions

- The Databricks Free tier maintains full Unity Catalog functionality as currently documented
- A single workspace is used; multi-workspace federation is not required at this stage
- Cloud provider and region are the defaults for the free workspace; no specific cloud infrastructure decisions are required at this stage

### Review trigger

When the project is deployed for use by an external organisation or in a regulated clinical context, evaluate whether the Databricks tier, pricing model, and cloud region are appropriate for that deployment.
