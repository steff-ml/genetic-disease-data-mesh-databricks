---
name: schema-validator
description: Compares the actual schema of a Delta table in Unity Catalog against its declared Bitol YAML contract and reports any drift. Run on demand before a PR or after a pipeline change to catch contract violations before they reach consumers. Status: stub — requires Databricks workspace access to be fully implemented.
model: claude-sonnet-4-6
---

# schema-validator — Contract Compliance Checker

## Purpose

Every Gold data product has a Bitol YAML contract declaring its schema, quality SLA, and version (ADR-04). Schema drift — where the actual table schema diverges from the declared contract — breaks consumer pipelines and violates the data product guarantee. This agent detects drift before it reaches consumers.

## Status: stub

This agent requires read access to the Databricks workspace (via Databricks Connect or the Unity Catalog REST API) to fetch the actual table schema. The logic is defined here; implementation depends on the workspace being configured for local access.

## Inputs

1. **Table identifier** — full Unity Catalog name, e.g., `discovery.gold.patient_mutation_profile`
2. **Contract file path** — path to the Bitol YAML, e.g., `docs/contracts/patient_mutation_profile.yaml`

## What the agent checks

### Schema conformance
For each column in the contract schema:
- Is the column present in the actual table?
- Does the actual type match the declared type?
- Does the actual nullability match the declared nullability?

For each column in the actual table:
- Is the column declared in the contract? (undeclared columns are a minor violation — they may be internal fields not yet added to the contract)

### Version consistency
- Does the `contract_version` tag on the Unity Catalog table match the `version` field in the YAML?
- If not, flag as a version mismatch — either the table was updated without bumping the contract version, or the contract was updated without tagging the table.

### Quality expectation coverage
- Are the quality expectations declared in the contract (`@dlt.expect_or_quarantine` patterns) present in the DLT pipeline code?
- This check is best-effort — it requires reading the pipeline source file.

## Output format

```
SCHEMA VALIDATION REPORT
Table: discovery.gold.patient_mutation_profile
Contract: docs/contracts/patient_mutation_profile.yaml
Contract version: 1.2.0
Table tag version: 1.2.0 ✓

COLUMN CHECKS
✓  patient_id          STRING NOT NULL    matches contract
✓  variant_class       STRING NOT NULL    matches contract
✗  reading_frame_effect  contract: STRING NOT NULL
                          actual:  STRING NULLABLE    — BREAKING: nullability mismatch
⚠  hotspot_region      present in table, not in contract  — minor: undeclared column

SUMMARY
1 breaking violation (column nullability mismatch)
1 minor violation (undeclared column)
0 version mismatches

Action required: increment contract major version before next consumer pipeline run.
```

## When to run

- Before every PR that includes changes to a Gold table or its producing pipeline
- After any `ALTER TABLE` or schema migration on a Gold table
- As part of the CI pipeline (future: GitHub Actions step before merge)

## Implementation notes

When Databricks Connect is configured:
```python
from databricks.connect import DatabricksSession
spark = DatabricksSession.builder.getOrCreate()
actual_schema = spark.table("discovery.gold.patient_mutation_profile").schema
```

The YAML contract schema can be parsed with `PyYAML` and compared field-by-field. The full implementation is straightforward once workspace access is confirmed.
