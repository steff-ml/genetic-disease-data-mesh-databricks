# ADR-12: Cross-Domain Contract Enforcement Mechanism

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-03 (domain boundary principle), ADR-08 (versioning and lifecycle strategy)
**Blocks:** External publication of genomic domain products

---

## Knowledge Required

Unity Catalog table properties documentation — how to store version metadata as a table property so consumer pipelines can read the declared contract version programmatically and fail fast if a breaking change is detected.

Delta Lake time travel documentation — how to pin a consumer pipeline to a specific table version using VERSION AS OF or TIMESTAMP AS OF. Time travel is the safety net during breaking change absorption: consumers can stay on the previous version while migrating.

Schema evolution documentation — what Delta enforces automatically at write time (schema enforcement flag) versus what requires explicit migration logic. Delta schema enforcement catches structural breaks at the pipeline layer before bad data reaches consumers.

Consumer tolerance for breaking changes: for a prototype with one internal consumer, this is simple. For an open-source project with external consumers, a deprecation policy and notice period are needed. The mechanism must scale from one consumer to many without replacement.

Bitol Open Data Contract Standard — the YAML-based contract format used in this project for publishing schema, SLA, update frequency, and licence terms alongside the data product.

---

## Partial Decision

Version stored as Unity Catalog table property. Consumer pipelines declare version dependency explicitly in code. Delta schema enforcement catches structural breaks at write time. Time travel used as safety net during breaking change absorption.

---

## Decision (to be filled in)

*Context, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the first cross-domain product is published.*