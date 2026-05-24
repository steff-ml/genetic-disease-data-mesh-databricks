# ADR-22: Data Quality Monitoring Framework

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-09 (medallion layer invariants — the invariants define the quality rules; the monitoring framework surfaces them), ADR-21 (pipeline framework — DLT has built-in quality expectations that shape what a separate monitoring layer needs to add)
**Blocks:** Quality SLA enforcement for data products

---

## The Problem

Data quality has two separate concerns that are often conflated: enforcement (bad records must not reach Gold) and monitoring (quality trends must be visible over time so degradation is caught before it reaches consumers). ADR-09 addresses enforcement — the layer invariants and DLT expectations stop bad records at the pipeline boundary. This ADR addresses monitoring: how quality metrics are measured, stored, surfaced, and acted on across the lifecycle of a data product.

---

## Knowledge Required

**DLT expectations as the primary enforcement layer**: If DLT is chosen (ADR-21), `@dlt.expect_or_quarantine` provides inline enforcement with per-expectation pass/fail metrics available in the DLT event log. The event log is a Delta table — it can be queried directly to produce quality trend dashboards. This may reduce what a separate monitoring framework needs to add.

**Quality dimensions to cover**: Completeness (required fields populated), validity (values within expected ranges or controlled vocabularies), consistency (relationships between fields hold — e.g., an exon deletion range that is internally contradictory), timeliness (source data freshness — when was ClinicalTrials.gov last ingested?), uniqueness (no duplicate trial records after normalisation).

**SLA definition**: Each Gold data product has a quality SLA (from the data contract). The monitoring framework must be able to confirm or breach that SLA on each pipeline run. A breach must trigger an alert — not just log a metric — because Gold consumers depend on the SLA being met.

**Unity Catalog quality dashboards**: Databricks has native quality monitoring features in Unity Catalog (Lakehouse Monitoring). This can auto-profile Delta tables and detect drift in column distributions without custom code. Relevant for detecting when the distribution of extracted eligibility criterion types changes — a signal that the extraction model or source data has changed.

**Custom quality tables**: A lightweight alternative — write a quality metrics table after each pipeline run with one row per pipeline run per table, recording pass/fail counts per expectation. Simple, portable, queryable from any SQL tool. This is the fallback if DLT event logs or Lakehouse Monitoring do not cover the required dimensions.

---

## Decision (to be filled in before Silver layer build)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the Silver layer is built.*