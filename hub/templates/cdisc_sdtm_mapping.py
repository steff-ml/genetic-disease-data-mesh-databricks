# Template: CDISC SDTM v3.3 mapping
#
# WHEN TO USE THIS TEMPLATE (vs OMOP CDM)
# ========================================
# Use CDISC SDTM when:
#   1. Producing output for regulatory submission (FDA, EMA, PMDA)
#   2. Receiving sponsor-provided clinical trial data that arrived in SDTM format
#   3. Building the Phase 6 marketplace data package for pharma partners
#
# Use OMOP CDM (see omop_cdm_mapping.py) when:
#   1. Building analytical Gold tables consumed by EHR systems or research queries
#   2. Supporting patient cohort analysis, RWE, or trial eligibility matching
#   3. Any non-submission analytical use case
#
# The two standards are complementary, not alternatives — OMOP for analysis,
# SDTM for submission. Most tables in this project should use OMOP; SDTM is
# only needed for Phase 6 outputs or when a pharma sponsor delivers raw data
# in SDTM format.
#
# SDTM DOMAINS IMPLEMENTED HERE
# ==============================
# Three domains are most relevant for this DMD project:
#
#   GF  — Genomics Findings (CDISC Genomics v1.0)
#           One row per variant finding per subject. This is the primary domain
#           for LOVD and ClinVar variant data when submitted to a sponsor.
#           NOTE: GF is a provisional CDISC domain. Use the sponsor's define.xml
#           template or the CDISC Genomics Therapeutic Area (TA) user guide.
#
#   DM  — Demographics
#           One row per subject. Required in every SDTM submission.
#
#   DS  — Disposition (trial enrollment, discontinuation)
#           One row per disposition event per subject.
#
# STANDARD REFERENCE
# ==================
# CDISC SDTM Implementation Guide v3.3 (SDTMIG v3.3)
# CDISC Genomics TA User Guide v1.0
# Download from: https://www.cdisc.org/standards/foundational/sdtm
# (account required — store PDFs in Teams or SharePoint, not in this repo)
#
# CONTROLLED TERMINOLOGY (CT)
# ============================
# SDTM requires CDISC CT for coded fields (RACE, SEX, ETHNIC, etc.).
# Do not hard-code CT values — look them up via the CDISC CT browser or the
# NCI Thesaurus. Controlled terms change with each CT release; document which
# CT release date was used in your submission define.xml.
#
# CT browser: https://www.cdisc.org/standards/terminology
#
# Related: hub/templates/omop_cdm_mapping.py (for analytical use cases)
#          hub/templates/ich_e6_gcp_checklist.md (GCP requirements for submissions)
#          hub/templates/audit_trail_config.py (21 CFR Part 11 trail required)

from dataclasses import dataclass, field
from typing import Optional
from datetime import date


# ---------------------------------------------------------------------------
# SDTM datetime format
# ISO 8601 is required: --STDT and --ENDT fields use "YYYY-MM-DD" or
# "YYYY-MM-DDThh:mm:ss" format. Partial dates are allowed ("YYYY-MM" or "YYYY").
# ---------------------------------------------------------------------------
def sdtm_date(d: Optional[date]) -> str:
    if d is None:
        return ""
    return d.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# GF domain — Genomics Findings
