# ADR-24: GDPR Right to Erasure vs GCP 15-Year Retention — Pseudonymisation Policy

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Working Decision
**Depends on:** ADR-03 (domain boundaries), ADR-06 (canonical sources)
**Blocks:** Phase 4 patient data ingestion; any pipeline that writes a `patient_id` to a Silver or Gold table

---

## Knowledge Required

- GDPR Article 17 (right to erasure) and Article 89 (scientific research derogation)
- ICH E6(R3) §5.5.7 (essential document retention, minimum 15 years post-trial)
- 21 CFR Part 11 §11.10 (electronic record integrity — records cannot be altered or deleted without a traceable audit entry)
- EDPB Guidelines 05/2020 on consent for scientific research
- ISO 25237:2017 — Pseudonymization in health informatics

---

## References

**Regulations**
- GDPR Art. 17: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay."
- GDPR Art. 89(1): Member states may derogate from Art. 17 "where personal data are processed for archiving purposes in the public interest, scientific or historical research purposes or statistical purposes" subject to appropriate safeguards.
- ICH E6(R3) §5.5.7: Essential documents shall be retained for at least 15 years after trial completion, or longer if required by applicable regulatory requirements.
- 21 CFR Part 11 §11.10(e): Audit trail records shall not be able to be disabled or altered by the same individuals responsible for the records.

**Standards**
- ISO 25237:2017: Defines pseudonymization as "a particular type of de-identification that both removes the association with a data subject and adds an association between a particular set of characteristics relating to the data subject and one or more pseudonyms."

---

## Decision

### Context

From Phase 4 onward, the platform stores patient-level clinical data. GDPR grants EU data subjects the right to request erasure of their personal data (Art. 17). ICH E6(R3) simultaneously requires that trial records be retained for a minimum of 15 years after trial completion. These two obligations conflict directly: a patient cannot exercise erasure rights without destroying records that GCP and regulatory law require to be kept.

The conflict cannot be resolved by choosing one obligation over the other — both are legally binding in the relevant jurisdictions. The resolution must satisfy both simultaneously.

Three facts make a technical resolution possible:

1. GDPR Art. 89(1) permits member states to restrict Art. 17 rights for scientific research where "appropriate safeguards" are in place. However, relying solely on this derogation is fragile — the patient can contest the research exemption and the derogation's scope varies by member state.

2. Once data is pseudonymised such that re-identification is not reasonably possible, it no longer constitutes personal data under GDPR (Recital 26). Therefore, destroying the re-identification key converts the retained record from personal data (subject to GDPR) to pseudonymous data (not subject to GDPR). This satisfies Art. 17 without destroying the trial record.

3. The trial record itself (variant, diagnosis, treatment, outcome) does not contain the patient's identity — it contains a pseudonymous identifier. Destroying the key makes the record effectively anonymous while preserving its scientific and regulatory value intact.

### Decision

**Pseudonymisation with a separately-held key, destroyed on valid erasure request.**

The architecture is as follows:

**At ingestion (Phase 4 Bronze → Silver):**
- Patient identifiers (name, DOB, national ID) are extracted from the source system and encrypted using a per-patient key stored in Azure Key Vault.
- The Bronze table row receives a `pseudonymous_id` (a HMAC-SHA256 digest of the national ID, salted per-study) instead of the direct identifier.
- The direct identifiers are stored separately in `clinical.phi.patient_identity` — a restricted table with Tier 1 ABAC masks applied per `phi_access_control.py`.
- The Bronze pipeline never writes raw identifiers to any table that reaches Silver or Gold.

**On a valid erasure request:**
1. The patient's `pseudonymous_id` is determined from the identity table.
2. The patient's row in `clinical.phi.patient_identity` is deleted (this is the only row that links `pseudonymous_id` back to the natural person).
3. The per-patient Azure Key Vault key is destroyed.
4. A deletion record is written to the audit log: `erasure_requested: true`, `erasure_date`, `erasing_user`, `pseudonymous_id`. The audit record does not contain the patient's identity.
5. All Silver and Gold rows keyed by `pseudonymous_id` are retained unchanged — they are now pseudonymous data under GDPR Recital 26 and therefore no longer personal data. ICH E6(R3) retention obligations are met.

**For the GDPR Art. 89 scientific research exemption (belt-and-suspenders):**
- Consent forms must explicitly state that data will be retained for regulatory purposes in pseudonymised form even after an erasure request.
- The Data Management Plan must document this policy.
- Ethics Committee / IRB approval must cover this retention practice.

