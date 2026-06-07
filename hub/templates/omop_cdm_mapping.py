# Databricks notebook source
# Template: OMOP CDM 5.3.1 mapping for clinical trial and variant data
#
# This template shows how to map Silver-layer data to the OMOP CDM tables
# relevant to this project. OMOP is required for:
#   - Interoperability with clinical data warehouses and EHR systems
#   - Regulatory submissions that reference OMOP CDM (EMA DARWIN EU, FDA Sentinel)
#   - Joining with real-world evidence datasets that use OMOP vocabularies
#
# Tables covered here:
#   condition_occurrence  — DMD diagnosis events
#   drug_exposure         — approved therapy prescriptions and trial enrolments
#   measurement           — variant classification as a genomic measurement
#   concept               — vocabulary lookups (sourced from Athena, not hardcoded)
#
# OMOP concept IDs must be sourced from the Athena vocabulary download
# (https://athena.ohdsi.org/) and stored in Unity Catalog as a reference table.
# Never hardcode concept IDs in pipeline logic — they can change between
# vocabulary versions. Fetch them via concept name + vocabulary_id join instead.
#
# Related: docs/adr/ (ADR referencing OMOP CDM adoption)
#          hub/templates/dlt_silver_table.py (upstream data)
#          hub/templates/dlt_gold_table.py (downstream Gold product)

import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import StructField, StructType, StringType, LongType, DateType, IntegerType

# ---------------------------------------------------------------------------
# Athena vocabulary reference table
# Load this once and broadcast for joining against Silver records.
# The concept table must be ingested into Unity Catalog from the Athena
# vocabulary download. See: https://athena.ohdsi.org/vocabulary/list
# ---------------------------------------------------------------------------
VOCABULARY_CATALOG = "<catalog>"     # e.g. "clinical"
VOCABULARY_SCHEMA  = "vocabulary"    # recommended: a dedicated schema for OMOP vocab tables
CONCEPT_TABLE      = f"{VOCABULARY_CATALOG}.{VOCABULARY_SCHEMA}.concept"

# ---------------------------------------------------------------------------
# Stable concept lookups for this project
#
# Rather than hardcoding concept IDs (which can change between Athena releases),
# look them up by name + vocabulary. Store the result in a module-level dict
# after the first run, or fetch at pipeline initialisation time.
#
# Key concepts for DMD:
#   "Duchenne muscular dystrophy"  | vocabulary_id="SNOMED" | concept_id=57676002 (verify in Athena)
#   "Exon skipping"                | vocabulary_id="SNOMED" | concept_id=<verify>
#   "Genetic finding"              | vocabulary_id="SNOMED" | concept_id=<verify>
#   "Antisense oligonucleotide"    | vocabulary_id="SNOMED" | concept_id=<verify>
#   Eteplirsen (EXONDYS 51)        | vocabulary_id="RxNorm" | concept_id=<verify>
#   Golodirsen (VYONDYS 53)        | vocabulary_id="RxNorm" | concept_id=<verify>
#   Viltolarsen (VILTEPSO)         | vocabulary_id="RxNorm" | concept_id=<verify>
#   Casimersen (AMONDYS 45)        | vocabulary_id="RxNorm" | concept_id=<verify>
# ---------------------------------------------------------------------------
def lookup_concept_id(spark, concept_name: str, vocabulary_id: str, domain_id: str) -> int:
    """
    Return the standard concept_id for a concept by name and vocabulary.
    Raises ValueError if not found or ambiguous — forces explicit resolution
    rather than silent null propagation.
    """
    rows = (
        spark.table(CONCEPT_TABLE)
        .filter(
            (F.col("concept_name") == concept_name)
            & (F.col("vocabulary_id") == vocabulary_id)
            & (F.col("domain_id") == domain_id)
            & (F.col("standard_concept") == "S")
            & (F.col("invalid_reason").isNull())
        )
        .select("concept_id", "concept_name")
        .collect()
    )
    if len(rows) == 0:
        raise ValueError(f"Concept not found: '{concept_name}' in vocabulary '{vocabulary_id}'")
    if len(rows) > 1:
        raise ValueError(f"Ambiguous concept: '{concept_name}' matched {len(rows)} rows in '{vocabulary_id}'")
    return rows[0]["concept_id"]


# ---------------------------------------------------------------------------
# 1. condition_occurrence — DMD diagnosis
#
# Maps a patient diagnosis record to OMOP condition_occurrence.
# Source: patient registry Silver table (when patient data is available).
# This table is populated in Phase 4+ when patient-level data is introduced.
# ---------------------------------------------------------------------------
CONDITION_OCCURRENCE_SCHEMA = StructType([
    StructField("condition_occurrence_id",      LongType(),    False),  # surrogate key
    StructField("person_id",                    LongType(),    False),  # patient identifier
    StructField("condition_concept_id",         IntegerType(), False),  # SNOMED concept for DMD
    StructField("condition_start_date",         DateType(),    False),  # diagnosis date
    StructField("condition_end_date",           DateType(),    True),   # null if ongoing
    StructField("condition_type_concept_id",    IntegerType(), False),  # "EHR problem list" etc.
    StructField("condition_source_value",       StringType(),  True),   # original diagnosis code (ICD-10: G71.01)
    StructField("condition_source_concept_id",  IntegerType(), True),   # ICD-10 concept_id
    # Provenance
    StructField("source_system",                StringType(),  False),
    StructField("pipeline_version",             StringType(),  False),
])

