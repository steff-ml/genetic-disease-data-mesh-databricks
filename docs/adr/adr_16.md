# ADR-16: Partitioning and Z-Order Optimisation

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Deferred
**Trigger:** Match query latency on the full trial catalogue exceeds 30 seconds.
**Depends on:** Independent — no upstream ADR dependency
**Blocks:** Nothing — default Delta Lake settings apply until triggered

---

## Current position

Default Delta Lake settings apply. No partitioning or Z-ordering configured. This is deliberate: partitioning decisions made before real query patterns are known optimise for the wrong thing.

---

## Knowledge Required When Triggered

Delta Lake optimisation documentation: OPTIMIZE command, ZORDER BY for multi-dimensional clustering, Liquid Clustering (the replacement for static partitioning in newer Delta versions) — understand the trade-offs before choosing.

Actual query patterns from usage — partitioning and Z-order decisions require real query logs. The columns to Z-order are the ones that appear most frequently in WHERE and JOIN predicates in actual queries, not hypothetical ones.

Data volume actuals — partitioning strategy depends on row counts. A trial catalogue with 500 rows does not need partitioning. A patient mutation catalogue with millions of variants may. Neither can be decided before data exists.

---

## Decision (to be filled in when triggered)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed when query performance threshold is crossed.*