"""
Contract compliance check — run before promoting a Gold table to "active" status.

Reads a Bitol ODCS YAML contract from docs/contracts/ and compares it against
the live Unity Catalog table schema. Reports three categories of drift:

  SCHEMA DRIFT  — columns present in the contract but missing from the table,
                  or in the table but undeclared in the contract
  TYPE DRIFT    — columns present in both but with mismatched data types
  QUALITY GAPS  — quality rules declared in the contract with no corresponding
                  @dlt.expect rule found in the pipeline source file

Usage:
  python hub/templates/contract_check.py \\
      --contract docs/contracts/trial_eligibility_catalogue.yaml \\
      --pipeline trial_eligibility_catalogue/src/pipeline.py

Exit code 0 = clean. Exit code 1 = drift found (suitable for CI gate).

Requirements: databricks-connect (configured with profile "steff_horemans"),
              pyyaml
"""

import argparse
import re
import sys
from pathlib import Path

import yaml
from databricks.connect import DatabricksSession


# ---------------------------------------------------------------------------
# Type normalisation
# Unity Catalog returns types like "STRING", "BIGINT", "BOOLEAN".
# The ODCS contract uses "string", "long", "boolean".
# This map normalises both sides for comparison.
# ---------------------------------------------------------------------------
UC_TO_ODCS = {
    "STRING":    "string",
    "BIGINT":    "long",
    "INT":       "integer",
    "DOUBLE":    "double",
    "FLOAT":     "float",
    "BOOLEAN":   "boolean",
    "DATE":      "date",
    "TIMESTAMP": "timestamp",
    "ARRAY":     "array",
    "STRUCT":    "struct",
    "BINARY":    "binary",
}


def load_contract(contract_path: Path) -> dict:
    with open(contract_path) as f:
        return yaml.safe_load(f)


def get_live_schema(spark, catalog: str, schema: str, table: str) -> dict[str, str]:
    """Return {column_name: uc_type} from Unity Catalog."""
    rows = spark.sql(f"DESCRIBE TABLE {catalog}.{schema}.{table}").collect()
    return {
        row["col_name"]: UC_TO_ODCS.get(row["data_type"].upper(), row["data_type"].lower())
        for row in rows
        if not row["col_name"].startswith("#")  # skip partition/metadata headers
    }


def get_contract_schema(contract: dict) -> dict[str, dict]:
    """Return {column_name: {type, required}} from contract models section."""
    models = contract.get("models", [])
    if not models:
        return {}
    columns = models[0].get("columns", [])
    return {
        col["name"]: {
            "type":     col.get("type", "string").lower(),
            "required": col.get("required", False),
        }
        for col in columns
    }


def get_contract_quality_rules(contract: dict) -> list[str]:
    """Return list of rule names declared in the contract quality section."""
    return [rule["rule"] for rule in contract.get("quality", [])]


def get_pipeline_expect_rules(pipeline_path: Path) -> list[str]:
    """
    Scan a pipeline Python file for @dlt.expect* decorator rule names.
    Matches: @dlt.expect_or_quarantine("rule_name", ...) and @dlt.expect_or_warn(...)
    """
    if not pipeline_path.exists():
        return []
    source = pipeline_path.read_text()
    return re.findall(r'@dlt\.expect[^(]*\(\s*["\']([^"\']+)["\']', source)


def check(contract_path: Path, pipeline_path: Path | None) -> int:
    contract = load_contract(contract_path)

    # Locate the server definition
    servers = contract.get("servers", {})
    prod = servers.get("production", {})
    catalog = prod.get("catalog")
    schema  = prod.get("schema")
    table   = prod.get("table")

    if not all([catalog, schema, table]):
        print("ERROR: contract servers.production is missing catalog, schema, or table.")
        return 1

    print(f"Checking contract: {contract_path.name}")
    print(f"Target table:      {catalog}.{schema}.{table}\n")

    spark = DatabricksSession.builder.profile("steff_horemans").serverless(True).getOrCreate()

    try:
        live   = get_live_schema(spark, catalog, schema, table)
    except Exception as e:
        print(f"ERROR: could not read table schema from Unity Catalog: {e}")
        return 1

    declared = get_contract_schema(contract)
    errors   = 0
    warnings = 0

    # ------------------------------------------------------------------
    # Schema drift
    # ------------------------------------------------------------------
    print("=== Schema drift ===\n")

    missing_from_table = set(declared) - set(live)
    undeclared_in_contract = set(live) - set(declared)

    if missing_from_table:
        for col in sorted(missing_from_table):
            print(f"  ERROR   column '{col}' declared in contract but NOT in table")
            errors += 1
    if undeclared_in_contract:
        for col in sorted(undeclared_in_contract):
            print(f"  WARNING column '{col}' exists in table but NOT declared in contract")
            warnings += 1

    # ------------------------------------------------------------------
    # Type drift
    # ------------------------------------------------------------------
    print("\n=== Type drift ===\n")
    for col in sorted(set(declared) & set(live)):
        contract_type = declared[col]["type"]
        live_type     = live[col]
        if contract_type != live_type:
            print(f"  ERROR   '{col}': contract={contract_type}, table={live_type}")
            errors += 1

    # ------------------------------------------------------------------
    # Required-nullable drift
    # ------------------------------------------------------------------
    print("\n=== Nullability drift ===\n")
    # Unity Catalog does not expose nullable directly in DESCRIBE TABLE;
    # use DESCRIBE TABLE EXTENDED for full column detail.
    # This is left as a stub — implement when Unity Catalog exposes nullable
    # reliably via the REST or SQL API.
    print("  (not yet implemented — check manually for nullable mismatches)")

    # ------------------------------------------------------------------
    # Quality rule coverage
    # ------------------------------------------------------------------
    print("\n=== Quality rule coverage ===\n")
    contract_rules = get_contract_quality_rules(contract)

    if pipeline_path:
        pipeline_rules = get_pipeline_expect_rules(pipeline_path)
        for rule in contract_rules:
            if rule not in pipeline_rules:
                print(f"  WARNING rule '{rule}' in contract has no @dlt.expect in {pipeline_path.name}")
                warnings += 1
    else:
        print("  (no pipeline file provided — skipping quality rule coverage check)")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'='*50}")
    print(f"  Errors:   {errors}")
    print(f"  Warnings: {warnings}")
    if errors == 0 and warnings == 0:
        print("  PASS — contract and table are aligned.")
    elif errors == 0:
        print("  PASS with warnings — review warnings before promoting to active.")
    else:
        print("  FAIL — resolve errors before promoting to active status.")
    print(f"{'='*50}\n")

    return 1 if errors > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="Check ODCS contract against live Unity Catalog schema.")
    parser.add_argument("--contract",  required=True,  help="Path to ODCS YAML contract file")
    parser.add_argument("--pipeline",  required=False, help="Path to DLT pipeline Python file (for quality rule coverage check)")
    args = parser.parse_args()

    exit_code = check(
        contract_path=Path(args.contract),
        pipeline_path=Path(args.pipeline) if args.pipeline else None,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
