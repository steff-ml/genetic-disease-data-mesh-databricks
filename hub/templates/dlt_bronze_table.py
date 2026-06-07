# Databricks notebook source
# Template: Bronze ingestion DLT table
#
# Copy into your bundle's pipeline directory and replace all <PLACEHOLDER> values.
# Remove the pattern you are not using (REST pagination or Autoloader).
# Do not modify the provenance fields or retention table_properties.
#
# Related: docs/contracts/_template.yaml (schema contract)
#          hub/templates/audit_trail_config.py (retention configuration detail)

import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import StructField, StructType, StringType, LongType, TimestampType
from datetime import datetime, timezone
import requests
import time

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SOURCE_SYSTEM = "<source_name>"       # e.g. "lovd_shared", "clinvar", "ctgov"
API_VERSION   = "<api_version>"       # e.g. "lovd3_rest_v1", "clinvar_eutils_v1"
BASE_URL      = "<base_api_url>"      # e.g. "https://databases.lovd.nl/shared/api/rest.php"
PAGE_SIZE     = 100

# ---------------------------------------------------------------------------
# Schema — always explicit, never inferred.
#
# All-null columns cause PySparkValueError: CANNOT_DETERMINE_TYPE at inference
# time. Add one StructField per column returned by the source, even if it will
# be null for most records — use StringType(True) for optional fields.
# ALCOA+ provenance fields are required on every Bronze table (last four).
# ---------------------------------------------------------------------------
BRONZE_SCHEMA = StructType([
    # Source fields — replace with actual fields from the exploration notebook
    StructField("<source_pk>",         StringType(), False),  # source primary key — must not be null
    StructField("<field_one>",         StringType(), True),
    StructField("<field_two>",         StringType(), True),
    # ... add remaining source fields ...

    # ALCOA+ provenance — do not remove or rename
    StructField("source_system",       StringType(), False),
    StructField("ingestion_timestamp", StringType(), False),  # UTC ISO-8601 string
    StructField("api_version",         StringType(), False),
    StructField("source_url",          StringType(), False),
])


# ---------------------------------------------------------------------------
# Helper: build a Bronze row dict from one source record
# Keep transformation logic out of here — Bronze stores verbatim source values.
# ---------------------------------------------------------------------------
def to_bronze_row(record: dict, source_url: str) -> dict:
    return {
        "<source_pk>":         record.get("<source_pk_field>"),
        "<field_one>":         record.get("<field_one_key>"),
        "<field_two>":         record.get("<field_two_key>"),
        "source_system":       SOURCE_SYSTEM,
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_version":         API_VERSION,
        "source_url":          source_url,
    }


# ---------------------------------------------------------------------------
# Bronze DLT table
# ---------------------------------------------------------------------------
@dlt.table(
    name="<table_name>_raw",
    comment=(
        "Bronze: raw ingestion from <source_name>. "
        "No transformation applied — values stored verbatim from source API. "
        "ALCOA+ provenance attached at write time."
    ),
    table_properties={
        "quality":                              "bronze",
        "source_system":                        SOURCE_SYSTEM,
        "pipelines.autoOptimize.managed":       "true",
        # 21 CFR Part 11 — 7-year minimum retention. Do not reduce.
        "delta.logRetentionDuration":           "interval 2555 days",
        "delta.deletedFileRetentionDuration":   "interval 2555 days",
    },
    schema=BRONZE_SCHEMA,
)
# Quarantine records missing the source primary key — they cannot be joined
# in Silver and would silently inflate deduplication counts.
@dlt.expect_or_quarantine("source_pk_not_null", "<source_pk> IS NOT NULL")
def <table_name>_raw():
    """
    Choose one of the two ingestion patterns below and delete the other.

    Pattern A — REST API with cursor/offset pagination
      Use for: LOVD, ClinVar E-utilities, ClinicalTrials.gov, EU CTR
      Not suitable for: sources with >500k records (use Pattern B instead)

    Pattern B — Autoloader reading from a cloud storage landing zone
      Use for: ClinVar FTP weekly snapshot (variant_summary.txt.gz),
               any bulk file delivery via SFTP or S3
    """

    # ------------------------------------------------------------------
    # Pattern A: REST API with offset pagination
    # ------------------------------------------------------------------
    rows = []
    start = 1  # 1-based offset; adjust to 0 if source is 0-based

    while True:
        url = f"{BASE_URL}/<endpoint>"
        resp = requests.get(
            url,
            params={"start": start, "limit": PAGE_SIZE},
            headers={"Accept": "application/json"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        records = data.get("<records_key>", [])  # adjust key to match API shape
        if not records:
            break

        for record in records:
            rows.append(to_bronze_row(record, resp.url))

        if len(records) < PAGE_SIZE:
            break
        start += PAGE_SIZE
        time.sleep(0.35)  # ~3 req/s; reduce to 0.1 if API key raises limit to 10 req/s

    return spark.createDataFrame(rows, schema=BRONZE_SCHEMA)

    # ------------------------------------------------------------------
    # Pattern B: Autoloader — cloud storage landing zone
    # Uncomment and delete Pattern A when using bulk file delivery.
    # ------------------------------------------------------------------
    # LANDING_PATH    = "/Volumes/<catalog>/<schema>/landing/<table_name>/"
    # CHECKPOINT_PATH = "/Volumes/<catalog>/<schema>/checkpoints/<table_name>_schema"
    #
    # return (
    #     spark.readStream
    #     .format("cloudFiles")
    #     .option("cloudFiles.format", "csv")           # or "json", "parquet"
    #     .option("cloudFiles.schemaLocation", CHECKPOINT_PATH)
    #     .option("header", "true")
    #     .option("sep", "\t")                           # adjust delimiter
    #     .schema(BRONZE_SCHEMA)
    #     .load(LANDING_PATH)
    #     .withColumn("source_system",       F.lit(SOURCE_SYSTEM))
    #     .withColumn("ingestion_timestamp", F.date_format(F.current_timestamp(), "yyyy-MM-dd'T'HH:mm:ssXXX"))
    #     .withColumn("api_version",         F.lit(API_VERSION))
    #     .withColumn("source_url",          F.lit(LANDING_PATH))
    # )
