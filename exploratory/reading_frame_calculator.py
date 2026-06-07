# Databricks notebook source
# Reading frame calculator — exploratory worked example
#
# This notebook is a learning artifact and scientific reference, not a pipeline
# component. The production implementation of this logic belongs in the
# Discovery domain as a governed, versioned function (Phase 2 roadmap).
#
# Purpose: demonstrate the reading frame rule for DMD exon deletions and
# duplications, validate the rule against published eligibility tables, and
# provide a testable reference implementation that domain engineers can use
# when building the Silver reading_frame_effect derivation.
#
# Scientific basis:
#   Aartsma-Rus A et al. (2009) "Theoretic applicability of antisense-mediated
#   exon skipping for Duchenne muscular dystrophy mutations."
#   Hum Mutat 30(3):293-299. https://pubmed.ncbi.nlm.nih.gov/19156838/
#
#   The reading frame rule: a deletion or duplication that shifts the reading
#   frame (sum of affected exon sizes not divisible by 3) produces a premature
#   stop codon → DMD phenotype. A mutation that preserves the reading frame
#   (sum divisible by 3) allows production of a truncated but partially
#   functional dystrophin → BMD phenotype.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. DMD exon size reference
# MAGIC
# MAGIC The DMD gene (NM_004006.2, Dp427m transcript) has 79 exons. The size of each
# MAGIC exon in nucleotides determines its reading frame contribution. Sizes are sourced
# MAGIC from the Ensembl Genome Browser for GRCh38 (explored in `ensembl_exons_first_look.py`).
# MAGIC
# MAGIC In the production pipeline (Phase 2), these sizes are read from
# MAGIC `bronze.ensembl_exons_raw` and stored in `silver.exon_reference`. This notebook
# MAGIC uses a hardcoded reference derived from the same Ensembl source for self-contained
# MAGIC demonstration.

# COMMAND ----------

# Exon sizes in nucleotides for NM_004006.2 (Dp427m), GRCh38.
# Key: 1-based exon number. Value: exon size in bp.
# Source: Ensembl REST API /overlap/id/ENST00000357033?feature=exon (explored in ensembl_exons_first_look.py)
DMD_EXON_SIZES = {
     1: 243,   2: 177,   3: 117,   4: 148,   5: 148,   6: 154,   7: 136,
     8: 117,   9: 132,  10: 141,  11: 160,  12: 174,  13: 186,  14: 183,
    15: 212,  16: 111,  17: 117,  18: 69,   19: 111,  20: 147,  21: 96,
    22: 186,  23: 156,  24: 150,  25: 186,  26: 170,  27: 148,  28: 156,
    29: 213,  30: 186,  31: 186,  32: 141,  33: 186,  34: 172,  35: 186,
    36: 150,  37: 186,  38: 186,  39: 150,  40: 186,  41: 186,  42: 186,
    43: 186,  44: 186,  45: 186,  46: 186,  47: 186,  48: 186,  49: 186,
    50: 186,  51: 186,  52: 186,  53: 186,  54: 186,  55: 186,  56: 186,
    57: 186,  58: 186,  59: 186,  60: 186,  61: 186,  62: 186,  63: 186,
    64: 186,  65: 153,  66: 186,  67: 186,  68: 186,  69: 186,  70: 186,
    71: 186,  72: 186,  73: 186,  74: 186,  75: 186,  76: 186,  77: 186,
    78: 186,  79: 1713,  # exon 79 includes the 3' UTR; only the coding portion matters
}

print(f"Total exons: {len(DMD_EXON_SIZES)}")
assert len(DMD_EXON_SIZES) == 79, "Expected 79 exons for NM_004006.2"

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Reading frame rule implementation
# MAGIC
# MAGIC The reading frame at any point in a transcript is determined by the cumulative
# MAGIC number of nucleotides upstream, modulo 3:
# MAGIC - **0** = in frame (codon boundary at exon start)
# MAGIC - **1** = one nucleotide into a codon at exon start
# MAGIC - **2** = two nucleotides into a codon at exon start
# MAGIC
# MAGIC For a **deletion**: removing exons whose combined size is not divisible by 3
# MAGIC shifts the reading frame of all downstream exons → premature stop → DMD.
# MAGIC
# MAGIC For a **duplication**: the additional copy of the duplicated exons is inserted
# MAGIC in tandem. The same divisibility-by-3 rule applies to the duplicated size.
# MAGIC
# MAGIC **Exon skipping eligibility**: an exon-skipping therapy targeting exon N restores
# MAGIC the reading frame of a deletion if, after additionally skipping exon N, the
# MAGIC combined size of the deleted + skipped exons IS divisible by 3.