This dual approach — pseudonymisation as the primary mechanism, Art. 89 as a documented secondary basis — is the most defensible position in an audit by a data protection authority.

---

### Alternatives considered

**Delete all records on erasure request:**
Violates ICH E6(R3) §5.5.7 and 21 CFR Part 11. Regulatory authorities can reject trial data during inspection if records are incomplete. A trial where patient records were deleted cannot be submitted for regulatory approval. Rejected.

**Rely solely on GDPR Art. 89 research exemption:**
Legally valid in principle, but the derogation scope varies by EU member state (not all have transposed it identically) and is contestable by the data subject. A patient who disputes the exemption can escalate to the national supervisory authority. Pseudonymisation is a stronger, less contestable position. Used as secondary basis only.

**Full anonymisation at the time of first write:**
Anonymisation (irreversible) is stronger than pseudonymisation for GDPR but creates a different problem: the trial record cannot be linked back to the patient for safety monitoring, follow-up, or adverse event reporting during the active trial. GCP requires that the investigator can identify a patient and report an adverse event. Anonymisation during the active trial is incompatible with GCP. Rejected.

**Tokenisation with a central token service:**
Functionally similar to pseudonymisation but adds a third-party token service (e.g., Privitar, Databricks Clean Rooms). Increases operational complexity and cost without a meaningful additional benefit over Key Vault-based pseudonymisation for this project's scale. Deferred unless the number of participating sites or jurisdictions makes a dedicated tokenisation service necessary.

### Rationale

Pseudonymisation with key destruction satisfies both legal frameworks simultaneously without relying on a derogation that could be contested. It is the approach recommended by the European Data Protection Board's guidelines on scientific research and is consistent with ISO 25237:2017. The approach is implementable within Unity Catalog ABAC + Azure Key Vault without additional vendor dependencies.

### Consequences

- **PHI table architecture**: `clinical.phi.patient_identity` is a separate, ABAC-controlled table. It is the only place where the link between `pseudonymous_id` and the natural person exists. Its access is limited to `phi_full_access` group only.
- **Erasure process**: a formal erasure request handling process must be documented in the DMP and assigned to a responsible party (typically the site coordinator or data manager). The process is manual by design — it must include confirmation that the correct patient is being erased before the key is destroyed.
- **Downstream joins**: Silver and Gold tables join on `pseudonymous_id`. No pipeline should ever join on a natural identifier.
- **FHIR layer**: the FHIR Patient resource (see `fhir_mapping.py`) uses `pseudonymous_id` as its identifier. No FHIR resource contains a direct identifier.
- **Audit trail**: the erasure audit record (pseudonymous_id + date + requesting user) is retained indefinitely. This is not personal data under GDPR Recital 26 and does not need to be erased.
- **Genomic data re-identification risk**: genomic variant data (HGVS notation, exon deletions) is quasi-identifying for rare variants. Destroying the key reduces but does not eliminate re-identification risk. The ABAC controls on Gold tables (research access only) are a necessary second layer of protection. Document this residual risk in the Data Protection Impact Assessment (DPIA).

### Compliance implications

- **GDPR Art. 17**: satisfied by key destruction — the remaining record is pseudonymous and no longer personal data.
- **GDPR Art. 89**: satisfied as secondary basis, documented in consent form, DMP, and Ethics approval.
- **ICH E6(R3) §5.5.7**: satisfied — the trial record is retained unchanged for 15 years.
- **21 CFR Part 11**: satisfied — no records are deleted; the erasure audit log is append-only.
- **ALCOA+ (Enduring)**: satisfied — original data is retained; only the re-identification key is destroyed.

### Assumptions

- Azure Key Vault key destruction is cryptographically irreversible within reasonable time bounds (HSM-backed keys require a 7-day scheduled deletion in Azure). The 7-day purge protection window must be communicated to patients: "your erasure request will be processed within 10 business days."
- The institution's legal and privacy team has reviewed this approach and confirmed it is consistent with applicable member state law.
- The Ethics Committee / IRB approval covers pseudonymised retention after an erasure request.

### Review trigger

If the platform expands to process whole-genome sequencing data (as opposed to targeted exon variants), the re-identification risk from the genomic data itself (not the key) becomes material enough to require a full DPIA review and potentially a more aggressive anonymisation strategy. Revisit this ADR before any WGS data is ingested.
