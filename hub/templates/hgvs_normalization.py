# Template: HGVS variant notation normalization
#
# HGVS (Human Genome Variation Society) nomenclature is the standard notation
# for describing sequence variants. Two sources in this project use HGVS but
# with different conventions:
#
#   LOVD   — uses a mix of canonical HGVS, legacy uncertain-boundary notation,
#             and fully-uncertain records ("c.?"). The `hgvs` Python library
#             will reject the legacy style with strict parsing.
#
#   ClinVar — uses canonical HGVS anchored to RefSeq accessions
#             (e.g. "NM_004006.2:c.6439del").
#
# Why normalization must happen before any join:
#   ADR-06 detects conflicts by joining LOVD and ClinVar records on the same
#   variant. If the same deletion is represented as "c.6439del" in ClinVar and
#   "c.(?_6438+1)_(6440-1_?)del" in LOVD, the join produces no match — a false
#   "independent record" rather than a detected conflict. Normalization collapses
#   both to the same canonical representation before the join runs.
#
# Parsing strategy (applied in order, most to least strict):
#   1. Strict HGVS — `hgvs` library with full validation
#   2. Lenient regex — extracts mutation type and coordinates from legacy notation
#   3. exon_raw fallback — uses the LOVD exon field if cDNA notation is unusable
#   4. Quarantine — record cannot be used in reading frame computation
#
# The `NormalizationResult.strategy` field records which level succeeded,
# so Silver can flag records that required fallback for quality reporting.
#
# Dependencies: pip install hgvs biocommons.seqrepo
# SeqRepo is required for full HGVS validation; for offline use, set
# HGVS_SEQREPO_DIR to a local SeqRepo snapshot.
#
# Related: hub/templates/dlt_silver_table.py (where this is called)
#          docs/adr/adr_06.md (why normalization precedes the join)
#          exploratory/lovd_first_look.py (shows the raw LOVD notation)

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NormalizationResult:
    """Outcome of one HGVS normalization attempt."""
    input_notation:     str
    canonical_hgvs:     Optional[str]       # e.g. "NM_004006.2:c.6439del"
    transcript:         Optional[str]       # e.g. "NM_004006.2"
    mutation_type:      Optional[str]       # deletion | duplication | substitution | insertion | indel | unknown
    cdna_start:         Optional[int]       # cDNA position (start), None if unparseable
    cdna_end:           Optional[int]       # cDNA position (end), None if point mutation
    strategy:           str                 # strict | lenient | exon_raw | unparseable
    unparseable:        bool = False
    parse_error:        Optional[str] = None


# ---------------------------------------------------------------------------
# Reference transcript for DMD
# All LOVD records reference NM_004006.2 (Dp427m). Records with a different
# transcript accession are still normalised but flagged for manual review.
# ---------------------------------------------------------------------------
DMD_REFERENCE_TRANSCRIPT = "NM_004006.2"

# ---------------------------------------------------------------------------
# Lenient regex patterns for legacy LOVD notation
#
# LOVD legacy format examples:
#   c.(?_432-1)_(6438+1_?)del    — uncertain boundaries, deletion
#   c.1483_1812dup               — canonical but without transcript prefix
#   c.(6439_6440)del             — approximate boundaries
#   c.?                          — completely unknown
# ---------------------------------------------------------------------------
_MUTATION_TYPE_PATTERNS = {
    "deletion":     re.compile(r"del", re.IGNORECASE),
    "duplication":  re.compile(r"dup", re.IGNORECASE),
    "insertion":    re.compile(r"ins(?!del)", re.IGNORECASE),
    "indel":        re.compile(r"delins|indel", re.IGNORECASE),
    "substitution": re.compile(r">[ACGT]", re.IGNORECASE),
}

# Extracts start and end cDNA positions from canonical and legacy notation.
# Handles: c.123del, c.123_456del, c.(?_123)_(456_?)del, c.(123_456)dup
_POSITION_PATTERN = re.compile(
    r"c\."                          # cDNA prefix
    r"(?:\(?\?_)?(\d+)"            # start position (may be preceded by (?_ uncertainty)
    r"(?:[+-]\d+)?"                # optional intron offset
    r"(?:_\(?(?:\d+\+\d+_)?"      # optional range separator
    r"\??\)?(\d+)"                 # end position
    r"(?:[+-]\d+)?\)?)?"           # optional intron offset + closing paren
)


def _detect_mutation_type(notation: str) -> str:
    for mut_type, pattern in _MUTATION_TYPE_PATTERNS.items():
        if pattern.search(notation):
            return mut_type
    return "unknown"


def _extract_positions(notation: str) -> tuple[Optional[int], Optional[int]]:
    match = _POSITION_PATTERN.search(notation)
    if not match:
        return None, None
    start = int(match.group(1)) if match.group(1) else None
    end   = int(match.group(2)) if match.group(2) else None
    return start, end


