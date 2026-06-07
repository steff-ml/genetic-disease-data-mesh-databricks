# Databricks notebook source
# Template: Gold data product DLT table
#
# Gold tables are versioned, governed data products with a published Bitol ODCS
# contract in docs/contracts/. Before a Gold table goes to "active" status:
#   - The contract file exists and is filled in
#   - contract_check.py passes with zero drift errors
#   - The table is tagged in Unity Catalog for Marketplace discoverability
#   - pipeline_version is set and bumped on every schema-affecting change
#
# Gold tables read from Silver. They apply a final quality gate (quarantine
# records that slipped through Silver without detection) and add governance
# metadata. No business logic that is not already encoded in Silver.
#
# Related: docs/contracts/<table_name>.yaml (must exist before status → active)
#          hub/templates/dlt_silver_table.py (upstream)
#          hub/templates/contract_check.py (pre-release validation)
#          hub/templates/cross_domain_interface.py (if consuming a cross-domain product)

import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import StructField, StructType, StringType, BooleanType, TimestampType

# ---------------------------------------------------------------------------
# Versioning — bump minor on additive changes, major on breaking schema changes.
# Consumers pin to a major version; minor bumps must be backward compatible.
# ---------------------------------------------------------------------------
DATA_PRODUCT_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Schema — must match the models section in docs/contracts/<table_name>.yaml exactly.
# Run contract_check.py before promoting to active status.
# ---------------------------------------------------------------------------
GOLD_SCHEMA = StructType([
    StructField("<pk>",                      StringType(),  False),
    StructField("<business_field>",          StringType(),  True),

    # Quality provenance — carry action_required so consumers know which records
    # required expert intervention before Gold promotion
    StructField("action_required",           StringType(),  True),  # null = clean record
    StructField("classification_conflict",   BooleanType(), False),

    # Data product metadata
    StructField("data_product_version",      StringType(),  False),
    StructField("pipeline_version",          StringType(),  False),
    StructField("source_system",             StringType(),  False),
    StructField("ingestion_timestamp",       StringType(),  False),
])


# ---------------------------------------------------------------------------
# Gold DLT table
# ---------------------------------------------------------------------------
@dlt.table(
    name="<table_name>",
    comment=(
        "Gold data product: <one-line description>. "
        f"Schema version {DATA_PRODUCT_VERSION}. "
        "Published contract: docs/contracts/<table_name>.yaml."
    ),
    table_properties={
        "quality":                              "gold",
        "data_product_version":                 DATA_PRODUCT_VERSION,
        # Unity Catalog tags — used by Marketplace and by contract_check.py
        "tag.domain":                           "<clinical|discovery>",
        "tag.product":                          "<product_name>",
        "tag.disease":                          "dmd",
        "tag.standard":                         "omop_cdm_5_3_1",        # if applicable
        "tag.contract":                         "docs/contracts/<table_name>.yaml",
        "pipelines.autoOptimize.managed":       "true",
        "delta.logRetentionDuration":           "interval 2555 days",
        "delta.deletedFileRetentionDuration":   "interval 2555 days",
    },
    schema=GOLD_SCHEMA,
)
# Final quality gate — records that should have been quarantined in Silver
# but were not (e.g. null PK introduced by a join) are caught here.
# Do not add rules here that Silver already enforces — they add latency
# without catching new failure modes.
@dlt.expect_or_quarantine("gold_pk_not_null", "<pk> IS NOT NULL")
@dlt.expect_or_quarantine(
    "no_unreviewed_conflicts",
    # Records flagged for expert review must not be auto-promoted to Gold.
    # They remain in the quarantine table until action_required is cleared
    # by a human reviewer and the pipeline is re-run.
    "action_required IS NULL OR action_required != 'expert_review'",
)
def <table_name>():
    silver = dlt.read("<silver_table_name>")

    # ------------------------------------------------------------------
    # If this Gold table reads from a cross-domain data product, use
    # hub/templates/cross_domain_interface.py instead of dlt.read() here.
    # ------------------------------------------------------------------

    return (
        silver
        # Select only the columns declared in the Gold schema.
        # Do not pass Silver-internal columns (intermediate join keys,
        # raw text fields before normalisation) through to Gold.
        .select(
            F.col("<pk>"),
            F.col("<business_field>"),
            F.col("action_required"),
            F.col("classification_conflict"),
            F.lit(DATA_PRODUCT_VERSION).alias("data_product_version"),
            F.lit("<pipeline_semver>").alias("pipeline_version"),
            F.col("source_system"),
            F.col("ingestion_timestamp"),
        )
    )