#
# One row per genomic variant finding per subject.
# --TESTCD / --TEST describe what was measured; --ORRES / --STRESC hold the result.
#
# Column names follow SDTM variable naming conventions:
#   STUDYID   — study identifier
#   DOMAIN    — always "GF" for this domain
#   USUBJID   — unique subject identifier (sponsor prefix + site + subject number)
#   GFnn      — sequential finding number within subject
# ---------------------------------------------------------------------------
@dataclass
class SdtmGfRow:
    """SDTM GF (Genomics Findings) domain row."""
    STUDYID:      str                        # Sponsor study ID e.g. "DMD-2025-01"
    DOMAIN:       str = "GF"
    USUBJID:      str = ""                   # Unique subject ID e.g. "DMD-2025-01-001-001"
    GFSEQ:        int = 1                    # Sequence number within subject
    GFTESTCD:     str = ""                   # Short test code, e.g. "GENVARCH" (genomic variant characterization)
    GFTEST:       str = ""                   # Long test name, e.g. "Genomic Variant Characterization"
    GFCAT:        str = ""                   # Category, e.g. "MUTATION FINDING"
    GFORRES:      str = ""                   # Original result (HGVS cDNA notation)
    GFSTRESC:     str = ""                   # Standardized result (canonical HGVS)
    GFSTRESN:     Optional[float] = None     # Numeric result (not used for variants)
    GFSTRESU:     str = ""                   # Result units (empty for variants)
    GFSTAT:       str = ""                   # Status if not done: "NOT DONE"
    GFREASND:     str = ""                   # Reason not done
    GFNAM:        str = ""                   # Lab/vendor name, e.g. "LOVD", "ClinVar"
    GFSPEC:       str = "BLOOD"              # Specimen type (CDISC CT: BLOOD, TISSUE, etc.)
    GFMETHOD:     str = "NGS"                # Method (CDISC CT: NGS, SANGER, etc.)
    VISITNUM:     Optional[float] = None     # Visit number
    VISIT:        str = ""                   # Visit label
    GFDTC:        str = ""                   # Date/time of result (ISO 8601)
    GFDY:         Optional[int] = None       # Study day of result

    # --- Extension fields for this project (not in base SDTM GF) ---
    # Capture these as supplemental qualifiers (SUPPGF) in submission packages
    VARIANT_VRS_ID:   str = ""              # GA4GH VRS ID for cross-system linkage
    READING_FRAME:    str = ""              # "in_frame" | "out_of_frame" | "unknown"
    EXON_AFFECTED:    str = ""              # Affected exon range e.g. "45-52"
    CONFLICT_FLAG:    str = ""              # "conflict" | "no_conflict"
    SOURCE_DB:        str = ""              # "LOVD" | "ClinVar" | "merged"


@dataclass
class SdtmDmRow:
    """SDTM DM (Demographics) domain row. One per subject."""
    STUDYID:   str
    DOMAIN:    str = "DM"
    USUBJID:   str = ""
    SUBJID:    str = ""         # Subject identifier within site
    SITEID:    str = ""         # Study site ID
    INVID:     str = ""         # Investigator ID
    RFSTDTC:   str = ""         # Reference start date (first dose / enrollment date, ISO 8601)
    RFENDTC:   str = ""         # Reference end date
    DTHDTC:    str = ""         # Date/time of death (if applicable)
    DTHFL:     str = ""         # Death flag: "Y" or ""
    COUNTRY:   str = ""         # ISO 3166-1 alpha-3 e.g. "BEL", "NLD"
    ETHNIC:    str = ""         # CDISC CT: "NOT HISPANIC OR LATINO" etc.
    RACE:      str = ""         # CDISC CT: "WHITE", "ASIAN" etc.
    ARACE:     str = ""         # Additional race if multiple
    SEX:       str = ""         # CDISC CT: "M" | "F" | "U" | "UNDIFFERENTIATED"
    BRTHDTC:   str = ""         # Birthdate (partial date allowed for de-identification)
    AGE:       Optional[float] = None   # Age at reference start
    AGEU:      str = "YEARS"    # Age units: CDISC CT


@dataclass
class SdtmDsRow:
    """SDTM DS (Disposition) domain row. One per disposition event per subject."""
    STUDYID:   str
    DOMAIN:    str = "DS"
    USUBJID:   str = ""
    DSSEQ:     int = 1          # Sequence within subject
    DSSPID:    str = ""         # Sponsor-defined event ID
    DSTERM:    str = ""         # Verbatim term for event e.g. "COMPLETED", "SCREEN FAILURE"
    DSDECOD:   str = ""         # CDISC CT decoded term
    DSCAT:     str = ""         # Category: "PROTOCOL MILESTONE" | "DISPOSITION EVENT"
    DSSCAT:    str = ""         # Subcategory
    EPOCH:     str = ""         # CDISC CT epoch: "SCREENING" | "TREATMENT" | "FOLLOW-UP"
    DSDTC:     str = ""         # Date of event (ISO 8601)
    DSDY:      Optional[int] = None  # Study day


# ---------------------------------------------------------------------------
# Mapping functions — adapt from this project's Silver tables
# ---------------------------------------------------------------------------

