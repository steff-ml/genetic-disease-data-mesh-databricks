# Databricks notebook source
# Template: MLflow-governed GenAI batch inference pipeline
#
# Use this template for any pipeline that applies a language model to extract
# structured data from free text — the primary use case is Phase 1.3:
# extracting mutation eligibility rules from trial eligibility criteria text.
#
# Governance model:
#   - The model is registered in MLflow Model Registry before this pipeline runs.
#     No ad-hoc model loading (no local file paths, no direct API keys in code).
#   - Every inference call is logged to an MLflow run for reproducibility.
#   - Each output record carries a confidence score. Records below the threshold
#     are routed to a human review queue instead of flowing to Silver.
#   - The prompt template is versioned alongside the model — changing the prompt
#     is a model version bump, not a code change.
#
# Confidence routing:
#   confidence >= HIGH_CONFIDENCE_THRESHOLD  → write to silver output table
#   confidence <  HIGH_CONFIDENCE_THRESHOLD  → write to review queue with
#                                               action_required = 'low_confidence_extraction'
#
# Related: docs/model-card.md (model documentation)
#          hub/templates/dlt_silver_table.py (downstream Silver consumer)
#          docs/adr/ (ADR for GenAI extraction approach)

import dlt
import mlflow
import mlflow.pyfunc
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructField, StructType, StringType, FloatType, BooleanType, ArrayType
)
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Model configuration — all sourced from MLflow Model Registry.
# Never load a model from a local path or pass API credentials in code.
# ---------------------------------------------------------------------------
MLFLOW_MODEL_NAME    = "<registered_model_name>"   # e.g. "eligibility_criteria_extractor"
MLFLOW_MODEL_ALIAS   = "champion"                  # or a specific version: "v3"
                                                    # "champion" always points to the production model

HIGH_CONFIDENCE_THRESHOLD = 0.85  # records below this go to human review
BATCH_SIZE                = 50    # records per model call — tune to context window size

# ---------------------------------------------------------------------------
# Output schema — structured extraction result
#
# Every output record must carry:
#   - the extracted structured fields
#   - confidence_score for the extraction as a whole
#   - per_field_confidence for field-level confidence (optional but recommended)
#   - model_version so the extraction can be re-run if the model changes
#   - action_required = 'low_confidence_extraction' if below threshold
# ---------------------------------------------------------------------------
EXTRACTION_SCHEMA = StructType([
    # Source record identifier — carry through for join back to Silver
    StructField("source_id",                    StringType(),  False),
    StructField("source_text",                  StringType(),  True),   # verbatim input text (for audit)

    # Extracted fields — replace with fields relevant to your extraction task
    StructField("mutation_type_extracted",      StringType(),  True),   # e.g. "deletion", "duplication"
    StructField("exon_targets_extracted",       StringType(),  True),   # e.g. "51" or "45-55" (JSON string)
    StructField("reading_frame_rule_mentioned", BooleanType(), True),   # True if text references reading frame
    StructField("genetic_criteria_present",     BooleanType(), False),  # True if any genetic criterion found

    # Confidence
    StructField("confidence_score",             FloatType(),   False),  # overall extraction confidence [0, 1]
    StructField("low_confidence_fields",        StringType(),  True),   # JSON list of field names below threshold

    # Governance
    StructField("action_required",              StringType(),  True),   # 'low_confidence_extraction' | null
    StructField("model_name",                   StringType(),  False),
    StructField("model_version",                StringType(),  False),
    StructField("prompt_version",               StringType(),  False),
    StructField("inference_timestamp",          StringType(),  False),
    StructField("source_system",                StringType(),  False),
    StructField("pipeline_version",             StringType(),  False),
])

PIPELINE_VERSION = "0.1.0"
SOURCE_SYSTEM    = "<source_name>_genai_extraction"


# ---------------------------------------------------------------------------
# Prompt template
#
# The prompt is versioned here alongside the code. A change to the prompt
# must bump PROMPT_VERSION and be accompanied by an evaluation run comparing
# extraction quality before and after. Document the evaluation in model-card.md.
#
# The prompt should:
#   1. Specify the output format (JSON with confidence scores)
#   2. Define the fields to extract with examples
#   3. Instruct the model to return null for fields it cannot determine
#      (never fabricate — a null is better than a hallucinated value)
#   4. Request a confidence score for each field and an overall score
# ---------------------------------------------------------------------------
PROMPT_VERSION = "v1.0"

SYSTEM_PROMPT = """You are a clinical data extraction assistant specialising in rare disease genetics.
Extract structured eligibility criteria from the provided clinical trial text.
Return ONLY valid JSON matching the schema below. Do not add commentary.
For fields you cannot determine from the text, return null.
Return confidence scores between 0.0 and 1.0 for each field and an overall score.

Output schema:
{
  "mutation_type_extracted": string | null,
  "exon_targets_extracted": string | null,
  "reading_frame_rule_mentioned": boolean | null,
  "genetic_criteria_present": boolean,
  "field_confidence": {
    "mutation_type_extracted": float,
    "exon_targets_extracted": float,
    "reading_frame_rule_mentioned": float,
    "genetic_criteria_present": float
  },
  "overall_confidence": float
}"""

USER_PROMPT_TEMPLATE = """Extract genetic eligibility criteria from this clinical trial text:

---
{eligibility_text}
---"""


