# ICH E6(R3) Good Clinical Practice — Compliance Checklist

ICH E6(R3) GCP is the international standard for conducting and documenting
clinical trials involving human subjects. For this project, GCP requirements
apply when patient-level data from a clinical trial enters the system (Phase 4+).

**Who needs this checklist:** anyone building or reviewing pipelines that ingest,
store, or expose patient-level clinical trial data.

**When to run through this checklist:** before Phase 4 patient data enters the
system, and again before any Gold table containing patient data goes to "active".

This checklist is not legal advice. For a binding compliance review, engage your
institution's Clinical Research Operations or a contract research organisation (CRO).

---

## Section 1 — Electronic Source Data Requirements (ICH E6(R3) §5.5.3)

GCP requires that electronic records be as complete, accurate, readable, and
verifiable as paper records would be. For Databricks-hosted data:

- [ ] **Audit trail enabled on all patient tables.** Delta's change data feed
  captures who wrote what and when. Verify with `audit_trail_config.py`:
  ```
  python hub/templates/audit_trail_config.py --catalog clinical --schema gold --check-schema
  ```

- [ ] **Records are attributable.** Every Bronze row must carry `source_system`,
  `ingestion_timestamp`, and `api_version` (ALCOA+ provenance from `dlt_bronze_table.py`).
  Post-ingestion changes must be logged via the Delta change log — never overwrite rows.

- [ ] **Records are legible and retrievable.** Columns use self-explanatory names
  aligned with OMOP CDM or SDTM where relevant. The Unity Catalog table description
  and column comments explain each field. No raw numeric codes without a vocabulary join.

- [ ] **Original data is preserved.** Bronze tables are append-only. Silver
  transformations write to a separate table — they do not modify Bronze. If a Bronze
  record is found to be erroneous, add a correction row with `correction_reason` and
  `corrected_by`; do not delete the original.

- [ ] **Backup and recovery verified.** Confirm that Unity Catalog data is covered
  by your workspace backup policy. Delta time travel provides a rolling window
  (currently 30 days for most workspaces) but is not a substitute for backup.

---

## Section 2 — Audit Trail Requirements (ICH E6(R3) §5.5.3.b)

The audit trail must record who accessed, created, modified, or deleted each record,
and when. ICH E6(R3) requires that audit trail entries are:
- Computer-generated (not manually editable)
- Time-stamped (server time, not client time)
- Retained for the trial lifecycle (see Section 4)

- [ ] **Delta table properties set for 7-year retention.**
  ```
  delta.logRetentionDuration = interval 2555 days
  delta.deletedFileRetentionDuration = interval 2555 days
  ```
  Apply via `audit_trail_config.py`. These properties prevent Delta vacuum from
  removing historical versions that are needed for audit reconstruction.

- [ ] **Change Data Feed enabled.**
  ```
  delta.enableChangeDataFeed = true
  ```
  Allows downstream consumers to subscribe to the change log. Required for
  building a reconciliation trail during a GCP audit.

- [ ] **`_change_type` is monitored.** Rows with `_change_type = "delete"` in the
  CDF log are an audit finding — patient records should never be deleted. Set an
  alert if deletes are detected on Gold patient tables.

- [ ] **Access is logged.** Unity Catalog access logs are written to
  `system.access.audit`. Verify the audit log is enabled in your workspace:
  ```sql
  SELECT * FROM system.access.audit
  WHERE service_name = 'dataAccess'
  AND request_params.table_full_name = 'clinical.gold.patient_trial_eligibility'
  LIMIT 20;
  ```

---

## Section 3 — Data Management Plan (DMP)

GCP requires a DMP that describes how data is collected, validated, cleaned, and
stored. The DMP is a document, not a code artifact — it lives in your study folder
(Teams / SharePoint / eTMF), not in this repository.

The following must be described in the DMP:

- [ ] **Data sources and collection methods.** List all APIs (LOVD, ClinVar, Ensembl,
  EU CTR, ClinicalTrials.gov) and their access methods. Reference `exploratory/notes.md`
  for API-level DQ notes.

- [ ] **Data validation rules.** Reference the DLT `@dlt.expect_or_quarantine` rules
  in the pipeline files and the quality rules in each Gold contract YAML.

- [ ] **Data correction procedures.** Describe how errors in patient records are
  corrected (append correction row) and how corrections are reviewed (action queue).