def variant_to_sdtm_gf(
    study_id:      str,
    usubjid:       str,
    seq:           int,
    canonical_hgvs: str,
    vrs_id:        Optional[str],
    mutation_type: Optional[str],
    exon_range:    Optional[str],
    reading_frame: Optional[str],
    conflict_flag: Optional[str],
    source_system: str,
    result_date:   Optional[date] = None,
) -> SdtmGfRow:
    """
    Map a single variant record from the Silver `dmd_variants` table to an
    SDTM GF domain row. Called once per variant per subject in the submission
    package preparation step.

    Parameters
    ----------
    study_id       : sponsor study ID
    usubjid        : unique subject identifier
    seq            : sequence number (increment per subject)
    canonical_hgvs : normalised HGVS cDNA string (from hgvs_normalization)
    vrs_id         : GA4GH VRS ID (from ga4gh_vrs_normalization), may be None
    mutation_type  : deletion | duplication | substitution | insertion | indel
    exon_range     : affected exon range, e.g. "45-52"
    reading_frame  : in_frame | out_of_frame | unknown
    conflict_flag  : conflict | no_conflict (from ADR-06)
    source_system  : LOVD | ClinVar | merged
    result_date    : date the finding was recorded
    """
    return SdtmGfRow(
        STUDYID=study_id,
        USUBJID=usubjid,
        GFSEQ=seq,
        GFTESTCD="GENVARCH",
        GFTEST="Genomic Variant Characterization",
        GFCAT="MUTATION FINDING",
        GFORRES=canonical_hgvs,
        GFSTRESC=canonical_hgvs,
        GFNAM=source_system,
        GFSPEC="BLOOD",
        GFMETHOD="NGS",
        GFDTC=sdtm_date(result_date),
        VARIANT_VRS_ID=vrs_id or "",
        READING_FRAME=reading_frame or "",
        EXON_AFFECTED=exon_range or "",
        CONFLICT_FLAG=conflict_flag or "",
        SOURCE_DB=source_system,
    )


# ---------------------------------------------------------------------------
# Spark-based batch export to SDTM format
# ---------------------------------------------------------------------------

def export_sdtm_gf_dataset(spark, study_id: str, silver_table: str, output_path: str) -> None:
    """
    Export the Silver variant table to an SDTM GF dataset (SAS Transport v5 or
    parquet — confirm file format with the sponsor's submission specifications).

    In most cases, the sponsor will require SAS XPT v5 format. Use the
    `xport` Python package or SAS Viya to convert the parquet output.

    Parameters
    ----------
    spark        : Spark session
    study_id     : sponsor study ID (injected into every row)
    silver_table : fully-qualified Silver table name (catalog.schema.table)
    output_path  : Unity Catalog Volume path for output files
    """
    from pyspark.sql import functions as F

    df = spark.table(silver_table)

    # Required GF columns; add supplemental qualifiers (SUPPGF) for extension fields
    sdtm_gf = df.select(
        F.lit(study_id).alias("STUDYID"),
        F.lit("GF").alias("DOMAIN"),
        # USUBJID must be derived from the patient_id join — placeholder shown here
        F.col("source_id").alias("USUBJID"),
        F.monotonically_increasing_id().cast("int").alias("GFSEQ"),
        F.lit("GENVARCH").alias("GFTESTCD"),
        F.lit("Genomic Variant Characterization").alias("GFTEST"),
        F.lit("MUTATION FINDING").alias("GFCAT"),
        F.col("canonical_hgvs").alias("GFORRES"),
        F.col("canonical_hgvs").alias("GFSTRESC"),
        F.col("source_system").alias("GFNAM"),
        F.lit("BLOOD").alias("GFSPEC"),
        F.lit("NGS").alias("GFMETHOD"),
        F.date_format(F.col("ingestion_timestamp"), "yyyy-MM-dd").alias("GFDTC"),
    )

    # Write as parquet; convert to SAS XPT as a separate post-processing step
    sdtm_gf.write.mode("overwrite").parquet(f"{output_path}/gf.parquet")
    print(f"SDTM GF dataset written to {output_path}/gf.parquet")
    print(f"Row count: {sdtm_gf.count()}")
    print("Next: convert to SAS XPT v5 using the `xport` package or SAS Viya.")
    print("Provide define.xml with GF variable metadata before submission.")
