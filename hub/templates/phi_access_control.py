"""
PHI/PII access control — Unity Catalog ABAC pattern for patient-level tables.

Applies to any table introduced in Phase 4+ that contains patient identifiers
or clinical measurements. Run this script after the table is created and before
the first data load. It is idempotent — safe to re-run.

WHY ABAC OVER RBAC
==================
Simple role-based grants (GRANT SELECT ON TABLE TO role) give all members of
a role identical access — a clinical coordinator can see every patient, not just
their assigned ones. For this project ABAC (Attribute-Based Access Control) is
the appropriate model because:

  1. Row-level isolation: a coordinator should see only their assigned patients.
     This cannot be expressed with GRANT — it requires a row filter that checks
     the current user against an assignment table.

  2. Column-level masking by sensitivity tier: identifiers (name, DOB) need full
     masking for researchers; direct care teams need them unmasked. The same table
     serves both audiences without duplication.

  3. Policy maintenance: a new column tagged 'phi' automatically inherits the mask
     function. No manual GRANT update is needed when the schema evolves.

DATABRICKS UNITY CATALOG ABAC (2024-2025 best practice)
========================================================
Unity Catalog implements ABAC via two declarative mechanisms:

  - Column masks: SQL function applied transparently at query time.
    The function receives the column value and returns a masked or unmasked value
    based on the current user's group memberships (IS_MEMBER()) or identity.

  - Row filters: SQL function that returns a boolean. Only rows for which the
    function returns TRUE are visible to the current user.

Both are applied by the Unity Catalog engine — they cannot be bypassed by direct
Delta table reads. They survive table renames and schema evolution.

GROUPS TO CREATE BEFORE RUNNING THIS SCRIPT
============================================
Create these groups in the Databricks account console (or via the Groups API)
and assign users before applying the access control:

  phi_full_access      — direct care clinical team; sees all columns unmasked
  phi_research_access  — approved researchers; identifiers masked, cohort data visible
  phi_coordinator_<id> — per-study coordinators; row-filtered to their patients
  platform_admin       — pipeline service principals; read/write, no masking

Usage:
  python hub/templates/phi_access_control.py \\
      --catalog clinical --schema gold --table patient_trial_eligibility

Requirements: databricks-connect configured with an admin service principal.
"""

import argparse
from databricks.connect import DatabricksSession

# ---------------------------------------------------------------------------
# PHI column tiers
#
# Tier 1 — Direct identifiers: must be fully masked for all non-clinical roles.
#           Examples: name, date of birth, national ID, address.
#
# Tier 2 — Quasi-identifiers: individually not identifying, but combinable.
#           Examples: year of birth, postcode prefix, diagnosis date.
#           Masked for researcher role; visible to clinical roles.
#
# Tier 3 — Clinical data: not identifying without Tier 1/2 linkage.
#           Examples: mutation type, trial eligibility flags, reading frame effect.
#           Visible to all authorised roles.
# ---------------------------------------------------------------------------
PHI_TIERS = {
    "tier_1_direct_identifiers": [
        "patient_name", "date_of_birth", "national_id",
        "address", "postcode", "phone", "email",
    ],
    "tier_2_quasi_identifiers": [
        "birth_year", "diagnosis_date", "first_symptoms_date",
        "postcode_prefix", "country",
    ],
}


# ---------------------------------------------------------------------------
# SQL DDL for column mask functions
# ---------------------------------------------------------------------------

MASK_TIER1_FUNCTION = """
CREATE OR REPLACE FUNCTION {catalog}.{schema}.mask_phi_tier1(col_value STRING)
RETURNS STRING
LANGUAGE SQL
COMMENT 'Masks direct patient identifiers. Unmasked only for phi_full_access group members.'
RETURN CASE
    WHEN IS_MEMBER('phi_full_access')  THEN col_value
    WHEN IS_MEMBER('platform_admin')   THEN col_value  -- service principals need full access for pipeline writes
    ELSE '***REDACTED***'
END;
"""

MASK_TIER2_FUNCTION = """
CREATE OR REPLACE FUNCTION {catalog}.{schema}.mask_phi_tier2(col_value STRING)
RETURNS STRING
LANGUAGE SQL
COMMENT 'Masks quasi-identifiers. Visible to clinical team and coordinators; masked for researchers.'
RETURN CASE
    WHEN IS_MEMBER('phi_full_access')      THEN col_value
    WHEN IS_MEMBER('phi_coordinator_%')    THEN col_value  -- coordinators see quasi-identifiers
    WHEN IS_MEMBER('platform_admin')       THEN col_value
    ELSE '***MASKED***'
END;
"""

ROW_FILTER_FUNCTION = """
CREATE OR REPLACE FUNCTION {catalog}.{schema}.row_filter_patient_access(patient_id STRING)
RETURNS BOOLEAN
LANGUAGE SQL
COMMENT 'Row-level filter: coordinators see only their assigned patients; clinical team and researchers see all (subject to column masking).'
RETURN (
    IS_MEMBER('phi_full_access')
    OR IS_MEMBER('phi_research_access')
    OR IS_MEMBER('platform_admin')
    OR EXISTS (
        -- Check coordinator assignment table
        -- This table must be maintained by the registry team
        SELECT 1 FROM {catalog}.{schema}.coordinator_patient_assignments
        WHERE assigned_coordinator = CURRENT_USER()
        AND   assigned_patient_id  = patient_id
    )
);
"""


