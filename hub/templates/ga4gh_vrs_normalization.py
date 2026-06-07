# Template: GA4GH VRS v2 variant normalization
#
# GA4GH VRS (Variant Representation Specification) is the machine-stable
# identifier standard for genomic variants. While HGVS is human-readable and
# used by clinicians and databases, VRS provides a digest-based ID that is
# stable across reference genome assemblies and database versions.
#
# WHY VRS ALONGSIDE HGVS
# =======================
# HGVS identifiers are human-readable but not stable:
#   - The same deletion described against NM_004006.2 vs NM_004006.3 produces
#     different HGVS strings even though the variant is identical
#   - HGVS does not normalise left-shift ambiguity (an insertion at a repeated
#     region can be written multiple ways)
#   - External platforms (Terra, gnomAD, ClinGen) use VRS for cross-system joins
#
# VRS solves this by:
#   1. Normalising to a canonical left-shifted, trimmed representation
#   2. Computing a SHA-512 digest of the normalised form → stable ID regardless
#      of which HGVS string was used to describe the variant
#   3. Allowing cross-system joins without HGVS string matching
#
# WHEN TO APPLY VRS IN THIS PROJECT
# ==================================
# - Silver `dmd_variants` table: add `vrs_allele_id` alongside `canonical_hgvs`
# - Gold `dmd_mutation_catalogue`: VRS ID is the join key for external consumers
# - Gold `patient_mutation_profile`: VRS ID enables linkage with Terra, gnomAD,
#   and any system that follows the GA4GH data connect standard
#
# ARCHITECTURE NOTE
# =================
# VRS computation requires access to reference sequences (via SeqRepo or
# the GA4GH refget API). In this project, use the hosted refget endpoint
# at refget.org or deploy a local SeqRepo snapshot in a Unity Catalog Volume.
#
# Dependencies: pip install ga4gh.vrs ga4gh.vrs[extras] biocommons.seqrepo
#
# Related: hub/templates/hgvs_normalization.py (HGVS must be normalised first)
#          hub/templates/dlt_silver_table.py (where VRS is added)
#          hub/templates/dlt_gold_table.py (Gold consumers use VRS as join key)

from dataclasses import dataclass
from typing import Optional


@dataclass
class VrsResult:
    """Result of a VRS normalization attempt."""
    canonical_hgvs:     str
    vrs_allele_id:      Optional[str]   # ga4gh:VA.<digest> — stable cross-system ID
    vrs_allele_json:    Optional[str]   # full VRS Allele object as JSON string
    assembly:           str             # GRCh38
    chromosome:         Optional[str]   # chrX for DMD
    success:            bool
    error:              Optional[str]


# ---------------------------------------------------------------------------
# Reference configuration for DMD (NM_004006.2 / ENST00000357033)
# ---------------------------------------------------------------------------
DMD_REFSEQ_ACCESSION  = "NM_004006.2"   # transcript reference
DMD_CHROMOSOME        = "X"
DMD_ASSEMBLY          = "GRCh38"

# SeqRepo data directory — set this to the local snapshot path or use the
# hosted refget endpoint. In production, mount a SeqRepo snapshot in a
# Unity Catalog Volume and point SEQREPO_DIR at the mount path.
SEQREPO_DIR = "/Volumes/<catalog>/<schema>/references/seqrepo/2024-02-20"
# Alternative: use the hosted refget API (no local SeqRepo required)
REFGET_ENDPOINT = "https://refget.ensembl.org/sequence/"


