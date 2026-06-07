# Databricks notebook source
# Template: Silver transformation DLT table
#
# Silver is where source-verbatim Bronze values are parsed, normalised,
# enriched, and quality-gated. Two concerns are encoded here that must not
# drift between pipelines:
#
#   1. Quality expectations — @dlt.expect_or_quarantine (blocking) and
#      @dlt.expect_or_warn (advisory). Severity decisions are documented in
#      the Bitol ODCS contract for this table.
#
#   2. ADR-06 conflict detection — classification_conflict,
#      classification_conflict_internal, and action_required must be set
#      here, never in Bronze (too early) or Gold (too late to quarantine).
#
# Related: docs/adr/adr_06.md
#          docs/contracts/<table_name>.yaml
#          hub/templates/dlt_bronze_table.py (upstream)
#          hub/templates/dlt_gold_table.py (downstream)

import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import StructField, StructType, StringType, BooleanType, TimestampType

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SILVER_SCHEMA = StructType([
    # Normalised source fields — replace with actual fields
    StructField("<pk>",                          StringType(),  False),
    StructField("<normalised_field>",            StringType(),  True),

    # ADR-06 conflict flags — required on every Silver variant/classification table
    StructField("classification_conflict",       BooleanType(), False),  # LOVD vs ClinVar disagreement
    StructField("classification_conflict_internal", BooleanType(), False),  # ClinVar internal disagreement
    StructField("action_required",               StringType(),  True),   # 'expert_review' | 'manual_review' | null

    # Provenance — carry forward from Bronze, add pipeline metadata
    StructField("source_system",                 StringType(),  False),
    StructField("ingestion_timestamp",           StringType(),  False),
    StructField("pipeline_version",              StringType(),  False),
])

PIPELINE_VERSION = "0.1.0"  # bump on every schema-affecting change


# ---------------------------------------------------------------------------
# Quality rule helpers
#
# Use these as the condition strings in @dlt.expect_or_quarantine /
# @dlt.expect_or_warn. Document each rule's severity choice in the contract.
#
# Severity guide:
#   expect_or_quarantine — record cannot be used safely in Gold; quarantine it
#   expect_or_warn       — record is imperfect but usable; raise alert, keep it
# ---------------------------------------------------------------------------
QUALITY_RULES = {
    # Blocking — missing PK breaks all downstream joins
    "pk_not_null":          "<pk> IS NOT NULL",

    # Blocking — a variant we cannot place on the exon map cannot contribute
    # to reading frame computation (see docs/scientific_background.md)
    "exon_parseable":       "exon_raw IS NOT NULL OR position_mrna IS NOT NULL",

    # Blocking — action_required must be a known value or null
    "action_required_valid": (
        "action_required IN ('expert_review', 'manual_review') "
        "OR action_required IS NULL"
    ),

    # Advisory — classification without a date is low-confidence for ADR-06
    "classification_dated":  "classification_last_evaluated IS NOT NULL",

    # Advisory — records without a ClinVar cross-reference cannot be checked
    # against the cross-source conflict rule; flag but do not quarantine
    "clinvar_id_present":    "clinvar_id IS NOT NULL",
}


# ---------------------------------------------------------------------------
# ADR-06 conflict detection helpers
# ---------------------------------------------------------------------------
def _lovd_to_acmg(lovd_effect_col):
    """Map LOVD +/+?/-/-?/?/. notation to ACMG 5-tier string."""
    return (
        F.when(lovd_effect_col == "+",  "Pathogenic")
         .when(lovd_effect_col == "+?", "Likely pathogenic")
         .when(lovd_effect_col == "-",  "Benign")
         .when(lovd_effect_col == "-?", "Likely benign")
         .when(lovd_effect_col == "?",  "Uncertain significance")
         .otherwise(None)  # "." (not provided) and unknowns → null
    )