def apply_phi_controls(spark, catalog: str, schema: str, table: str) -> None:
    full_table = f"{catalog}.{schema}.{table}"

    print(f"Applying PHI access controls to {full_table}\n")

    # ------------------------------------------------------------------
    # Step 1: Create mask and filter functions in the same schema
    # ------------------------------------------------------------------
    print("Creating mask functions...")
    spark.sql(MASK_TIER1_FUNCTION.format(catalog=catalog, schema=schema))
    spark.sql(MASK_TIER2_FUNCTION.format(catalog=catalog, schema=schema))
    spark.sql(ROW_FILTER_FUNCTION.format(catalog=catalog, schema=schema))
    print("  mask_phi_tier1, mask_phi_tier2, row_filter_patient_access created.\n")

    # ------------------------------------------------------------------
    # Step 2: Discover PHI columns via Unity Catalog tags
    # Columns tagged 'phi_tier' = '1' or '2' get masks applied.
    # Tag columns using: ALTER TABLE ... ALTER COLUMN ... SET TAGS ('phi_tier' = '1')
    # ------------------------------------------------------------------
    print("Discovering PHI-tagged columns...")
    tagged = spark.sql(f"""
        SELECT column_name, tag_value
        FROM system.information_schema.column_tags
        WHERE catalog_name  = '{catalog}'
        AND   schema_name   = '{schema}'
        AND   table_name    = '{table}'
        AND   tag_name      = 'phi_tier'
        AND   tag_value IN ('1', '2')
    """).collect()

    if not tagged:
        print("  No columns tagged with phi_tier found. Tag columns before applying masks:")
        print(f"  ALTER TABLE {full_table} ALTER COLUMN <col> SET TAGS ('phi_tier' = '1');")

    # ------------------------------------------------------------------
    # Step 3: Apply column masks to tagged columns
    # ------------------------------------------------------------------
    for row in tagged:
        col   = row["column_name"]
        tier  = row["tag_value"]
        fn    = f"{catalog}.{schema}.mask_phi_tier{tier}"
        spark.sql(f"ALTER TABLE {full_table} ALTER COLUMN {col} SET MASK {fn}")
        print(f"  Masked tier-{tier} column: {col}")

    # ------------------------------------------------------------------
    # Step 4: Apply row filter
    # Assumes the table has a 'patient_id' column. Adjust if different.
    # ------------------------------------------------------------------
    print("\nApplying row filter...")
    try:
        spark.sql(f"""
            ALTER TABLE {full_table}
            SET ROW FILTER {catalog}.{schema}.row_filter_patient_access ON (patient_id)
        """)
        print(f"  Row filter applied on patient_id column.")
    except Exception as e:
        print(f"  WARNING: could not apply row filter: {e}")
        print("  Verify that the table has a 'patient_id' column and the coordinator_patient_assignments table exists.")

    # ------------------------------------------------------------------
    # Step 5: Apply table-level tags for Unity Catalog data classification
    # ------------------------------------------------------------------
    print("\nApplying Unity Catalog classification tags...")
    spark.sql(f"""
        ALTER TABLE {full_table} SET TAGS (
            'data_classification' = 'phi',
            'gdpr_applicable'     = 'true',
            'hipaa_applicable'    = 'true',
            'retention_years'     = '7',
            'access_policy'       = 'abac_phi_v1'
        )
    """)
    print("  Table tagged: data_classification=phi, gdpr_applicable=true, hipaa_applicable=true\n")

    print(f"PHI access controls applied to {full_table}.")
    print("\nNext steps:")
    print("  1. Verify groups exist: phi_full_access, phi_research_access, platform_admin")
    print("  2. Create coordinator_patient_assignments table if not exists")
    print(f"  3. Tag PHI columns: ALTER TABLE {full_table} ALTER COLUMN <col> SET TAGS ('phi_tier' = '1')")
    print("  4. Test with a coordinator user account to verify row filter works")
    print("  5. Run audit_trail_config.py to set 21 CFR Part 11 Delta properties")


def verify_phi_controls(spark, catalog: str, schema: str, table: str) -> None:
    """Print a summary of active masks and row filters on a table."""
    full_table = f"{catalog}.{schema}.{table}"
    print(f"\nVerifying PHI controls on {full_table}:\n")

    masks = spark.sql(f"""
        SELECT column_name, mask_function_name
        FROM system.information_schema.column_masks
        WHERE catalog_name = '{catalog}'
        AND   schema_name  = '{schema}'
        AND   table_name   = '{table}'
    """).collect()

    filters = spark.sql(f"""
        SELECT filter_function_name, filter_columns
        FROM system.information_schema.row_filters
        WHERE catalog_name = '{catalog}'
        AND   schema_name  = '{schema}'
        AND   table_name   = '{table}'
    """).collect()

    print(f"  Column masks ({len(masks)}):")
    for m in masks:
        print(f"    {m['column_name']:<30} → {m['mask_function_name']}")

    print(f"\n  Row filters ({len(filters)}):")
    for f in filters:
        print(f"    {f['filter_function_name']} on columns: {f['filter_columns']}")

    if not masks and not filters:
        print("  WARNING: No PHI controls found. Apply phi_access_control.py before loading patient data.")


def main():
    parser = argparse.ArgumentParser(description="Apply Unity Catalog PHI access controls.")
    parser.add_argument("--catalog",  required=True)
    parser.add_argument("--schema",   required=True)
    parser.add_argument("--table",    required=True)
    parser.add_argument("--verify",   action="store_true", help="Verify existing controls instead of applying")
    args = parser.parse_args()

    spark = DatabricksSession.builder.profile("steff_horemans").serverless(True).getOrCreate()

    if args.verify:
        verify_phi_controls(spark, args.catalog, args.schema, args.table)
    else:
        apply_phi_controls(spark, args.catalog, args.schema, args.table)


if __name__ == "__main__":
    main()