def compute_vrs_id(canonical_hgvs: str, use_refget: bool = False) -> VrsResult:
    """
    Compute the GA4GH VRS Allele ID for a normalised HGVS string.

    Parameters
    ----------
    canonical_hgvs : normalised HGVS string (output of hgvs_normalization.normalize_hgvs)
    use_refget     : if True, use the hosted refget API instead of local SeqRepo

    Returns
    -------
    VrsResult with vrs_allele_id set if successful.
    The VRS ID has the form "ga4gh:VA.<base64url-encoded-sha512-digest>".
    """
    try:
        from ga4gh.vrs import models, normalize
        from ga4gh.vrs.dataproxy import SeqRepoRESTDataProxy, SeqRepoDataProxy
        import ga4gh.vrs.extras.translator as t
        import json

        if use_refget:
            dp = SeqRepoRESTDataProxy(base_url=REFGET_ENDPOINT)
        else:
            from biocommons.seqrepo import SeqRepo
            sr = SeqRepo(SEQREPO_DIR)
            dp = SeqRepoDataProxy(sr)

        translator = t.Translator(data_proxy=dp)

        # Translate HGVS → VRS Allele object (normalises left-shift ambiguity)
        allele = translator.translate_from(canonical_hgvs, "hgvs")

        # Compute the stable digest ID
        allele._id = models.ga4gh_identify(allele)

        return VrsResult(
            canonical_hgvs=canonical_hgvs,
            vrs_allele_id=str(allele._id),
            vrs_allele_json=json.dumps(allele.model_dump()),
            assembly=DMD_ASSEMBLY,
            chromosome=DMD_CHROMOSOME,
            success=True,
            error=None,
        )

    except ImportError:
        return VrsResult(
            canonical_hgvs=canonical_hgvs,
            vrs_allele_id=None,
            vrs_allele_json=None,
            assembly=DMD_ASSEMBLY,
            chromosome=None,
            success=False,
            error="ga4gh.vrs not installed — run: pip install 'ga4gh.vrs[extras]'",
        )
    except Exception as e:
        return VrsResult(
            canonical_hgvs=canonical_hgvs,
            vrs_allele_id=None,
            vrs_allele_json=None,
            assembly=DMD_ASSEMBLY,
            chromosome=None,
            success=False,
            error=str(e)[:200],
        )


# ---------------------------------------------------------------------------
# Spark UDF wrapper — use this in DLT Silver/Gold pipelines
# ---------------------------------------------------------------------------
def register_vrs_udf(spark, use_refget: bool = False):
    """
    Register compute_vrs_id as a Spark SQL UDF.

    Usage in DLT pipeline:
        from ga4gh_vrs_normalization import register_vrs_udf
        register_vrs_udf(spark)
        df = df.withColumn("vrs", F.expr("compute_vrs_udf(canonical_hgvs)"))
        df = df.withColumn("vrs_allele_id",   F.col("vrs.vrs_allele_id"))
        df = df.withColumn("vrs_allele_json", F.col("vrs.vrs_allele_json"))

    Note: VRS computation is CPU-intensive. Apply only to records where
    canonical_hgvs is non-null (strategy != 'unparseable'). Records that
    could not be normalised by HGVS will not get a VRS ID.
    """
    from pyspark.sql.types import StructType, StructField, StringType, BooleanType

    result_type = StructType([
        StructField("vrs_allele_id",   StringType(),  True),
        StructField("vrs_allele_json", StringType(),  True),
        StructField("assembly",        StringType(),  False),
        StructField("chromosome",      StringType(),  True),
        StructField("success",         BooleanType(), False),
        StructField("error",           StringType(),  True),
    ])

    def _udf(canonical_hgvs):
        if not canonical_hgvs:
            return (None, None, DMD_ASSEMBLY, None, False, "empty input")
        r = compute_vrs_id(canonical_hgvs, use_refget=use_refget)
        return (r.vrs_allele_id, r.vrs_allele_json, r.assembly, r.chromosome, r.success, r.error)

    spark.udf.register("compute_vrs_udf", _udf, result_type)


# ---------------------------------------------------------------------------
# VRS ID validation — confirm external consumers can resolve the ID
# ---------------------------------------------------------------------------
def validate_vrs_id(vrs_id: str) -> bool:
    """
    Validate that a VRS ID follows the ga4gh:VA.<digest> format.
    Does not contact any external service — format check only.
    """
    import re
    return bool(re.match(r"^ga4gh:VA\.[A-Za-z0-9_-]{32,}$", vrs_id or ""))
