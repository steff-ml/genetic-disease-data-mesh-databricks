# ADR-09: Medallion Layer Invariants

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-01 (data mesh paradigm), ADR-02 (Databricks platform). Silver invariants also depend on ADR-06 (canonical data sources).
**Blocks:** Quality constraint design, audit trail approach

---

## Knowledge Required

FDA Data Integrity Guidance (2018) — what immutability and audit trail mean in a regulated context. Defines the Bronze invariant: data must be raw as-received with full provenance, no transformation permitted.

ICH E6(R3) sections 4-5 — data governance obligations (data accuracy, legibility, contemporaneity, originality, attributability) that translate to layer guarantees in a clinical research context.

Delta Lake documentation: time travel, transaction log, deletion vectors — the technical mechanisms that implement immutability and audit trail at the storage layer.

DLT expectations documentation — how to express quality constraints as pipeline-enforced rules with quarantine table patterns so bad records are isolated rather than dropped.

ClinicalTrials.gov data quality actuals — what is actually encountered when ingesting it (missing fields, inconsistent date formatting, free-text criterion fields). Silver invariants cannot be written until real data quality is known.

---

## Partial Decision

Bronze invariant: Immutable, raw as-received, full provenance metadata (source, ingestion timestamp, API version), no transformation permitted.

Silver invariant: Deferred until first Bronze ingestion — actual data quality must be seen before realistic conformance constraints can be written.

---

## References

**Books**
- FDE ch6–8: pipeline architecture, data quality enforcement, and audit trail patterns
- DDIA ch3: storage engines and how append-only semantics implement immutability
- DDIA ch10–11: batch and stream processing patterns relevant to Bronze ingestion guarantees

**Databricks documentation**
- [Delta Lake overview](https://docs.databricks.com/en/delta/index.html) — ACID guarantees, append-only semantics, and the transaction log that implement Bronze immutability
- [Delta Lake time travel](https://docs.databricks.com/en/delta/history.html) — how the Bronze immutability story holds even when data corrections are needed: append, never overwrite
- [Delta Live Tables overview](https://docs.databricks.com/en/dlt/index.html) — the pipeline framework for implementing Silver layer quality constraints and transformations (now called Lakeflow Spark Declarative Pipelines)
- [DLT expectations](https://docs.databricks.com/en/dlt/expectations.html) — how to write conformance rules as first-class pipeline components; directly implements Silver layer invariants

**Regulatory references**
- FDA Data Integrity Guidance (2018)
- ICH E6(R3) sections 4–5

---

## Decision (to be filled in)

*Context, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed in two stages: Bronze invariants before Bronze build; Silver invariants before Silver build.*