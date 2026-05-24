# ADR-21: Pipeline Framework — DLT vs Spark Jobs

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-02 (Databricks — framework must be available on the platform), ADR-09 (medallion layer invariants — invariants constrain what the pipeline must enforce)
**Blocks:** Pipeline implementation design, ADR-22 (quality monitoring), ADR-23 (test strategy)

---

## The Decision Space

**Delta Live Tables (DLT)**: Databricks' declarative pipeline framework. Pipelines are defined as a DAG of `@dlt.table` and `@dlt.view` decorated functions. DLT manages checkpointing, restarts, and incremental processing automatically. Built-in `@dlt.expect` and `@dlt.expect_or_quarantine` decorators enforce quality constraints inline and route failing records to quarantine tables. Unity Catalog lineage is tracked automatically at the table level.

**Standard Spark Jobs**: Python or Scala scripts submitted as Databricks jobs. Full flexibility — any Spark API, any orchestration pattern. Easier to unit test in isolation (no DLT runtime dependency). Manual checkpoint and restart management. Lineage must be tracked explicitly or via Unity Catalog if using Delta writes. Quality constraints require a separate framework (custom expectations, Great Expectations, or dbt tests).

**Hybrid**: DLT for ingestion and transformation (Bronze → Silver → Gold); standard jobs for orchestration, one-off operations, and anything DLT cannot express (e.g., Python-heavy extraction logic that does not fit the declarative model).

---

## Knowledge Required

DLT documentation — pipeline modes (triggered vs continuous), the `@dlt.expect_or_quarantine` pattern for quality enforcement, streaming vs batch source handling, Unity Catalog integration.

DLT limitations — what DLT cannot do well: arbitrary Python logic between table definitions, fine-grained error handling per record outside of expectations, external API calls within a DLT pipeline (relevant for the Claude extraction step). The extraction pipeline may need to live outside DLT for this reason.

Standard Spark job documentation — Databricks job clusters, task dependencies, retry logic, parameter passing. Relevant if extraction runs as a job rather than a DLT pipeline.

Testing implications — DLT pipelines run inside the DLT runtime and are harder to unit test than plain Python functions. Testing a DLT pipeline requires either running it (integration test) or extracting the transformation logic into testable functions called by the DLT definitions. This is a known friction point. The test strategy (ADR-23) depends on this decision.

Cost implications — DLT adds a DBU multiplier on top of standard compute costs. For a prototype with low data volume, this is negligible. For a production pipeline running continuously, the cost difference is material.

---

## Decision (to be filled in before Bronze build)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the first pipeline is built.*