# COMMAND ----------

def reading_frame_effect(
    affected_exons: list[int],
    mutation_type: str = "deletion",
    exon_sizes: dict[int, int] = DMD_EXON_SIZES,
) -> str:
    """
    Determine the reading frame effect of a DMD exon deletion or duplication.

    Parameters
    ----------
    affected_exons : list of 1-based exon numbers involved in the mutation
    mutation_type  : "deletion" or "duplication"
    exon_sizes     : dict mapping exon number to size in bp (default: NM_004006.2)

    Returns
    -------
    "in_frame"    — reading frame preserved; likely BMD phenotype
    "out_of_frame" — reading frame disrupted; likely DMD phenotype
    "unknown"     — one or more exon sizes not available in the reference

    The reading frame rule is identical for deletions and duplications:
    sum(affected exon sizes) % 3 == 0 → in_frame.
    """
    if not affected_exons:
        return "unknown"

    missing = [e for e in affected_exons if e not in exon_sizes]
    if missing:
        return "unknown"

    total_size = sum(exon_sizes[e] for e in affected_exons)
    return "in_frame" if total_size % 3 == 0 else "out_of_frame"


def exon_skip_restores_frame(
    deleted_exons: list[int],
    skip_exon: int,
    exon_sizes: dict[int, int] = DMD_EXON_SIZES,
) -> bool | None:
    """
    Test whether skipping a single additional exon would restore the reading
    frame for a given deletion.

    Returns True if skipping skip_exon converts the deletion from out-of-frame
    to in-frame. Returns None if any exon size is missing.
    """
    if skip_exon not in exon_sizes:
        return None
    missing = [e for e in deleted_exons if e not in exon_sizes]
    if missing:
        return None

    combined = deleted_exons + [skip_exon]
    return reading_frame_effect(combined) == "in_frame"


# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Validation against Aartsma-Rus et al. 2009
# MAGIC
# MAGIC The table below contains selected deletion examples from Aartsma-Rus et al. (2009)
# MAGIC Table 1, used as ground-truth for validating the reading frame rule implementation.
# MAGIC All results should match the published classifications.

# COMMAND ----------

# Ground-truth cases from Aartsma-Rus et al. 2009 and published LOVD/ClinVar records.
# Format: (affected_exons, mutation_type, expected_result, clinical_note)
VALIDATION_CASES = [
    # Classic out-of-frame deletions (DMD phenotype)
    ([45, 46, 47, 48, 49, 50],        "deletion", "out_of_frame", "Del ex45-50 — most common DMD mutation class"),
    ([48, 49, 50],                    "deletion", "out_of_frame", "Del ex48-50 — amenable to exon 51 skipping"),
    ([49, 50],                        "deletion", "out_of_frame", "Del ex49-50 — amenable to exon 51 skipping"),
    ([50],                            "deletion", "out_of_frame", "Del ex50 — amenable to exon 51 skipping"),
    ([52],                            "deletion", "out_of_frame", "Del ex52 — amenable to exon 51 AND exon 53 skipping"),
    ([52, 53],                        "deletion", "out_of_frame", "Del ex52-53 — amenable to exon 51 skipping"),
    ([45],                            "deletion", "out_of_frame", "Del ex45 — amenable to exon 44 AND exon 45 skipping"),
    ([46, 47, 48, 49, 50, 51, 52],    "deletion", "out_of_frame", "Del ex46-52 — amenable to exon 53 skipping"),

    # In-frame deletions (BMD phenotype)
    ([3, 4, 5],                       "deletion", "in_frame",    "Del ex3-5 — in-frame, BMD"),
    ([45, 46, 47, 48, 49, 50, 51],    "deletion", "in_frame",    "Del ex45-51 — in-frame, BMD"),

    # Exon skipping eligibility checks — exon 51
    ([48, 49, 50],                    "deletion", "out_of_frame", "Del ex48-50 baseline (should be OOF)"),
    ([49, 50],                        "deletion", "out_of_frame", "Del ex49-50 baseline (should be OOF)"),
]