- [ ] **Database lock and freeze procedures.** Describe when the data is locked
  for analysis (typically after last patient last visit). In Databricks, "locking"
  is achieved by revoking write permissions on the Gold tables and tagging with
  `db_lock_date`.

- [ ] **Data retention and destruction.** Minimum 15 years after trial completion
  per ICH E6(R3) §5.5.7. Confirm your institution's policy — it may be longer.
  Document the responsible party for data destruction at retention expiry.

---

## Section 4 — Data Retention (ICH E6(R3) §5.5.7)

| Data type | Minimum retention |
|-----------|------------------|
| Essential trial documents | 15 years after trial completion |
| Patient-level data | 15 years after trial completion |
| Audit trail records | Same as the records they document |
| Source data (Bronze) | Same as above |

The 7-year Delta table property set by `audit_trail_config.py` is shorter than
ICH E6(R3)'s 15-year requirement. For patient-level Gold tables:
- Set `delta.logRetentionDuration = interval 5475 days` (15 years)
- Archive Parquet snapshots to long-term cold storage (Azure Blob archive tier)
  at the time of database lock

---

## Section 5 — Electronic Signatures (ICH E6(R3) §4.9.0)

If the system captures electronic signatures (e.g., investigator approval of trial
enrollment decisions), those signatures must comply with 21 CFR Part 11 §11.100.

- [ ] **Service principal tokens are not personal.** Each person who accesses
  patient data must authenticate with their individual Databricks identity — not
  a shared service principal. Shared credentials cannot be attributed to a person.

- [ ] **MFA is enabled** for all users with access to patient-level catalogs.
  Verify in the Databricks account console under Identity & Access.

- [ ] **If the system surfaces any decision for investigator sign-off** (e.g., a
  flag that a patient is eligible for a trial), that approval must be captured with
  the approver's identity, timestamp, and the exact record version approved.
  Use Delta's row versioning (`@version`) to capture what was approved.

---

## Section 6 — Access Control (ICH E6(R3) §5.5.2)

GCP requires that only authorised personnel access trial data, and that access
reflects their role in the trial.

- [ ] **PHI access controls applied.** Run `phi_access_control.py` before any
  patient data is loaded. Column masks and row filters enforce role-based access
  at the Unity Catalog engine level — they cannot be bypassed by direct Delta reads.

- [ ] **Access is role-appropriate.** Clinical coordinators see only their assigned
  subjects. Researchers see de-identified cohort data. Direct care teams see full records.
  Verify with `phi_access_control.py --verify`.

- [ ] **Access changes are logged.** Any change to group membership or permission
  grants must be logged in the account audit log. Unity Catalog logs permission changes
  in `system.access.audit` under `service_name = 'accounts'`.

- [ ] **Access is reviewed periodically.** Set a calendar reminder to review group
  membership quarterly. Remove coordinators who have left the study. Revoke researcher
  access at the end of the approved study period.

---

## Section 7 — Before Go-Live: GCP Readiness Sign-off

Run through this final list before the first patient record is written to a
production Gold table.

- [ ] DMP is complete and approved by the principal investigator
- [ ] Audit trail properties are verified on all patient tables
- [ ] PHI access controls are applied and verified
- [ ] Access log is confirmed active (`system.access.audit` contains recent entries)
- [ ] All pipeline engineers have individual Databricks identities (no shared logins)
- [ ] MFA is enabled for all users with clinical data access
- [ ] Data retention policy is documented and backup is confirmed
- [ ] A test audit was performed: pick a random patient row, reconstruct its full
  change history from the Delta log, and verify the history is complete and attributable

---

## Quick Reference — Where GCP Maps to This Project

| GCP Requirement | This Project's Implementation |
|-----------------|-------------------------------|
| Audit trail | `audit_trail_config.py` + Delta CDF |
| Attribution / provenance | ALCOA+ in `dlt_bronze_table.py` |
| Access control | `phi_access_control.py` (ABAC) |
| GDPR erasure vs GCP retention conflict | `docs/adr/adr_24.md` — pseudonymisation policy |
| EHR integration (patient lookup) | `fhir_mapping.py` (Phase 5) |
| Validation rules | `@dlt.expect_or_quarantine` in DLT pipelines |
| Data contract | `docs/contracts/` + `contract_check.py` in CI |
| Electronic signatures | 21 CFR Part 11 via `audit_trail_config.py` |
| Retention | Delta properties (15 yr) + cold storage archive |
| SDTM submission format | `cdisc_sdtm_mapping.py` (Phase 6) |
