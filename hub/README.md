# Platform Hub — Developer Resource Templates

This hub is for **domain engineers building compliant data pipelines** on this mesh.
You do not need to understand every standard cited here before you start. Read the
Quick Start below, follow the decision guide for your current phase, and use the
templates as your baseline — they encode decisions already made in the ADRs.

If something in a template does not make sense, ask the platform team before removing
it. The compliance requirements (21 CFR Part 11, OMOP, HGVS, GCP) have non-obvious
consequences that are documented in the template comments.

---

## Quick Start for Domain Engineers

You are starting a new pipeline. Answer three questions:

**1. Which layer are you building?**
→ Bronze: start with [`dlt_bronze_table.py`](templates/dlt_bronze_table.py)
→ Silver: start with [`dlt_silver_table.py`](templates/dlt_silver_table.py)
→ Gold: start with [`dlt_gold_table.py`](templates/dlt_gold_table.py)

**2. Does your table contain variant data (HGVS notation)?**
→ Yes: also read [`hgvs_normalization.py`](templates/hgvs_normalization.py) before writing Silver.
  Normalization must happen before any join — otherwise the ADR-06 conflict
  detection will produce false matches and false conflicts.

**3. Does your table contain patient identifiers or clinical measurements?**
→ Yes (Phase 4+): also read [`phi_access_control.py`](templates/phi_access_control.py).
  Do not deploy a patient-level table without the column masks and row filters in place.
  This is a hard requirement — it is not optional when patient data is present.

---

## Template Decision Guide

### Starting a pipeline (all domains)

| Situation | Template | Required? |
|-----------|----------|-----------|
| Writing any Bronze table | `dlt_bronze_table.py` | Yes |
| Writing any Silver table | `dlt_silver_table.py` | Yes |
| Publishing a Gold data product | `dlt_gold_table.py` + a contract in `docs/contracts/` | Yes |
| Validating a contract before release | `contract_check.py` | Yes — run in CI |

### Handling variants (Discovery domain, Phases 2–4)

| Situation | Template | When |
|-----------|----------|------|
| Ingesting LOVD or ClinVar | `hgvs_normalization.py` | Before Silver transformation |
| Cross-source variant matching (ADR-06) | `hgvs_normalization.py` + `dlt_silver_table.py` | Phase 3 |
| Publishing variant catalogue for external consumers | `ga4gh_vrs_normalization.py` | Phase 3 Silver → Gold |

**Why both HGVS and VRS?** HGVS is human-readable notation used by clinicians and databases
(e.g. `NM_004006.2:c.6439del`). VRS is a machine-stable digest used for cross-system
interoperability (e.g. `ga4gh:VA.abc123`). Silver stores HGVS for readability; the Gold
data product exposes VRS IDs for programmatic consumers (Terra, gnomAD, GA4GH APIs).

### Handling patient data (Phases 4–5)

| Situation | Template | When |
|-----------|----------|------|
| Any table with a patient identifier | `phi_access_control.py` — column masks + row filters | Before first data load |
| Sharing patient-level data across domains | `cross_domain_interface.py` + `phi_access_control.py` | Phase 5 |
| EHR integration (clinician looks up a patient) | `fhir_mapping.py` | Phase 5 |
| GDPR erasure request against retained trial data | See `docs/adr/adr_24.md` for the pseudonymisation policy | Before Phase 4 go-live |

**ABAC vs RBAC:** This project uses Unity Catalog **Attribute-Based Access Control (ABAC)**
for patient data. ABAC is more appropriate than simple role-based grants here because:
- A clinical coordinator should see only their assigned patients, not all patients with that role
- A researcher approved for a specific study should see only study-relevant data
- New columns added to a PHI table are automatically masked if tagged correctly

ABAC is implemented via Unity Catalog column masks and row filters that reference
`IS_MEMBER()` and `CURRENT_USER()` — see `phi_access_control.py` for the full pattern.

### Clinical standards alignment (Clinical domain, Phases 1, 5)

| Standard | Template | When |
|----------|----------|------|
| OMOP CDM 5.3.1 (analytical interoperability) | `omop_cdm_mapping.py` | Phase 1.4 vocabulary mapping, Phase 4 patient profiles |
| CDISC SDTM (regulatory submission format) | `cdisc_sdtm_mapping.py` | Phase 6 Marketplace publishing; earlier if sponsor data is received in SDTM |
| ICH E6 GCP (Good Clinical Practice) | `ich_e6_gcp_checklist.md` | Before any patient-level data enters the system |

**OMOP vs CDISC — when to use which:**
- Use **OMOP CDM** for analytical Gold tables consumed by EHR systems, real-world evidence
  platforms, and research queries. OMOP is optimised for querying across a patient cohort.
- Use **CDISC SDTM** when producing outputs for regulatory submissions (FDA, EMA) or when
  receiving sponsor clinical trial data that arrives in SDTM format. SDTM is optimised for
  submission, not analysis.
- For most tables in this project, OMOP is the right standard. SDTM is needed only if
  a sponsor provides raw trial data or if the platform outputs feed a regulatory package.

