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

## References

**Books**
- FDE ch6–8: pipeline architecture and physical design — data layout decisions that affect query performance; partitioning is a physical design choice that must follow, not precede, real query pattern observation
- DDIA ch3: storage engines and data structures — the conceptual foundation for why data locality on disk affects scan performance; explains why Z-ordering and clustering work

**Databricks documentation**
- [Delta Lake OPTIMIZE and ZORDER](https://docs.databricks.com/en/delta/optimize.html) — the OPTIMIZE command and ZORDER BY clause; how to trigger compaction and multi-dimensional clustering; file size targets and when to run
- [Liquid Clustering](https://docs.databricks.com/en/delta/liquid-clustering.html) — the current recommended alternative to static partitioning for most Delta tables; adaptive clustering that does not require upfront partition column selection and can be changed without rewriting the table

---

## Decision (to be filled in when triggered)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed when query performance threshold is crossed.*