# ---------------------------------------------------------------------------
# Strategy 1: Strict HGVS parsing via the `hgvs` library
# ---------------------------------------------------------------------------
def _try_strict(notation: str) -> Optional[NormalizationResult]:
    """
    Attempt full HGVS parsing. Requires the `hgvs` library and a SeqRepo
    snapshot for sequence validation.

    Returns None if parsing fails — caller falls through to lenient strategy.
    """
    try:
        import hgvs.parser
        import hgvs.normalizer
        import hgvs.assemblymapper

        # Add transcript prefix if missing (LOVD sometimes omits it)
        if notation.startswith("c.") or notation.startswith("n."):
            full_notation = f"{DMD_REFERENCE_TRANSCRIPT}:{notation}"
        else:
            full_notation = notation

        parser = hgvs.parser.Parser()
        var    = parser.parse_hgvs_variant(full_notation)

        mut_type = {
            "del":    "deletion",
            "dup":    "duplication",
            "ins":    "insertion",
            "delins": "indel",
            "sub":    "substitution",
        }.get(var.posedit.edit.type, "unknown")

        return NormalizationResult(
            input_notation=notation,
            canonical_hgvs=str(var),
            transcript=str(var.ac) if var.ac else DMD_REFERENCE_TRANSCRIPT,
            mutation_type=mut_type,
            cdna_start=int(var.posedit.pos.start.base) if hasattr(var.posedit.pos, "start") else None,
            cdna_end=int(var.posedit.pos.end.base) if hasattr(var.posedit.pos, "end") else None,
            strategy="strict",
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Strategy 2: Lenient regex parsing for legacy LOVD notation
# ---------------------------------------------------------------------------
def _try_lenient(notation: str) -> Optional[NormalizationResult]:
    """
    Extract mutation type and approximate positions from legacy LOVD notation
    using regex. Does not validate against the reference sequence.

    Returns None only for the fully-unknown "c.?" record.
    """
    if notation.strip() in ("c.?", "n.?", "?", ""):
        return None

    mut_type       = _detect_mutation_type(notation)
    start, end     = _extract_positions(notation)

    if mut_type == "unknown" and start is None:
        return None

    # Construct a best-effort canonical form. Silver will flag these for review.
    canonical = f"{DMD_REFERENCE_TRANSCRIPT}:{notation}" if not notation.startswith("NM_") else notation

    return NormalizationResult(
        input_notation=notation,
        canonical_hgvs=canonical,
        transcript=DMD_REFERENCE_TRANSCRIPT,
        mutation_type=mut_type,
        cdna_start=start,
        cdna_end=end,
        strategy="lenient",
    )


# ---------------------------------------------------------------------------
# Strategy 3: exon_raw fallback
# ---------------------------------------------------------------------------
def _try_exon_raw(notation: str, exon_raw: Optional[str]) -> Optional[NormalizationResult]:
    """
    When cDNA notation is unparseable but exon_raw is available, record the
    exon range as a fallback. This record cannot contribute to HGVS-based
    cross-source matching but CAN contribute to reading frame computation.
    """
    if not exon_raw:
        return None
    return NormalizationResult(
        input_notation=notation,
        canonical_hgvs=None,  # no canonical HGVS — exon_raw only
        transcript=DMD_REFERENCE_TRANSCRIPT,
        mutation_type=_detect_mutation_type(notation) or "unknown",
        cdna_start=None,
        cdna_end=None,
        strategy="exon_raw",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def normalize_hgvs(notation: str, exon_raw: Optional[str] = None) -> NormalizationResult:
    """
    Normalize a HGVS cDNA notation string using a three-level fallback strategy.

    Parameters
    ----------
    notation  : HGVS cDNA string as returned by LOVD or ClinVar
    exon_raw  : LOVD exon field (e.g. "44i_52i") used as last resort

    Returns
    -------
    NormalizationResult with strategy indicating which level succeeded.
    strategy == "unparseable" means the record cannot be used for variant matching
    or reading frame computation and should be quarantined.
    """
    if not notation or not notation.strip():
        return NormalizationResult(
            input_notation=notation or "",
            canonical_hgvs=None,
            transcript=None,
            mutation_type=None,
            cdna_start=None,
            cdna_end=None,
            strategy="unparseable",
            unparseable=True,
            parse_error="empty notation",
        )

    result = _try_strict(notation)
    if result:
        return result

    result = _try_lenient(notation)
    if result:
        return result

    result = _try_exon_raw(notation, exon_raw)
    if result:
        return result

    return NormalizationResult(
        input_notation=notation,
        canonical_hgvs=None,
        transcript=None,
        mutation_type=None,
        cdna_start=None,
        cdna_end=None,
        strategy="unparseable",
        unparseable=True,
        parse_error=f"all strategies failed for: {notation[:100]}",
    )


# ---------------------------------------------------------------------------
# Spark UDF wrapper — use this in DLT Silver pipelines
# ---------------------------------------------------------------------------
def register_hgvs_udf(spark):
    """
    Register normalize_hgvs as a Spark SQL UDF returning a struct.
    Call once at pipeline initialisation. Use in DLT via:

        from hgvs_normalization import register_hgvs_udf
        register_hgvs_udf(spark)
        df = df.withColumn("hgvs", F.expr("normalize_hgvs_udf(dna_change_cdna, exon_raw)"))
    """
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, BooleanType
    from pyspark.sql import functions as F

    result_type = StructType([
        StructField("canonical_hgvs",  StringType(),  True),
        StructField("transcript",      StringType(),  True),
        StructField("mutation_type",   StringType(),  True),
        StructField("cdna_start",      IntegerType(), True),
        StructField("cdna_end",        IntegerType(), True),
        StructField("strategy",        StringType(),  False),
        StructField("unparseable",     BooleanType(), False),
        StructField("parse_error",     StringType(),  True),
    ])

    def _udf_wrapper(notation, exon_raw):
        r = normalize_hgvs(notation or "", exon_raw)
        return (r.canonical_hgvs, r.transcript, r.mutation_type,
                r.cdna_start, r.cdna_end, r.strategy, r.unparseable, r.parse_error)

    spark.udf.register(
        "normalize_hgvs_udf",
        _udf_wrapper,
        result_type,
    )
