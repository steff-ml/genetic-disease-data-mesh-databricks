# Databricks notebook source
# Template: Cross-domain data product interface
#
# Use this template when a pipeline in one domain reads a data product
# published by another domain. The primary instance in this project is
# Phase 5: the Clinical domain consuming discovery.gold.patient_mutation_profile.
#
# The governance problem this template solves:
#   Without enforcement at the boundary, a schema change in the Discovery domain
#   would silently corrupt Clinical domain pipelines. The Clinical team would
#   discover the breakage only when Gold outputs are wrong — after patient-trial
#   matching has produced incorrect verdicts.
#
# This template enforces the contract at read time:
#   1. The consuming pipeline declares the schema it expects (pinned to a
#      contract version). If the published schema diverges, the pipeline fails
#      loudly at the read step rather than silently downstream.
#   2. The producing domain's data_product_version is checked against the
#      version the consumer was certified against. A major version bump blocks
#      the consuming pipeline until the contract is renegotiated.
#   3. The cross-domain read is wrapped in a function so it can be mocked
#      in unit tests without a live Unity Catalog connection.
#
# Related: docs/adr/ (ADR for cross-domain data product contracts)
#          hub/templates/dlt_gold_table.py (producing side)
#          docs/contracts/<table>.yaml (the contract being enforced here)

import dlt
from pyspark.sql import functions as F, DataFrame
from pyspark.sql.types import StructField, StructType, StringType, BooleanType

# ---------------------------------------------------------------------------
# Cross-domain product reference
# ---------------------------------------------------------------------------
PRODUCER_CATALOG  = "discovery"
PRODUCER_SCHEMA   = "gold"
PRODUCER_TABLE    = "patient_mutation_profile"
FULL_PRODUCT_NAME = f"{PRODUCER_CATALOG}.{PRODUCER_SCHEMA}.{PRODUCER_TABLE}"

# The major version the consuming pipeline was certified against.
# A mismatch raises an error and halts the pipeline — renegotiate the contract
# before bumping this value.
CERTIFIED_MAJOR_VERSION = "1"

# ---------------------------------------------------------------------------
# Expected schema — declare explicitly what the consumer depends on.
#
# This is NOT the full producer schema. Declare only the columns this pipeline
# actually uses. Unknown columns from the producer are ignored (additive changes
# are backward compatible). A column the consumer depends on that disappears
# from the producer is caught by the validation below.
# ---------------------------------------------------------------------------
EXPECTED_COLUMNS = {
    "patient_id":             "string",
    "variant_hgvs_cdna":      "string",
    "mutation_type":          "string",      # deletion | duplication | nonsense | missense | other
    "exons_affected":         "string",      # JSON array of integer exon numbers
    "reading_frame_effect":   "string",      # in_frame | out_of_frame | unknown
    "exon_51_skip_eligible":  "boolean",
    "exon_53_skip_eligible":  "boolean",
    "exon_45_skip_eligible":  "boolean",
    "exon_44_skip_eligible":  "boolean",
    "data_product_version":   "string",      # semver — checked below
    "classification_conflict": "boolean",    # ADR-06 flag — carry through to Clinical Gold
}


# ---------------------------------------------------------------------------
# Contract validation
# ---------------------------------------------------------------------------
def validate_cross_domain_schema(df: DataFrame) -> None:
    """
    Validate that the published data product schema matches what the consumer
    declared in EXPECTED_COLUMNS. Raises RuntimeError on any mismatch so the
    pipeline fails fast rather than producing wrong outputs.
    """
    live_schema = {f.name: f.dataType.simpleString() for f in df.schema.fields}

    # Map Spark type strings to ODCS-style for comparison
    type_map = {
        "string": "string", "boolean": "boolean", "bigint": "long",
        "int": "integer", "double": "double", "float": "float",
        "date": "date", "timestamp": "timestamp",
    }

    errors = []
    for col, expected_type in EXPECTED_COLUMNS.items():
        if col not in live_schema:
            errors.append(f"MISSING column '{col}' — required by consumer but absent from producer schema")
        else:
            actual = type_map.get(live_schema[col], live_schema[col])
            if actual != expected_type:
                errors.append(f"TYPE MISMATCH '{col}': consumer expects '{expected_type}', producer has '{actual}'")

    if errors:
        raise RuntimeError(
            f"Cross-domain contract violation for {FULL_PRODUCT_NAME}:\n"
            + "\n".join(f"  - {e}" for e in errors)
            + "\n\nUpdate EXPECTED_COLUMNS or renegotiate the contract before proceeding."
        )


def validate_product_version(df: DataFrame) -> None:
    """
    Check that the producer's major version matches CERTIFIED_MAJOR_VERSION.
    A major version bump indicates a breaking change — the consuming pipeline
    must be re-certified before it runs.
    """
    sample = df.select("data_product_version").limit(1).collect()
    if not sample:
        return  # empty table — skip version check

    published_version = sample[0]["data_product_version"]
    published_major   = published_version.split(".")[0]

    if published_major != CERTIFIED_MAJOR_VERSION:
        raise RuntimeError(
            f"Cross-domain version conflict for {FULL_PRODUCT_NAME}: "
            f"consumer certified against major version {CERTIFIED_MAJOR_VERSION}, "
            f"producer published version {published_version}. "
            f"Update CERTIFIED_MAJOR_VERSION and re-certify this pipeline before re-running."
        )


# ---------------------------------------------------------------------------
# Read function — wrap this in the consuming pipeline's DLT table function
# ---------------------------------------------------------------------------
def read_cross_domain_product(spark) -> DataFrame:
    """
    Read the cross-domain data product with full contract validation.
    Returns only the columns declared in EXPECTED_COLUMNS.
    Call this at the start of any DLT table function that consumes this product.
    """
    df = spark.table(FULL_PRODUCT_NAME)

    validate_cross_domain_schema(df)
    validate_product_version(df)

    # Return only the columns this pipeline depends on — do not pass unknown
    # producer columns into the consuming domain's tables
    return df.select(list(EXPECTED_COLUMNS.keys()))


# ---------------------------------------------------------------------------
# DLT table stub — the consuming pipeline's entry point
# Replace the body with the actual join/transformation logic.
# ---------------------------------------------------------------------------
@dlt.table(
    name="<consuming_table_name>",
    comment=(
        f"Consumes {FULL_PRODUCT_NAME} (certified against major version {CERTIFIED_MAJOR_VERSION}). "
        "Schema contract enforced at read time — pipeline halts on version or column mismatch."
    ),
    table_properties={
        "quality":                            "<silver|gold>",
        f"cross_domain.producer":             FULL_PRODUCT_NAME,
        f"cross_domain.certified_version":    CERTIFIED_MAJOR_VERSION,
        "delta.logRetentionDuration":         "interval 2555 days",
        "delta.deletedFileRetentionDuration": "interval 2555 days",
    },
)
def <consuming_table_name>():
    # Read the cross-domain product with contract validation
    patient_profiles = read_cross_domain_product(spark)

    # Read the local domain table to join against
    trial_catalogue = dlt.read("<local_silver_or_gold_table>")

    # ------------------------------------------------------------------
    # Join logic — replace with actual eligibility matching
    # Example: join patient mutation profiles against trial eligibility rules
    # ------------------------------------------------------------------
    return (
        patient_profiles
        .join(trial_catalogue, on="<join_key>", how="inner")
        # Add downstream transformations here
        .withColumn("pipeline_version", F.lit("<semver>"))
    )
