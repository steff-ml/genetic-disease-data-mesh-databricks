# Template: HL7 FHIR R4 mapping for EHR integration
#
# WHEN TO USE THIS TEMPLATE
# ==========================
# Use when Phase 5 EHR integration goes live — specifically when a clinician
# needs to look up a patient's trial eligibility or therapy options from inside
# an EHR system (Epic, Cerner, etc.).
#
# OMOP CDM (omop_cdm_mapping.py) is for analytical cohort queries.
# CDISC SDTM (cdisc_sdtm_mapping.py) is for regulatory submission.
# FHIR R4 is for individual patient API lookups from EHR systems and apps.
#
# These three are complementary, not alternatives — the same Gold data
# may be consumed via all three paths by different consumers.
#
# FHIR RESOURCES IMPLEMENTED HERE
# ================================
# Three R4 resources cover this project's Phase 5 EHR integration:
#
#   Patient          — subject demographics, de-identified
#   Observation      — variant genotype finding (using LOINC code 81252-9
#                       "Discrete genetic variant")
#   Condition        — diagnosis (DMD / BMD) using OMOP concept IDs mapped
#                       to SNOMED CT codes as required by FHIR
#
# DEPLOYMENT
# ==========
# The FHIR API layer is NOT Databricks. Gold data is published to a FHIR
# server that EHRs call. Two deployment options:
#
#   Option A — Azure Health Data Services (FHIR Service):
#     Managed FHIR R4/R5 server. Gold → FHIR is a one-way sync job (this
#     template). The FHIR server handles EHR queries.
#
#   Option B — HAPI FHIR server (open source):
#     Self-hosted. More control, more operational burden.
#
# For most organisations starting out, Option A is recommended. It handles
# auth (Azure AD / SMART on FHIR), FHIR version compliance, and scalability.
#
# SMART ON FHIR
# =============
# EHR-embedded apps use SMART on FHIR for authorization. The FHIR server
# must support the SMART App Launch Framework (HL7 SMART App Launch v2).
# Azure Health Data Services supports this natively.
#
# Dependencies: pip install fhir.resources  (Pydantic FHIR R4 models)
#
# Related: hub/templates/omop_cdm_mapping.py (analytical use; different consumers)
#          hub/templates/phi_access_control.py (patient data requires ABAC)
#          hub/templates/ich_e6_gcp_checklist.md (GCP requirements for patient data)
#          docs/adr/adr_24.md (GDPR/GCP pseudonymisation policy)

from typing import Optional
from datetime import date, datetime


# ---------------------------------------------------------------------------
# LOINC codes used for DMD variant observations
# Source: LOINC database — do not hard-code; look up current codes at loinc.org
# ---------------------------------------------------------------------------
LOINC_DISCRETE_GENETIC_VARIANT = "81252-9"    # Discrete genetic variant
LOINC_VARIANT_HGVS             = "81290-9"    # HGVS cDNA notation
LOINC_VARIANT_INTERPRETATION   = "53037-8"    # Genetic variant clinical significance
LOINC_VARIANT_VRS_ID           = "81259-4"    # Variant identifiers

# SNOMED CT codes for DMD and BMD diagnoses (verify against current release)
SNOMED_DMD = "73297009"   # Duchenne muscular dystrophy (disorder)
SNOMED_BMD = "75068009"   # Becker muscular dystrophy (disorder)

# FHIR system URIs
FHIR_SNOMED_SYSTEM  = "http://snomed.info/sct"
FHIR_LOINC_SYSTEM   = "http://loinc.org"
FHIR_HGVS_SYSTEM    = "http://varnomen.hgvs.org"
FHIR_VRS_SYSTEM     = "https://ga4gh.github.io/vrs"