def add_conflict_flags(df, lovd_acmg_col: str, clinvar_classification_col: str, clinvar_internal_conflict_col: str):
    """
    Apply ADR-06 two-layer conflict detection.

    lovd_acmg_col               — column already mapped to ACMG tier from LOVD
    clinvar_classification_col  — ClinVar germline_classification.description
    clinvar_internal_conflict_col — boolean: True if ClinVar itself has conflicting submitters

    Returns df with classification_conflict, classification_conflict_internal,
    and action_required columns set.
    """
    # Layer 1: ClinVar's own submitters disagree
    df = df.withColumn(
        "classification_conflict_internal",
        F.col(clinvar_internal_conflict_col).cast(BooleanType()),
    )

    # Layer 2: LOVD and ClinVar disagree across sources
    df = df.withColumn(
        "classification_conflict",
        F.when(
            F.col(lovd_acmg_col).isNotNull()
            & F.col(clinvar_classification_col).isNotNull()
            & (F.col(lovd_acmg_col) != F.col(clinvar_classification_col)),
            F.lit(True),
        ).otherwise(F.lit(False)),
    )

    # action_required: set to expert_review if any conflict flag is true
    df = df.withColumn(
        "action_required",
        F.when(
            F.col("classification_conflict") | F.col("classification_conflict_internal"),
            F.lit("expert_review"),
        ).otherwise(F.lit(None).cast(StringType())),
    )

    return df


# ---------------------------------------------------------------------------
# Silver DLT table
# ---------------------------------------------------------------------------
@dlt.table(
    name="<table_name>",
    comment=(
        "Silver: normalised and quality-gated records from <source>. "
        "ADR-06 conflict flags applied. Records failing blocking rules "
        "are quarantined and do not flow to Gold."
    ),
    table_properties={
        "quality":                            "silver",
        "pipelines.autoOptimize.managed":     "true",
        "delta.logRetentionDuration":         "interval 2555 days",
        "delta.deletedFileRetentionDuration": "interval 2555 days",
    },
    schema=SILVER_SCHEMA,
)
@dlt.expect_or_quarantine("pk_not_null",          QUALITY_RULES["pk_not_null"])
@dlt.expect_or_quarantine("exon_parseable",        QUALITY_RULES["exon_parseable"])
@dlt.expect_or_quarantine("action_required_valid", QUALITY_RULES["action_required_valid"])
@dlt.expect_or_warn("classification_dated",        QUALITY_RULES["classification_dated"])
@dlt.expect_or_warn("clinvar_id_present",          QUALITY_RULES["clinvar_id_present"])
def <table_name>():
    bronze = dlt.read("<bronze_table_name>_raw")

    # ------------------------------------------------------------------
    # Step 1 — Field normalisation
    # Parse, cast, and rename fields from Bronze verbatim to Silver types.
    # Do not apply business logic here — keep normalisation and enrichment
    # in separate steps so each is independently testable.
    # ------------------------------------------------------------------
    df = (
        bronze
        .withColumn("<normalised_field>", F.trim(F.col("<raw_field>")))
        # ... add normalisations ...
    )

    # ------------------------------------------------------------------
    # Step 2 — LOVD pathogenicity mapping to ACMG tier
    # Only needed for pipelines joining LOVD and ClinVar.
    # ------------------------------------------------------------------
    df = df.withColumn("lovd_acmg", _lovd_to_acmg(F.col("effect_concluded")))

    # ------------------------------------------------------------------
    # Step 3 — ADR-06 conflict detection
    # Pass the correct column names for this pipeline.
    # ------------------------------------------------------------------
    df = add_conflict_flags(
        df,
        lovd_acmg_col="lovd_acmg",
        clinvar_classification_col="clinvar_classification",
        clinvar_internal_conflict_col="clinvar_conflict_internal_flag",
    )

    # ------------------------------------------------------------------
    # Step 4 — Provenance
    # ------------------------------------------------------------------
    df = df.withColumn("pipeline_version", F.lit(PIPELINE_VERSION))

    return df
