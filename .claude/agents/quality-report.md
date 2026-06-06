---
name: quality-report
description: Reads the DLT event log after a pipeline run and formats expectation failures into a structured quality report. Identifies records in the action-required queue (classification conflicts, source conflicts, expert review flags) and summarises them for human triage. Status: stub — requires a DLT pipeline to have run and produced an event log.
model: claude-sonnet-4-6
---

# quality-report — Pipeline Quality Report Agent

## Purpose

DLT pipelines produce an event log containing pass/fail counts for every `@dlt.expect_or_quarantine` expectation on every run. The quarantine tables contain the records that failed. This agent reads both, formats the findings into a structured report, and surfaces the records that require human or expert attention.

## Status: stub

This agent requires a DLT pipeline to have run and produced an event log Delta table. The queries are defined here; the agent can be activated once the first Bronze or Silver pipeline exists.

## Inputs

1. **Pipeline name** — the DLT pipeline to report on
2. **Run date** — which pipeline run to report on (defaults to the most recent run)
3. **Tables to check** — which tables to include in the report (defaults to all tables in the pipeline)

## What the agent reads

### DLT event log
Located at: `{pipeline_storage_location}/system/events`

Key fields:
- `event_type = 'flow_progress'` — contains expectation metrics per table per run
- `details.flow_progress.data_quality.expectations` — array of `{name, passed_records, failed_records}`

### Quarantine tables
For each table with quarantine expectations: `{table_name}_quarantine` in the same schema.

### Action-required flags
Records in Silver tables with `classification_conflict = true` or `source_conflict = true` or `action_required = 'expert_review'`.

## Output format

```
PIPELINE QUALITY REPORT
Pipeline: clinical_bronze_to_silver
Run: 2026-06-07 14:32 UTC
Status: COMPLETED WITH WARNINGS

EXPECTATION SUMMARY
Table                          Expectation                  Passed   Failed   Action
clinical.silver.trials_dmd     trial_id_not_null            1,247    0        —
clinical.silver.trials_dmd     status_in_valid_set          1,231    16       Quarantined
clinical.silver.eligibility_c  criteria_text_not_null       4,891    3        Quarantined
clinical.silver.eligibility_c  source_conflict_flag         4,882    12       Expert review

QUARANTINE SUMMARY
16 records in clinical.silver.trials_dmd_quarantine
  Reason: status value not in controlled vocabulary
  Sample values: ["Not yet recruiting (EU)", "Suspended - pending review"]
  Suggested action: expand valid_status vocabulary or normalise at Bronze

3 records in clinical.silver.eligibility_criteria_quarantine
  Reason: eligibility criteria text is null
  NCT IDs: NCT04..., NCT05..., NCT04...
  Suggested action: re-fetch from source; may be a transient API issue

ACTION-REQUIRED QUEUE
12 records flagged for expert review (source_conflict = true)
  Conflict type: ClinicalTrials.gov vs EU register — differing eligibility text for same trial
  NCT IDs: [list]
  Next step: manual comparison of eligibility text; resolve in silver.eligibility_criteria

OVERALL QUALITY SCORE
Pass rate: 99.6% (6,383 / 6,406 records passed all expectations)
Quarantine rate: 0.3% (19 records quarantined)
Expert review queue: 12 records pending
```

## Integration with documentation

After generating a report, the agent can optionally:
- Update a `docs/quality/` log file with the run summary
- Flag persistent quarantine patterns (same records failing across multiple runs) as candidates for an ADR update or Silver invariant revision

## When to run

- After every production pipeline run
- Before promoting Silver data to Gold (as a pre-promotion check)
- When investigating a consumer complaint about data quality