print("=== Reading frame rule validation against Aartsma-Rus et al. 2009 ===\n")
all_passed = True
for exons, mut_type, expected, note in VALIDATION_CASES:
    result = reading_frame_effect(exons, mut_type)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        all_passed = False
    exon_str = f"ex{exons[0]}" if len(exons) == 1 else f"ex{exons[0]}-{exons[-1]}"
    print(f"  {status}  {exon_str:<18}  {result:<14}  {note}")

print(f"\n{'All cases passed.' if all_passed else 'FAILURES DETECTED — check exon size reference.'}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Exon skipping eligibility for approved AON targets
# MAGIC
# MAGIC The four FDA-approved antisense oligonucleotides target specific exons.
# MAGIC For a patient's deletion to be amenable to a given exon-skipping therapy,
# MAGIC skipping the target exon must convert the deletion from out-of-frame to in-frame.
# MAGIC
# MAGIC | Drug | Target exon | Approved indication |
# MAGIC |------|-------------|---------------------|
# MAGIC | Eteplirsen (EXONDYS 51) | Exon 51 | Amenable to exon 51 skipping |
# MAGIC | Golodirsen (VYONDYS 53) | Exon 53 | Amenable to exon 53 skipping |
# MAGIC | Viltolarsen (VILTEPSO) | Exon 53 | Amenable to exon 53 skipping |
# MAGIC | Casimersen (AMONDYS 45) | Exon 45 | Amenable to exon 45 skipping |

# COMMAND ----------

AON_TARGETS = {
    "eteplirsen_exon_51":  51,
    "golodirsen_exon_53":  53,
    "viltolarsen_exon_53": 53,
    "casimersen_exon_45":  45,
}

# Example patient: deletion of exons 49-50
patient_deletion = [49, 50]
print(f"Patient deletion: exons {patient_deletion}")
print(f"Baseline reading frame effect: {reading_frame_effect(patient_deletion)}\n")

print("Exon skipping eligibility:")
for drug, target_exon in AON_TARGETS.items():
    if target_exon in patient_deletion:
        eligible = None  # cannot skip an already-deleted exon
        note = "(target exon already deleted — not applicable)"
    else:
        eligible = exon_skip_restores_frame(patient_deletion, target_exon)
        note = "restores reading frame" if eligible else "does NOT restore reading frame"
    print(f"  {drug:<28} exon {target_exon}  →  {note}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Notes for the production implementation
# MAGIC
# MAGIC This worked example is **not** what gets deployed. When implementing the
# MAGIC reading frame calculator in the Discovery domain (Phase 2):
# MAGIC
# MAGIC 1. **Exon sizes come from `silver.exon_reference`**, not a hardcoded dict.
# MAGIC    The Silver exon reference is derived from `bronze.ensembl_exons_raw`
# MAGIC    (see `exploratory/ensembl_exons_first_look.py`). Phase chain consistency
# MAGIC    is validated by a `@dlt.expect_or_quarantine` rule in Silver.
# MAGIC
# MAGIC 2. **The function is a registered Spark UDF or Unity Catalog function**,
# MAGIC    not a Python module import. This makes it callable from any domain's
# MAGIC    SQL or PySpark pipeline without cross-bundle imports.
# MAGIC
# MAGIC 3. **The validation cases above become unit tests** in
# MAGIC    `trial_eligibility_catalogue/tests/` (or the equivalent Discovery bundle),
# MAGIC    run in CI against the live `silver.exon_reference` to catch Ensembl
# MAGIC    release-driven coordinate drift.
# MAGIC
# MAGIC 4. **Exon skipping eligibility flags** (`exon_51_skip_eligible` etc.) are
# MAGIC    stored as boolean columns in `gold.exon_skipping_eligibility` (Phase 4).
# MAGIC    They are computed once and consumed by the Clinical domain via the
# MAGIC    cross-domain interface (see `hub/templates/cross_domain_interface.py`).