# ---------------------------------------------------------------------------
# Model loader — called once per pipeline run, not per record
# ---------------------------------------------------------------------------
def load_model():
    """Load the champion model from MLflow Model Registry."""
    model_uri = f"models:/{MLFLOW_MODEL_NAME}@{MLFLOW_MODEL_ALIAS}"
    model = mlflow.pyfunc.load_model(model_uri)
    model_version = mlflow.MlflowClient().get_model_version_by_alias(
        MLFLOW_MODEL_NAME, MLFLOW_MODEL_ALIAS
    ).version
    return model, str(model_version)


# ---------------------------------------------------------------------------
# Inference function — apply to one record
# ---------------------------------------------------------------------------
def extract_one(model, source_id: str, text: str, model_version: str) -> dict:
    """
    Apply the model to one eligibility text. Returns a dict matching
    EXTRACTION_SCHEMA. On model error, returns a low-confidence record
    with action_required = 'low_confidence_extraction' so the error is
    surfaced in the human review queue rather than silently dropped.
    """
    import json

    ts = datetime.now(timezone.utc).isoformat()
    prompt = USER_PROMPT_TEMPLATE.format(eligibility_text=text or "")

    try:
        # The MLflow pyfunc model wraps the underlying LLM call.
        # Input format depends on the model's signature — adjust as needed.
        raw_output = model.predict([{"role": "system", "content": SYSTEM_PROMPT},
                                    {"role": "user",   "content": prompt}])
        result = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
    except Exception as e:
        return {
            "source_id":                    source_id,
            "source_text":                  text,
            "mutation_type_extracted":      None,
            "exon_targets_extracted":       None,
            "reading_frame_rule_mentioned": None,
            "genetic_criteria_present":     False,
            "confidence_score":             0.0,
            "low_confidence_fields":        json.dumps(["all"]),
            "action_required":              "low_confidence_extraction",
            "model_name":                   MLFLOW_MODEL_NAME,
            "model_version":                model_version,
            "prompt_version":               PROMPT_VERSION,
            "inference_timestamp":          ts,
            "source_system":                SOURCE_SYSTEM,
            "pipeline_version":             PIPELINE_VERSION,
        }

    overall_confidence = float(result.get("overall_confidence", 0.0))
    field_conf         = result.get("field_confidence", {})
    low_conf_fields    = [f for f, c in field_conf.items() if float(c) < HIGH_CONFIDENCE_THRESHOLD]

    return {
        "source_id":                    source_id,
        "source_text":                  text,
        "mutation_type_extracted":      result.get("mutation_type_extracted"),
        "exon_targets_extracted":       result.get("exon_targets_extracted"),
        "reading_frame_rule_mentioned": result.get("reading_frame_rule_mentioned"),
        "genetic_criteria_present":     bool(result.get("genetic_criteria_present", False)),
        "confidence_score":             overall_confidence,
        "low_confidence_fields":        json.dumps(low_conf_fields) if low_conf_fields else None,
        "action_required":              "low_confidence_extraction" if overall_confidence < HIGH_CONFIDENCE_THRESHOLD else None,
        "model_name":                   MLFLOW_MODEL_NAME,
        "model_version":                model_version,
        "prompt_version":               PROMPT_VERSION,
        "inference_timestamp":          ts,
        "source_system":                SOURCE_SYSTEM,
        "pipeline_version":             PIPELINE_VERSION,
    }


# ---------------------------------------------------------------------------
# DLT table: structured extraction output (Silver)
# ---------------------------------------------------------------------------
@dlt.table(
    name="<source>_eligibility_extracted",
    comment=(
        "Silver: structured eligibility criteria extracted from free text using "
        f"MLflow model '{MLFLOW_MODEL_NAME}' (alias: {MLFLOW_MODEL_ALIAS}). "
        "Records below confidence threshold are routed to human review via action_required."
    ),
    table_properties={
        "quality":                            "silver",
        "model_name":                         MLFLOW_MODEL_NAME,
        "prompt_version":                     PROMPT_VERSION,
        "pipelines.autoOptimize.managed":     "true",
        "delta.logRetentionDuration":         "interval 2555 days",
        "delta.deletedFileRetentionDuration": "interval 2555 days",
    },
    schema=EXTRACTION_SCHEMA,
)
@dlt.expect_or_quarantine("source_id_not_null", "source_id IS NOT NULL")
@dlt.expect_or_warn("high_confidence",          f"confidence_score >= {HIGH_CONFIDENCE_THRESHOLD}")
def <source>_eligibility_extracted():
    source_df = dlt.read("<source_silver_table>")

    # Load model once — do not reload per partition
    model, model_version = load_model()

    with mlflow.start_run(run_name=f"batch_inference_{MLFLOW_MODEL_NAME}_{model_version}"):
        mlflow.log_params({
            "model_name":    MLFLOW_MODEL_NAME,
            "model_version": model_version,
            "prompt_version": PROMPT_VERSION,
            "confidence_threshold": HIGH_CONFIDENCE_THRESHOLD,
            "batch_size":    BATCH_SIZE,
            "source_table":  "<source_silver_table>",
        })

        rows = source_df.select("source_id", "<eligibility_text_column>").collect()
        results = [
            extract_one(model, row["source_id"], row["<eligibility_text_column>"], model_version)
            for row in rows
        ]

        mlflow.log_metrics({
            "total_records":          len(results),
            "high_confidence_count":  sum(1 for r in results if r["confidence_score"] >= HIGH_CONFIDENCE_THRESHOLD),
            "review_queue_count":     sum(1 for r in results if r["action_required"] == "low_confidence_extraction"),
        })

    return spark.createDataFrame(results, schema=EXTRACTION_SCHEMA)