# ---------------------------------------------------------------------------
# Patient resource
#
# Patient identifiers are pseudonymised per ADR-24 before exposure via FHIR.
# The FHIR Patient resource holds the pseudonymous ID; the re-identification
# key is held in Azure Key Vault and is never exposed in this layer.
# ---------------------------------------------------------------------------
def build_fhir_patient(
    pseudonymous_id: str,
    birth_year:      Optional[int],
    sex_code:        str,   # "male" | "female" | "unknown" | "other" (FHIR R4 AdministrativeGender)
    country:         Optional[str],
) -> dict:
    """
    Build a FHIR R4 Patient resource from pseudonymised patient attributes.

    birth_year is used instead of full date of birth to prevent re-identification.
    Full birthdate is only included if the EHR integration explicitly requires it
    and the coordinator has phi_full_access.
    """
    resource = {
        "resourceType": "Patient",
        "id": pseudonymous_id,
        "meta": {
            "profile": [
                "http://hl7.org/fhir/StructureDefinition/Patient"
            ]
        },
        "identifier": [
            {
                "system": "urn:oid:2.16.840.1.113883.3.4424.pseudonymous",
                "value": pseudonymous_id,
            }
        ],
        # Provide only birth year — partial date is valid FHIR R4
        "birthDate": str(birth_year) if birth_year else None,
        "gender": sex_code,
    }

    if country:
        resource["address"] = [{"country": country}]

    return resource


# ---------------------------------------------------------------------------
# Observation resource — Genetic Variant Finding
#
# One Observation per variant per patient. Uses LOINC 81252-9 as the code,
# which is the standard LOINC code for discrete genetic variant observations.
# ---------------------------------------------------------------------------
def build_fhir_variant_observation(
    observation_id:  str,
    patient_id:      str,
    canonical_hgvs:  str,
    vrs_id:          Optional[str],
    clinical_significance: Optional[str],  # Pathogenic | VUS | Benign | Conflicting
    interpretation_code:   Optional[str],  # ACMG tier as LOINC answer code (LA6668-3 etc.)
    effective_date:  Optional[date],
) -> dict:
    """
    Build a FHIR R4 Observation resource for a single variant finding.

    The Observation uses the Genomics Reporting IG (Implementation Guide) component
    structure for reporting HGVS and VRS identifiers as separate components under
    the parent Observation.

    clinical_significance should be one of the ACMG five-tier values. The
    interpretation.coding field carries the LOINC answer list LA codes:
        LA6668-3  — Pathogenic
        LA26332-9 — Likely pathogenic
        LA26333-7 — Uncertain significance
        LA26334-5 — Likely benign
        LA6675-8  — Benign
    """
    components = [
        {
            "code": {
                "coding": [{"system": FHIR_LOINC_SYSTEM, "code": LOINC_VARIANT_HGVS,
                             "display": "HGVS cDNA"}]
            },
            "valueString": canonical_hgvs,
        }
    ]

    if vrs_id:
        components.append({
            "code": {
                "coding": [{"system": FHIR_LOINC_SYSTEM, "code": LOINC_VARIANT_VRS_ID,
                             "display": "Variant identifiers"}]
            },
            "valueString": vrs_id,
        })

    observation = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code":    "laboratory",
                        "display": "Laboratory",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system":  FHIR_LOINC_SYSTEM,
                    "code":    LOINC_DISCRETE_GENETIC_VARIANT,
                    "display": "Discrete genetic variant",
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": effective_date.isoformat() if effective_date else None,
        "component": components,
    }

    if clinical_significance and interpretation_code:
        observation["interpretation"] = [
            {
                "coding": [
                    {
                        "system":  FHIR_LOINC_SYSTEM,
                        "code":    interpretation_code,
                        "display": clinical_significance,
                    }
                ]
            }
        ]

    return observation


