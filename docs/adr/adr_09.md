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

## Decision (to be filled in)

*Context, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed in two stages: Bronze invariants before Bronze build; Silver invariants before Silver build.*