# DMD ICD-10-CM code: G71.01 (Duchenne muscular dystrophy)
# SNOMED CT: 57676002 — verify current concept_id in Athena before use
DMD_CONDITION_SOURCE_VALUE = "G71.01"


# ---------------------------------------------------------------------------
# 2. measurement — variant classification as a genomic measurement
#
# Maps a variant pathogenicity classification to OMOP measurement.
# This is the primary mechanism for representing genetic test results in OMOP.
# OMOP does not have a native genomics table in CDM 5.3.1; measurement is the
# recommended interim representation (OMOP Genomics WG guidance).
# ---------------------------------------------------------------------------
MEASUREMENT_SCHEMA = StructType([
    StructField("measurement_id",               LongType(),    False),
    StructField("person_id",                    LongType(),    True),   # null for population-level catalogue rows
    StructField("measurement_concept_id",       IntegerType(), False),  # "Genetic variation" or "Exon deletion"
    StructField("measurement_date",             DateType(),    True),   # classification date
    StructField("value_as_string",              StringType(),  True),   # ACMG tier: "Pathogenic" etc.
    StructField("value_source_value",           StringType(),  True),   # raw LOVD/ClinVar classification
    StructField("measurement_source_value",     StringType(),  True),   # HGVS cDNA notation
    StructField("unit_concept_id",              IntegerType(), True),   # null for categorical measurements
    # Provenance
    StructField("source_system",                StringType(),  False),
    StructField("pipeline_version",             StringType(),  False),
])


# ---------------------------------------------------------------------------
# 3. drug_exposure — approved therapy (for patient-level data in Phase 4+)
#
# Maps an approved DMD therapy prescription or trial enrolment to
# OMOP drug_exposure. RxNorm concept IDs for approved AONs:
#   Eteplirsen  (EXONDYS 51)  — RxNorm: verify in Athena
#   Golodirsen  (VYONDYS 53)  — RxNorm: verify in Athena
#   Viltolarsen (VILTEPSO)    — RxNorm: verify in Athena
#   Casimersen  (AMONDYS 45)  — RxNorm: verify in Athena
# ---------------------------------------------------------------------------
DRUG_EXPOSURE_SCHEMA = StructType([
    StructField("drug_exposure_id",             LongType(),    False),
    StructField("person_id",                    LongType(),    False),
    StructField("drug_concept_id",              IntegerType(), False),  # RxNorm concept for the drug
    StructField("drug_exposure_start_date",     DateType(),    False),
    StructField("drug_exposure_end_date",       DateType(),    True),
    StructField("drug_type_concept_id",         IntegerType(), False),  # "Prescription written" etc.
    StructField("drug_source_value",            StringType(),  True),   # original drug name
    StructField("drug_source_concept_id",       IntegerType(), True),
    # Provenance
    StructField("source_system",                StringType(),  False),
    StructField("pipeline_version",             StringType(),  False),
])


# ---------------------------------------------------------------------------
# Mapping function: Silver variant record → OMOP measurement row
#
# Use this as the per-row mapping function in a Silver → Gold DLT pipeline.
# Adapt field names to the actual Silver schema for your domain.
# ---------------------------------------------------------------------------
def variant_to_omop_measurement(df, measurement_concept_id: int, pipeline_version: str):
    """
    Map a Silver variant DataFrame to OMOP measurement rows.

    measurement_concept_id — the OMOP concept representing this type of
                             genomic measurement (look up via lookup_concept_id).
    """
    return (
        df
        .withColumn("measurement_id",           F.monotonically_increasing_id())
        .withColumn("person_id",                F.lit(None).cast(LongType()))  # population-level: no patient
        .withColumn("measurement_concept_id",   F.lit(measurement_concept_id).cast(IntegerType()))
        .withColumn("measurement_date",         F.to_date(F.col("classification_last_evaluated"), "yyyy/MM/dd"))
        .withColumn("value_as_string",          F.col("clinical_significance_description"))
        .withColumn("value_source_value",       F.col("effect_concluded"))   # raw LOVD notation
        .withColumn("measurement_source_value", F.col("dna_change_cdna"))    # HGVS cDNA
        .withColumn("unit_concept_id",          F.lit(None).cast(IntegerType()))
        .withColumn("pipeline_version",         F.lit(pipeline_version))
        .select(*[f.name for f in MEASUREMENT_SCHEMA.fields])
    )


# ---------------------------------------------------------------------------
# DLT table stub — wire up in the Gold pipeline
# ---------------------------------------------------------------------------
# Uncomment and adapt when building the Gold genomic measurement table.
#
# @dlt.table(
#     name="omop_measurement_dmd_variants",
#     comment="OMOP CDM 5.3.1 measurement: DMD variant pathogenicity classifications.",
#     table_properties={
#         "quality": "gold",
#         "tag.standard": "omop_cdm_5_3_1",
#         "delta.logRetentionDuration": "interval 2555 days",
#         "delta.deletedFileRetentionDuration": "interval 2555 days",
#     },
#     schema=MEASUREMENT_SCHEMA,
# )
# def omop_measurement_dmd_variants():
#     silver = dlt.read("dmd_variants")
#     # Fetch concept ID at pipeline init time — fail fast if vocabulary is missing
#     concept_id = lookup_concept_id(spark, "Genetic variation", "SNOMED", "Measurement")
#     return variant_to_omop_measurement(silver, concept_id, pipeline_version="<semver>")