### Compliance and governance

| Requirement | Template | When |
|-------------|----------|------|
| 21 CFR Part 11 audit trail | `audit_trail_config.py` | Every table, at creation time |
| Contract CI enforcement | `.github/workflows/contract_ci.yml` | Before first PR merge to main |
| GenAI extraction (eligibility criteria parsing) | `genai_extraction_pipeline.py` | Phase 1.3 |
| Consuming a cross-domain data product | `cross_domain_interface.py` | Phase 5 |

---

## Standards Reference

| Standard | Scope | Templates that implement it |
|----------|-------|----------------------------|
| **Bitol ODCS v3** | Data contract format for all Gold tables | `dlt_gold_table.py`, `contract_check.py` |
| **ALCOA+** | Provenance requirements on every Bronze row | `dlt_bronze_table.py` |
| **HGVS (HGVS Nomenclature v21)** | Variant notation for LOVD and ClinVar | `hgvs_normalization.py` |
| **GA4GH VRS v2** | Machine-stable variant IDs for external interoperability | `ga4gh_vrs_normalization.py` |
| **HL7 FHIR R4** | EHR integration API for individual patient lookups | `fhir_mapping.py` |
| **OMOP CDM 5.3.1** | Analytical clinical data model | `omop_cdm_mapping.py` |
| **CDISC SDTM v3.3** | Regulatory submission tabulation model | `cdisc_sdtm_mapping.py` |
| **ICH E6(R3) GCP** | Good Clinical Practice for electronic records | `ich_e6_gcp_checklist.md` |
| **21 CFR Part 11** | Electronic records and audit trail for clinical data | `audit_trail_config.py` |
| **GDPR / HIPAA** | Privacy, access control, and right to erasure | `phi_access_control.py`, `adr_24.md` |
| **ISO 25237:2017** | Pseudonymisation policy for GDPR/GCP conflict | `docs/adr/adr_24.md` |
| **MLflow Model Registry** | GenAI model governance for batch inference | `genai_extraction_pipeline.py` |
| **FAIR (Wilkinson 2016)** | Findable, Accessible, Interoperable, Reusable | Unity Catalog tags in all Gold templates |

---

## Compliance checklist before a Gold table goes to "active"

Use this list before setting `status: active` in the contract YAML.

- [ ] Contract YAML exists at `docs/contracts/<table_name>.yaml`
- [ ] `contract_check.py` passes with zero errors
- [ ] All tables have 21 CFR Part 11 Delta properties set (`audit_trail_config.py`)
- [ ] If the table contains PHI: column masks and row filters applied (`phi_access_control.py`)
- [ ] If the table contains variant data: HGVS normalization applied in Silver upstream
- [ ] If the table is a Gold data product exposed externally: VRS IDs present alongside HGVS
- [ ] `pipeline_version` is set and bumped
- [ ] Unity Catalog tags (`domain`, `product`, `disease`, `standard`) are set
- [ ] CI workflow passes on the PR (`contract_ci.yml`)

---

## All templates

| File | Standard(s) | Phase |
|------|-------------|-------|
| [`dlt_bronze_table.py`](templates/dlt_bronze_table.py) | ALCOA+, 21 CFR Part 11 | All |
| [`dlt_silver_table.py`](templates/dlt_silver_table.py) | ADR-06, ALCOA+ | All |
| [`dlt_gold_table.py`](templates/dlt_gold_table.py) | Bitol ODCS, FAIR, 21 CFR Part 11 | All |
| [`contract_check.py`](templates/contract_check.py) | Bitol ODCS | All (CI) |
| [`hgvs_normalization.py`](templates/hgvs_normalization.py) | HGVS Nomenclature v21 | Phase 3 |
| [`ga4gh_vrs_normalization.py`](templates/ga4gh_vrs_normalization.py) | GA4GH VRS v2 | Phase 3 Gold |
| [`omop_cdm_mapping.py`](templates/omop_cdm_mapping.py) | OMOP CDM 5.3.1 | Phase 1.4, 4 |
| [`cdisc_sdtm_mapping.py`](templates/cdisc_sdtm_mapping.py) | CDISC SDTM v3.3 | Phase 6 |
| [`phi_access_control.py`](templates/phi_access_control.py) | GDPR, HIPAA, ABAC | Phase 4 |
| [`genai_extraction_pipeline.py`](templates/genai_extraction_pipeline.py) | MLflow Model Registry | Phase 1.3 |
| [`audit_trail_config.py`](templates/audit_trail_config.py) | 21 CFR Part 11 | All |
| [`cross_domain_interface.py`](templates/cross_domain_interface.py) | Bitol ODCS | Phase 5 |
| [`fhir_mapping.py`](templates/fhir_mapping.py) | HL7 FHIR R4 (Patient, Observation, Condition) | Phase 5 |
| [`ich_e6_gcp_checklist.md`](templates/ich_e6_gcp_checklist.md) | ICH E6(R3) GCP | Phase 4 |
| [`.github/workflows/contract_ci.yml`](../.github/workflows/contract_ci.yml) | Bitol ODCS, ADR-06 | All (CI) |