# ---------------------------------------------------------------------------
# Condition resource — DMD/BMD Diagnosis
# ---------------------------------------------------------------------------
def build_fhir_condition(
    condition_id:   str,
    patient_id:     str,
    diagnosis:      str,          # "DMD" | "BMD"
    onset_year:     Optional[int],
    clinical_status: str = "active",  # FHIR R4: active | relapse | remission | resolved
) -> dict:
    """
    Build a FHIR R4 Condition resource for a DMD or BMD diagnosis.

    SNOMED codes are used as required by the FHIR US Core and international
    patient summary profiles.
    """
    snomed_code = SNOMED_DMD if diagnosis.upper() == "DMD" else SNOMED_BMD
    display     = "Duchenne muscular dystrophy" if diagnosis.upper() == "DMD" else "Becker muscular dystrophy"

    condition = {
        "resourceType": "Condition",
        "id": condition_id,
        "clinicalStatus": {
            "coding": [
                {
                    "system":  "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code":    clinical_status,
                    "display": clinical_status.capitalize(),
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system":  FHIR_SNOMED_SYSTEM,
                    "code":    snomed_code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
    }

    if onset_year:
        condition["onsetDateTime"] = str(onset_year)

    return condition


# ---------------------------------------------------------------------------
# FHIR Bundle — package Patient + Observations + Conditions in one response
# ---------------------------------------------------------------------------
def build_patient_bundle(
    patient_resource: dict,
    observations:     list[dict],
    conditions:       list[dict],
    bundle_id:        str,
) -> dict:
    """
    Bundle a Patient with their variant Observations and Conditions into a
    FHIR R4 Bundle of type 'searchset'. This is the response format returned
    by the FHIR $everything operation or a combined search.

    When deploying to Azure Health Data Services, import this bundle via the
    FHIR service's batch import API. The FHIR server handles incremental updates
    on subsequent syncs using the resource id as the idempotency key.
    """
    entries = []

    def _entry(resource: dict) -> dict:
        rtype = resource["resourceType"]
        rid   = resource["id"]
        return {
            "fullUrl": f"urn:uuid:{rid}",
            "resource": resource,
            "request": {"method": "PUT", "url": f"{rtype}/{rid}"},
        }

    entries.append(_entry(patient_resource))
    for obs in observations:
        entries.append(_entry(obs))
    for cond in conditions:
        entries.append(_entry(cond))

    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "transaction",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entry": entries,
    }


# ---------------------------------------------------------------------------
# Spark batch sync job — Gold → FHIR server
#
# Run this as a scheduled Databricks job after Gold pipeline completes.
# It reads new/updated Gold patient rows and POSTs FHIR bundles to the server.
# ---------------------------------------------------------------------------
def sync_gold_to_fhir(
    spark,
    gold_table:   str,
    fhir_base_url: str,
    fhir_token:   str,
    batch_size:   int = 100,
) -> None:
    """
    Batch sync Gold patient mutation profiles to the FHIR server.

    Authentication: use Azure Managed Identity in production, not a hardcoded token.
    Pass fhir_token from Databricks Secret Scope:
        fhir_token = dbutils.secrets.get(scope="fhir", key="azure_fhir_bearer")

    Parameters
    ----------
    spark         : Spark session
    gold_table    : fully qualified Gold table (catalog.schema.table)
    fhir_base_url : FHIR server base URL e.g. "https://<workspace>.fhir.azurehealthcareapis.com"
    fhir_token    : Bearer token for the FHIR API
    batch_size    : rows per Spark partition (controls parallelism)
    """
    import json
    import requests

    headers = {
        "Authorization": f"Bearer {fhir_token}",
        "Content-Type": "application/fhir+json",
    }

    df = spark.table(gold_table)
    rows = df.collect()

    synced, failed = 0, 0
    for row in rows:
        try:
            patient   = build_fhir_patient(
                pseudonymous_id=row["pseudonymous_id"],
                birth_year=row.get("birth_year"),
                sex_code=row.get("sex_code", "unknown"),
                country=row.get("country"),
            )
            observation = build_fhir_variant_observation(
                observation_id=f"{row['pseudonymous_id']}-variant-1",
                patient_id=row["pseudonymous_id"],
                canonical_hgvs=row.get("canonical_hgvs", ""),
                vrs_id=row.get("vrs_allele_id"),
                clinical_significance=row.get("clinical_significance"),
                interpretation_code=row.get("loinc_interpretation_code"),
                effective_date=None,
            )
            condition = build_fhir_condition(
                condition_id=f"{row['pseudonymous_id']}-condition-1",
                patient_id=row["pseudonymous_id"],
                diagnosis=row.get("phenotype", "DMD"),
                onset_year=row.get("onset_year"),
            )
            bundle = build_patient_bundle(
                patient_resource=patient,
                observations=[observation],
                conditions=[condition],
                bundle_id=f"bundle-{row['pseudonymous_id']}",
            )

            resp = requests.post(fhir_base_url, json=bundle, headers=headers, timeout=30)
            resp.raise_for_status()
            synced += 1
        except Exception as e:
            print(f"FHIR sync failed for {row.get('pseudonymous_id')}: {e}")
            failed += 1

    print(f"FHIR sync complete: {synced} succeeded, {failed} failed.")
    if failed > 0:
        raise RuntimeError(f"FHIR sync had {failed} failures — check logs before marking job successful.")
