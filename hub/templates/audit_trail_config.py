"""
21 CFR Part 11 audit trail configuration for Delta tables.

21 CFR Part 11 requires that electronic records used in clinical contexts
are trustworthy, reliable, and equivalent to paper records. For Delta tables
this means:

  1. Immutable history — DESCRIBE HISTORY must be available for the full
     retention period (minimum 7 years for clinical data).
  2. Attributable — every write is attributed to a service principal or user
     (Unity Catalog captures this automatically in the Delta log).
  3. Contemporaneous — ingestion_timestamp on every row reflects when the
     record was written, not when the source data was created.
  4. Accurate — rows cannot be silently overwritten; schema changes are logged.
  5. Complete — deleted file retention must match log retention so that
     time-travel queries can reconstruct any historical state.

Run this script during pipeline initialisation to apply the correct table
properties. It is idempotent — safe to run on existing tables.

Usage:
  python hub/templates/audit_trail_config.py \\
      --catalog clinical --schema gold --table trial_eligibility_catalogue

Or call configure_table() from within a pipeline notebook.
"""

import argparse
from databricks.connect import DatabricksSession

# ---------------------------------------------------------------------------
# Required table properties for 21 CFR Part 11 compliance
# These values are the minimum. Do not reduce retention below 2555 days (7 years).
# ---------------------------------------------------------------------------
REQUIRED_PROPERTIES = {
    # Delta log retention — how long DESCRIBE HISTORY entries are kept
    "delta.logRetentionDuration":         "interval 2555 days",   # 7 years
    # Data file retention — must be >= logRetentionDuration for time travel to work
    "delta.deletedFileRetentionDuration": "interval 2555 days",
    # Prevent schema changes without an explicit ALTER TABLE — protects record integrity
    "delta.columnMapping.mode":           "name",                 # enables column rename without rewrite
    # Enable change data feed for downstream audit consumers
    "delta.enableChangeDataFeed":         "true",
}


def configure_table(spark, catalog: str, schema: str, table: str) -> None:
    """Apply 21 CFR Part 11 properties to a Delta table. Idempotent."""
    full_name = f"{catalog}.{schema}.{table}"
    props_sql  = ", ".join(f"'{k}' = '{v}'" for k, v in REQUIRED_PROPERTIES.items())

    spark.sql(f"ALTER TABLE {full_name} SET TBLPROPERTIES ({props_sql})")
    print(f"Configured {full_name} for 21 CFR Part 11 compliance.")

    # Verify
    result = spark.sql(f"SHOW TBLPROPERTIES {full_name}").collect()
    configured = {row["key"]: row["value"] for row in result}
    for key, expected in REQUIRED_PROPERTIES.items():
        actual = configured.get(key)
        status = "OK" if actual == expected else f"MISMATCH (got: {actual})"
        print(f"  {key:<50s} {status}")


# ---------------------------------------------------------------------------
# Audit query patterns
#
# Copy these into a notebook or monitoring job. They are the primary interface
# for auditors and compliance reviewers.
# ---------------------------------------------------------------------------
AUDIT_QUERIES = {
    "full_history": """
        -- Full write history for a table (21 CFR Part 11 audit trail)
        DESCRIBE HISTORY {catalog}.{schema}.{table}
    """,

    "history_in_range": """
        -- All operations performed between two timestamps
        DESCRIBE HISTORY {catalog}.{schema}.{table}
        TIMESTAMP AS OF '{as_of_timestamp}'
    """,

    "time_travel_snapshot": """
        -- Reconstruct the table as it existed at a specific point in time
        SELECT * FROM {catalog}.{schema}.{table}
        TIMESTAMP AS OF '{as_of_timestamp}'
    """,

    "change_data_feed": """
        -- All inserts, updates, and deletes since a given version
        -- Requires delta.enableChangeDataFeed = true on the table
        SELECT *
        FROM table_changes('{catalog}.{schema}.{table}', {start_version})
        WHERE _change_type IN ('insert', 'update_postimage', 'delete')
        ORDER BY _commit_timestamp
    """,

    "who_wrote_version": """
        -- Which user or service principal wrote a specific version
        SELECT operationParameters, userMetadata, userName, timestamp
        FROM (DESCRIBE HISTORY {catalog}.{schema}.{table})
        WHERE version = {version}
    """,

    "schema_changes": """
        -- All schema change events (ADD COLUMN, ALTER COLUMN, etc.)
        SELECT version, timestamp, operation, operationParameters, userName
        FROM (DESCRIBE HISTORY {catalog}.{schema}.{table})
        WHERE operation IN ('REPLACE TABLE', 'ADD COLUMNS', 'CHANGE COLUMN', 'DROP COLUMNS')
        ORDER BY version
    """,
}


def print_audit_queries(catalog: str, schema: str, table: str) -> None:
    """Print formatted audit queries for a specific table — hand these to auditors."""
    print(f"\nAudit queries for {catalog}.{schema}.{table}:\n")
    for name, query in AUDIT_QUERIES.items():
        formatted = query.format(
            catalog=catalog, schema=schema, table=table,
            as_of_timestamp="<YYYY-MM-DD HH:MM:SS>",
            start_version="<version_number>",
            version="<version_number>",
        )
        print(f"-- {name}")
        print(formatted.strip())
        print()


# ---------------------------------------------------------------------------
# Monitoring: detect tables missing required properties
# Run this as a scheduled job or pre-deployment check.
# ---------------------------------------------------------------------------
def audit_compliance_check(spark, catalog: str, schema: str) -> list[dict]:
    """
    Check all tables in a schema for 21 CFR Part 11 property compliance.
    Returns a list of non-compliant tables with missing or incorrect properties.
    """
    tables = spark.sql(f"SHOW TABLES IN {catalog}.{schema}").collect()
    non_compliant = []

    for row in tables:
        table = row["tableName"]
        full_name = f"{catalog}.{schema}.{table}"
        try:
            props = {
                r["key"]: r["value"]
                for r in spark.sql(f"SHOW TBLPROPERTIES {full_name}").collect()
            }
        except Exception:
            continue  # skip views and non-Delta tables

        missing = {
            k: v for k, v in REQUIRED_PROPERTIES.items()
            if props.get(k) != v
        }
        if missing:
            non_compliant.append({"table": full_name, "missing_or_wrong": missing})

    if non_compliant:
        print(f"NON-COMPLIANT tables in {catalog}.{schema}:")
        for entry in non_compliant:
            print(f"  {entry['table']}")
            for k, v in entry["missing_or_wrong"].items():
                print(f"    {k}: expected '{v}', got '{props.get(k, 'NOT SET')}'")
    else:
        print(f"All tables in {catalog}.{schema} are 21 CFR Part 11 compliant.")

    return non_compliant


def main():
    parser = argparse.ArgumentParser(description="Apply 21 CFR Part 11 table properties.")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema",  required=True)
    parser.add_argument("--table",   required=True)
    parser.add_argument("--check-schema", action="store_true",
                        help="Check all tables in the schema instead of configuring one table")
    args = parser.parse_args()

    spark = DatabricksSession.builder.profile("steff_horemans").serverless(True).getOrCreate()

    if args.check_schema:
        audit_compliance_check(spark, args.catalog, args.schema)
    else:
        configure_table(spark, args.catalog, args.schema, args.table)
        print_audit_queries(args.catalog, args.schema, args.table)


if __name__ == "__main__":
    main()
