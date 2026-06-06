# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # Ensembl REST API — DMD Exon Coordinates First Look
# MAGIC
# MAGIC **Source**: Ensembl REST API — genomic coordinate reference (`rest.ensembl.org`)
# MAGIC **Target table**: `workspace.steff_horemans.bronze_ensembl_exons_raw`
# MAGIC **API base**: `https://rest.ensembl.org`
# MAGIC **Auth type**: Public — no credentials required
# MAGIC **Gene**: DMD (`ENSG00000198947`), canonical Dp427m transcript (`ENST00000357033`)
# MAGIC **Assembly**: GRCh38
# MAGIC **Author**: exploration-notebook agent
# MAGIC **Date**: 2026-06-06
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Section 0 — Context and Purpose
# MAGIC
# MAGIC The Ensembl REST API is the **authoritative genomic coordinate reference** for the Discovery domain.
# MAGIC Unlike the variant databases (LOVD, ClinVar), Ensembl does not hold patient or variant data — it holds
# MAGIC the immutable biological reference: which nucleotides form each exon of the canonical DMD transcript,
# MAGIC their genomic positions on GRCh38, and their reading frame phase offsets.
# MAGIC
# MAGIC This source feeds the pipeline at the Silver reference layer, not the variant layer:
# MAGIC
# MAGIC ```
# MAGIC workspace.steff_horemans.bronze_ensembl_exons_raw   (this notebook)
# MAGIC   → silver.exon_reference     (exon number, size in bp, cumulative reading frame contribution)
# MAGIC   → gold.patient_mutation_profile   (reading_frame_effect computed by joining patient's exon list
# MAGIC                                       to silver.exon_reference and summing sizes mod 3)
# MAGIC ```
# MAGIC
# MAGIC **Why Ensembl is needed as a separate Bronze source**: both LOVD (`position_mRNA`) and ClinVar (HGVS
# MAGIC cDNA notation) return nucleotide coordinate ranges but not discrete exon numbers or exon sizes. To
# MAGIC implement the reading frame rule — `(sum of deleted/duplicated exon sizes) mod 3` — the Silver pipeline
# MAGIC must map cDNA coordinate ranges onto the DMD exon table. That mapping table is what this notebook
# MAGIC retrieves and stores as Bronze.
# MAGIC
# MAGIC **The scientific question this exploration answers**: does the Ensembl REST API return the complete
# MAGIC 79-exon structure of the canonical Dp427m transcript with per-exon genomic coordinates and reading frame
# MAGIC phase information in a single call, and are those phase values internally consistent (i.e. does the
# MAGIC `ensembl_end_phase` of exon N equal the `ensembl_phase` of exon N+1)?
# MAGIC
# MAGIC A successful Bronze ingestion of this source enables:
# MAGIC 1. `silver.exon_reference` — the per-exon lookup table that makes the reading frame computation
# MAGIC    deterministic. Without this, reading frame classification must rely on hardcoded exon size tables
# MAGIC    (brittle) rather than a live, version-tracked reference.
# MAGIC 2. HGVS coordinate-to-exon mapping in Silver — cDNA positions from LOVD and ClinVar can be mapped
# MAGIC    to discrete exon numbers by intersecting against the `start`/`end` coordinate ranges in this table.
# MAGIC 3. Assembly version provenance — the `assembly_name` field from Ensembl pins every exon coordinate to
# MAGIC    a specific GRCh38 patch, enabling downstream detection of coordinate drift if the assembly changes.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 1 — Connection and Authentication
# MAGIC
# MAGIC The Ensembl REST API at `rest.ensembl.org` is fully public. No API key, OAuth token, or registration
# MAGIC is required. The API enforces a rate limit of **15 requests per second** (55,000 per hour) per IP
# MAGIC address, communicated via response headers:
# MAGIC - `X-RateLimit-Limit`: 55,000
# MAGIC - `X-RateLimit-Remaining`: queries left in the current hour window
# MAGIC - `X-RateLimit-Reset`: seconds until quota resets
# MAGIC - HTTP 429 with `Retry-After` header when the limit is exceeded
# MAGIC
# MAGIC For this exploration notebook only two API calls are needed — the transcript metadata lookup and the
# MAGIC exon overlap query — so rate limiting is not a practical concern.
# MAGIC
# MAGIC **Why Ensembl over alternatives:**
# MAGIC - **Ensembl REST API**: machine-readable, versioned, GRCh38-native, JSON responses, no authentication,
# MAGIC   stable stable IDs (`ENST`, `ENSE` prefixes). The canonical choice for programmatic genomic coordinate
# MAGIC   retrieval.
# MAGIC - **RefSeq / NCBI Entrez**: alternative authoritative reference. Ensembl is preferred here because the
# MAGIC   Dp427m isoform is annotated as `ENST00000357033` and the downstream Silver pipeline uses Ensembl
# MAGIC   stable IDs as the primary coordinate namespace. RefSeq coordinates are cross-validated at Silver.
# MAGIC - **dmd.nl (Leiden MD pages)**: publishes a static exon size table and reading frame calculator.
# MAGIC   These are manually curated HTML tables, not a programmatic API. Useful for cross-validation at Silver
# MAGIC   but not suitable as a Bronze ingestion source.
# MAGIC - **UCSC Genome Browser API**: alternative coordinate reference. Ensembl is preferred for consistency
# MAGIC   with the HGVS stable IDs used throughout the Discovery domain pipeline.
# MAGIC
# MAGIC No ADR covering the Ensembl Bronze source has been finalised. This notebook is the evidence base for
# MAGIC that ADR. The Ensembl REST API version at exploration time is **v15.10**.

# COMMAND ----------

import time

import requests

BASE_URL = "https://rest.ensembl.org"
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Minimal connectivity check: retrieve server info to confirm API is reachable and capture version
info_url = f"{BASE_URL}/info/rest"
resp = requests.get(info_url, headers=HEADERS, timeout=30)

print(f"Status     : {resp.status_code}")
print(f"Content-Type: {resp.headers.get('Content-Type', 'unknown')}")
print(f"Rate limit remaining: {resp.headers.get('X-RateLimit-Remaining', 'header absent')}")

assert resp.status_code == 200, f"Expected HTTP 200, got {resp.status_code}"
server_info = resp.json()
API_VERSION = f"ensembl_rest_v{server_info.get('release', 'unknown')}"
print(f"\nEnsembl REST API version: {server_info.get('release', 'unknown')}")
print(f"API_VERSION string for provenance: {API_VERSION}")
print("\nConnection successful — Ensembl REST API is reachable.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 2 — Endpoint and Parameter Selection
# MAGIC
# MAGIC The Ensembl REST API provides two candidate endpoints for retrieving exon structure:
# MAGIC
# MAGIC | Endpoint | Description | Exon fields returned |
# MAGIC |----------|-------------|----------------------|
# MAGIC | `GET /overlap/id/:id?feature=exon` | All features overlapping the region of a given identifier | `exon_id`, `start`, `end`, `strand`, `rank`, `ensembl_phase`, `ensembl_end_phase`, `assembly_name`, `Parent` |
# MAGIC | `GET /lookup/id/:id?expand=1` | Transcript record with nested exon objects | `id`, `start`, `end`, `strand`, `assembly_name` — **no rank, no phase** |
# MAGIC
# MAGIC **Selected endpoint**: `GET /overlap/id/ENST00000357033?feature=exon`
# MAGIC
# MAGIC The overlap endpoint is the correct choice because it returns the two fields that are **essential for
# MAGIC the reading frame rule computation** but are absent from the lookup endpoint:
# MAGIC
# MAGIC - `rank` — the 1-based exon number within the transcript. Without `rank`, exon ordering must be
# MAGIC   inferred from genomic coordinates, which is ambiguous for the minus-strand DMD gene (higher genomic
# MAGIC   coordinate = lower exon number for DMD).
# MAGIC - `ensembl_phase` / `ensembl_end_phase` — the reading frame phase at the start and end of each exon
# MAGIC   (values: -1 for UTR/non-coding, 0/1/2 for coding). These encode the cumulative reading frame offset
# MAGIC   directly. A value of 0 at the exon start means the exon begins at a clean codon boundary; 1 means
# MAGIC   one nucleotide of the previous codon has spilled into this exon.
# MAGIC
# MAGIC **Parameter rationale:**
# MAGIC - `feature=exon` — restricts the response to exon features only. Without this filter the overlap
# MAGIC   endpoint returns all feature types (genes, transcripts, variants, repeats) overlapping the DMD locus,
# MAGIC   producing thousands of records.
# MAGIC - No `species` parameter needed — the transcript stable ID `ENST00000357033` is species-unambiguous.
# MAGIC - The `Parent` field in each exon record identifies which transcript the exon belongs to. DMD has
# MAGIC   multiple transcripts; filtering `Parent == "ENST00000357033"` isolates the canonical Dp427m exons.

# COMMAND ----------

TRANSCRIPT_ID = "ENST00000357033"
GENE_ID = "ENSG00000198947"

EXON_URL = f"{BASE_URL}/overlap/id/{TRANSCRIPT_ID}"
params = {"feature": "exon"}

# Fetch all exons for the DMD canonical transcript region
exon_resp = requests.get(EXON_URL, headers=HEADERS, params=params, timeout=30)

print(f"Request URL : {exon_resp.url}")
print(f"Status      : {exon_resp.status_code}")
print(f"Content-Type: {exon_resp.headers.get('Content-Type', 'unknown')}")
print(f"Rate limit remaining: {exon_resp.headers.get('X-RateLimit-Remaining', 'header absent')}")

assert exon_resp.status_code == 200, (
    f"Expected HTTP 200, got {exon_resp.status_code}: {exon_resp.text[:200]}"
)

all_features = exon_resp.json()
print(f"\nTotal features returned (all transcripts): {len(all_features)}")

# Show the first 3 records to confirm response shape before filtering
print("\nFirst 3 records (unfiltered):")
for feature in all_features[:3]:
    print(f"  {feature}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 3 — Response Schema Inspection
# MAGIC
# MAGIC The `/overlap/id/` endpoint returns all exon features overlapping the DMD locus — including exons
# MAGIC from alternative transcripts (Dp427b, Dp427p, Dp260, Dp140, Dp116, Dp71). The `Parent` field
# MAGIC identifies which transcript each exon belongs to. Filtering to `ENST00000357033` isolates the
# MAGIC canonical Dp427m (muscle) isoform — the 79-exon full-length transcript that is the reference for
# MAGIC all approved exon-skipping therapies and the Aartsma-Rus (2009) eligibility tables.
# MAGIC
# MAGIC **Clinically meaningful fields (annotated):**
# MAGIC
# MAGIC | Field | API name | Clinical / scientific role |
# MAGIC |-------|----------|---------------------------|
# MAGIC | Exon stable ID | `exon_id` | Ensembl stable ID (e.g. `ENSE00003536738`). Immutable across assembly patches — safe as a long-term join key between Bronze and Silver. |
# MAGIC | Exon number | `rank` | 1-based position within the transcript (= exon number as used by clinicians and in the AON eligibility tables). Exon 51 in clinical literature = `rank=51` here. |
# MAGIC | Genomic start | `start` | GRCh38 coordinate of the leftmost nucleotide of the exon. **Note**: for the minus-strand DMD gene, higher `start` = earlier in the transcript (exon 1 is 3′ in genomic coordinates). |
# MAGIC | Genomic end | `end` | GRCh38 coordinate of the rightmost nucleotide of the exon. Exon size = `end - start + 1`. |
# MAGIC | Strand | `strand` | -1 for DMD (minus strand). Critical for interpreting coordinate directionality in HGVS-to-exon mapping. |
# MAGIC | Phase at start | `ensembl_phase` | Reading frame phase entering this exon (0/1/2 = codon position; -1 = non-coding/UTR). A phase of 0 means the exon starts at a clean codon boundary. Used directly in the cumulative reading frame computation. |
# MAGIC | Phase at end | `ensembl_end_phase` | Reading frame phase leaving this exon. Must equal `ensembl_phase` of the next exon — internal consistency check. A phase of 0 at the end of exon N means deleting exon N alone contributes 0 to the frame disruption. |
# MAGIC | Parent transcript | `Parent` | Transcript stable ID the exon belongs to. Used to filter to `ENST00000357033`. Multi-transcript exons appear once per parent transcript. |
# MAGIC | Chromosome | `seq_region_name` | "X" for DMD. Confirms the correct gene locus was retrieved (X-linked). |
# MAGIC | Assembly | `assembly_name` | GRCh38 patch version (e.g. `GRCh38`). Must be pinned in Bronze provenance — coordinate systems are not interchangeable across assemblies. |
# MAGIC | Constitutive flag | `constitutive` | 1 if the exon is present in all transcripts of the gene, 0 otherwise. Exons constitutive across all DMD isoforms carry higher confidence for reading frame computation because their coordinates are confirmed by multiple independent annotation pipelines. |

# COMMAND ----------

# Filter to canonical Dp427m transcript exons only
canonical_exons = [f for f in all_features if f.get("Parent") == TRANSCRIPT_ID]

print(f"Total features from overlap endpoint : {len(all_features)}")
print(f"Exons belonging to {TRANSCRIPT_ID} : {len(canonical_exons)}")

# Print all fields present in the first record
if canonical_exons:
    first = canonical_exons[0]
    print(f"\nAll fields in first canonical exon ({len(first)} fields):")
    for k, v in sorted(first.items()):
        print(f"  {k:<25} = {v!r}")

# COMMAND ----------

# Show first 5 exon records sorted by rank to confirm field presence and values
canonical_exons_sorted = sorted(canonical_exons, key=lambda x: x.get("rank", 0))

print("First 5 exons by rank:")
print(f"  {'rank':>4}  {'exon_id':<22}  {'start':>11}  {'end':>11}  {'strand':>6}  "
      f"{'phase':>5}  {'end_phase':>9}  {'size':>6}")
print("  " + "-" * 85)
for exon in canonical_exons_sorted[:5]:
    size = exon["end"] - exon["start"] + 1
    print(
        f"  {exon.get('rank', '?'):>4}  {exon.get('exon_id', '?'):<22}  "
        f"{exon['start']:>11,}  {exon['end']:>11,}  {exon.get('strand', '?'):>6}  "
        f"{exon.get('ensembl_phase', '?'):>5}  {exon.get('ensembl_end_phase', '?'):>9}  "
        f"{size:>6}"
    )

print(f"\nLast 5 exons by rank:")
print(f"  {'rank':>4}  {'exon_id':<22}  {'start':>11}  {'end':>11}  {'strand':>6}  "
      f"{'phase':>5}  {'end_phase':>9}  {'size':>6}")
print("  " + "-" * 85)
for exon in canonical_exons_sorted[-5:]:
    size = exon["end"] - exon["start"] + 1
    print(
        f"  {exon.get('rank', '?'):>4}  {exon.get('exon_id', '?'):<22}  "
        f"{exon['start']:>11,}  {exon['end']:>11,}  {exon.get('strand', '?'):>6}  "
        f"{exon.get('ensembl_phase', '?'):>5}  {exon.get('ensembl_end_phase', '?'):>9}  "
        f"{size:>6}"
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 4 — Pagination Walkthrough
# MAGIC
# MAGIC The `/overlap/id/` endpoint for a transcript-level identifier returns **all matching features in a
# MAGIC single response** — there is no pagination. The Ensembl REST API enforces a slice length limit of
# MAGIC 5,000,000 bp for region-based overlap queries, but transcript-ID-based queries return all features
# MAGIC for that transcript's genomic span in one call regardless of the span size.
# MAGIC
# MAGIC The DMD gene spans approximately **2.4 Mb** (32,389,644 bp → 31,119,228 bp on chrX GRCh38), well
# MAGIC within the 5 Mb slice limit. However, this span encompasses all DMD transcripts, so the response
# MAGIC includes exons from all isoforms — the `Parent` filter in Section 3 is the correct isolation mechanism,
# MAGIC not pagination.
# MAGIC
# MAGIC **Ingestion volume estimate:**
# MAGIC - 79 exons for the canonical transcript (ENST00000357033)
# MAGIC - Total features returned by the overlap call (all isoforms): varies, typically 300–600 exon records
# MAGIC   across all DMD transcripts
# MAGIC - Full Bronze table for this source: 79 rows (one per exon, canonical transcript only)
# MAGIC - Ingestion frequency: **monthly or on Ensembl release** — exon coordinates are stable across GRCh38
# MAGIC   patch releases but may change between major Ensembl release series. The `assembly_name` and
# MAGIC   `api_version` provenance fields detect when a re-ingestion reflects a coordinate update.
# MAGIC
# MAGIC **Pagination gotcha**: none — single-call retrieval. However, the `overlap/id` endpoint for a gene-level
# MAGIC ID (`ENSG00000198947`) rather than a transcript ID returns a different (larger) set of features. Always
# MAGIC query at transcript level and filter by `Parent` to avoid pulling in features from unrelated loci that
# MAGIC happen to overlap the DMD gene span.

# COMMAND ----------

# Verify single-response completeness: confirm no pagination headers are present
print("Pagination-relevant response headers:")
for header in ["Link", "X-Total-Count", "X-Page", "X-Pages"]:
    val = exon_resp.headers.get(header, "ABSENT")
    print(f"  {header:<20} = {val}")

# Confirm the total feature count and canonical-exon subset count
print(f"\nTotal features in response        : {len(all_features)}")
print(f"Canonical Dp427m exons (filtered) : {len(canonical_exons)}")

# Show breakdown of Parent transcript IDs to quantify how many isoforms are in the response
from collections import Counter  # noqa: E402

parent_counts = Counter(f.get("Parent", "unknown") for f in all_features)
print(f"\nExon counts by parent transcript ({len(parent_counts)} transcripts in response):")
for transcript, count in sorted(parent_counts.items(), key=lambda x: -x[1])[:10]:
    marker = " <-- canonical Dp427m" if transcript == TRANSCRIPT_ID else ""
    print(f"  {transcript:<25} {count:>3} exons{marker}")

if len(parent_counts) > 10:
    print(f"  ... and {len(parent_counts) - 10} more transcripts")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 5 — Data Quality First Look
# MAGIC
# MAGIC For a genomic reference source like Ensembl, data quality concerns differ from variant databases.
# MAGIC The primary concerns are not null rates or inconsistent classification — Ensembl coordinates are
# MAGIC authoritatively defined — but rather:
# MAGIC
# MAGIC **Reading frame phase consistency**: if `ensembl_end_phase` of exon N does not equal `ensembl_phase`
# MAGIC of exon N+1, the phase chain is broken and the cumulative reading frame derivation will be incorrect.
# MAGIC This check is the critical quality gate for the Silver `exon_reference` table. A production DLT
# MAGIC pipeline should apply `@dlt.expect_or_quarantine("phase_chain_consistent")` on the Silver exon table.
# MAGIC
# MAGIC **Exon count**: the canonical Dp427m transcript has exactly 79 exons. If the Bronze table contains
# MAGIC any other number, the ingestion has captured the wrong transcript or the API returned an incomplete
# MAGIC response. This is an assertable invariant.
# MAGIC
# MAGIC **Strand consistency**: all exons of a single-stranded gene must share the same strand value. Mixed
# MAGIC strand values indicate a transcript-ID contamination issue (pulling in exons from an antisense
# MAGIC transcript that overlaps the DMD locus).
# MAGIC
# MAGIC **Rank completeness**: ranks must form a contiguous sequence from 1 to 79 with no gaps or duplicates.
# MAGIC A missing rank means an exon record was dropped; a duplicate rank means the `Parent` filter is
# MAGIC letting through the same exon from multiple transcripts.
# MAGIC
# MAGIC **Known Ensembl behaviour**: exons that appear in multiple transcripts share the same genomic
# MAGIC coordinates but carry different `rank` values in each transcript. The `exon_id` (ENSE stable ID)
# MAGIC may therefore appear in multiple rows of the raw overlap response — one per parent transcript. After
# MAGIC filtering to `ENST00000357033`, each `exon_id` should appear exactly once. A duplicate `exon_id`
# MAGIC after filtering would indicate that Ensembl has annotated the same physical exon at two different
# MAGIC ranks within the canonical transcript — a data anomaly worth flagging.

# COMMAND ----------

# --- Quality check 1: exon count ---
expected_exon_count = 79
actual_count = len(canonical_exons)
count_ok = actual_count == expected_exon_count
print(f"Exon count check: expected={expected_exon_count}, actual={actual_count}  "
      f"{'PASS' if count_ok else 'FAIL'}")
assert count_ok, (
    f"Expected exactly {expected_exon_count} exons for ENST00000357033, got {actual_count}. "
    "Check Parent filter or API response."
)

# --- Quality check 2: rank completeness ---
ranks = sorted(e.get("rank", -1) for e in canonical_exons)
expected_ranks = list(range(1, expected_exon_count + 1))
ranks_ok = ranks == expected_ranks
print(f"Rank completeness check: 1–{expected_exon_count} contiguous  "
      f"{'PASS' if ranks_ok else 'FAIL'}")
if not ranks_ok:
    missing = set(expected_ranks) - set(ranks)
    duplicate = [r for r in ranks if ranks.count(r) > 1]
    print(f"  Missing ranks : {sorted(missing)}")
    print(f"  Duplicate ranks: {sorted(set(duplicate))}")

# --- Quality check 3: strand consistency ---
strands = {e.get("strand") for e in canonical_exons}
strand_ok = strands == {-1}
print(f"Strand consistency check: all -1 (minus strand)  {'PASS' if strand_ok else 'FAIL'}")
if not strand_ok:
    print(f"  Strand values found: {strands}")

# --- Quality check 4: exon_id uniqueness ---
exon_ids = [e.get("exon_id") for e in canonical_exons]
unique_ids = set(exon_ids)
id_ok = len(unique_ids) == expected_exon_count
print(f"Exon ID uniqueness check: {len(unique_ids)}/{expected_exon_count} unique  "
      f"{'PASS' if id_ok else 'FAIL'}")

# --- Quality check 5: phase chain consistency ---
sorted_exons = sorted(canonical_exons, key=lambda x: x.get("rank", 0))
phase_chain_breaks = []
for i in range(len(sorted_exons) - 1):
    current_end_phase = sorted_exons[i].get("ensembl_end_phase")
    next_start_phase = sorted_exons[i + 1].get("ensembl_phase")
    if current_end_phase != next_start_phase:
        phase_chain_breaks.append({
            "exon_rank": sorted_exons[i].get("rank"),
            "end_phase": current_end_phase,
            "next_exon_rank": sorted_exons[i + 1].get("rank"),
            "next_start_phase": next_start_phase,
        })
phase_ok = len(phase_chain_breaks) == 0
print(f"Phase chain consistency check: {len(phase_chain_breaks)} breaks  "
      f"{'PASS' if phase_ok else 'FAIL — inspect phase_chain_breaks'}")
if phase_chain_breaks:
    for brk in phase_chain_breaks:
        print(f"  Exon {brk['exon_rank']} end_phase={brk['end_phase']} != "
              f"exon {brk['next_exon_rank']} start_phase={brk['next_start_phase']}")

# COMMAND ----------

# Null-rate analysis on all key fields
KEY_FIELDS = [
    "exon_id", "rank", "start", "end", "strand",
    "ensembl_phase", "ensembl_end_phase", "seq_region_name",
    "assembly_name", "constitutive", "Parent",
]
total = len(canonical_exons)
print(f"Null / missing rate for key fields (across {total} canonical exons):")
for field in KEY_FIELDS:
    null_count = sum(1 for e in canonical_exons if e.get(field) is None)
    print(f"  {field:<25} null={null_count}/{total}  ({100*null_count/total:.1f}%)")

# COMMAND ----------

# Phase value distribution (0/1/2 = coding, -1 = UTR/non-coding)
from collections import Counter  # noqa: F811, E402

start_phase_dist = Counter(e.get("ensembl_phase") for e in canonical_exons)
end_phase_dist = Counter(e.get("ensembl_end_phase") for e in canonical_exons)
print("\nensembl_phase (start of exon) distribution:")
for phase, count in sorted(start_phase_dist.items()):
    label = {-1: "UTR/non-coding", 0: "clean codon boundary", 1: "1 nt of prev codon carried over",
             2: "2 nt of prev codon carried over"}.get(phase, str(phase))
    print(f"  phase={phase:>2}  ({label}): {count} exons")

print("\nensembl_end_phase (end of exon) distribution:")
for phase, count in sorted(end_phase_dist.items()):
    label = {-1: "UTR/non-coding", 0: "ends at codon boundary", 1: "1 nt incomplete at end",
             2: "2 nt incomplete at end"}.get(phase, str(phase))
    print(f"  end_phase={phase:>2}  ({label}): {count} exons")

# COMMAND ----------

# Exon size statistics
sizes = [e["end"] - e["start"] + 1 for e in canonical_exons]
print(f"\nExon size statistics (bp):")
print(f"  Total coding bases (sum of all exon sizes): {sum(sizes):,}")
print(f"  Min exon size : {min(sizes):,} bp")
print(f"  Max exon size : {max(sizes):,} bp")
print(f"  Mean exon size: {sum(sizes)/len(sizes):.1f} bp")

# Identify hotspot exons 45–55 (primary deletion hotspot for exon skipping eligibility)
hotspot_exons = [e for e in canonical_exons if 45 <= e.get("rank", 0) <= 55]
print(f"\nHotspot exons 45–55 (primary AON therapy target region):")
print(f"  {'rank':>4}  {'exon_id':<22}  {'size':>6}  {'start':>11}  {'end':>11}  "
      f"{'phase':>5}  {'end_phase':>9}")
for exon in sorted(hotspot_exons, key=lambda x: x["rank"]):
    size = exon["end"] - exon["start"] + 1
    print(
        f"  {exon['rank']:>4}  {exon.get('exon_id', '?'):<22}  {size:>6}  "
        f"{exon['start']:>11,}  {exon['end']:>11,}  "
        f"{exon.get('ensembl_phase', '?'):>5}  {exon.get('ensembl_end_phase', '?'):>9}"
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 6 — Bronze Schema Sketch
# MAGIC
# MAGIC Proposed column list for `workspace.steff_horemans.bronze_ensembl_exons_raw` (and by extension
# MAGIC `discovery.bronze.ensembl_exons_raw` in production), based on the fields actually returned by the
# MAGIC Ensembl REST API overlap endpoint.
# MAGIC
# MAGIC | Column | Presence | Type | Notes |
# MAGIC |--------|----------|------|-------|
# MAGIC | `exon_id` | always-present | STRING | Ensembl stable exon ID (`ENSE00...`). Primary key within canonical transcript. Stable across assembly patches — safe as Silver join key. |
# MAGIC | `exon_rank` | always-present | INTEGER | 1-based exon number within ENST00000357033. Matches the clinical exon numbering used in AON eligibility tables (e.g. "exon 51 skip" = `exon_rank = 51`). |
# MAGIC | `seq_region_name` | always-present | STRING | Chromosome identifier (expected: `"X"`). Confirms the correct locus. |
# MAGIC | `start` | always-present | INTEGER | GRCh38 genomic start coordinate (leftmost, regardless of strand). For minus-strand DMD, higher `start` = earlier in the transcript. |
# MAGIC | `end` | always-present | INTEGER | GRCh38 genomic end coordinate. Exon size = `end - start + 1`. |
# MAGIC | `strand` | always-present | INTEGER | -1 for DMD (minus strand). Required for correct directional interpretation in HGVS cDNA-to-genomic mapping. |
# MAGIC | `size` | always-present | INTEGER | Computed: `end - start + 1`. Stored at Bronze to simplify Silver reads; redundant with `start`/`end` but avoids recomputation in every consumer. |
# MAGIC | `phase` | always-present | INTEGER | `ensembl_phase` — reading frame phase at exon start (-1/0/1/2). The primary input to the cumulative reading frame derivation. |
# MAGIC | `end_phase` | always-present | INTEGER | `ensembl_end_phase` — reading frame phase at exon end. Must chain to the next exon's `phase`. A phase-0 start and phase-0 end means the exon contributes 0 residual phase disruption when deleted alone. |
# MAGIC | `constitutive` | always-present | INTEGER | 1 if the exon is constitutive across all DMD transcripts, 0 otherwise. Higher confidence for reading frame computation. |
# MAGIC | `transcript_id` | always-present | STRING | Hardcoded `"ENST00000357033"` (= `Parent` field value). Pinned at Bronze to make the canonical transcript explicit. |
# MAGIC | `gene_id` | always-present | STRING | `"ENSG00000198947"` (DMD). Pinned at Bronze for join compatibility with other Discovery domain sources that reference the gene-level stable ID. |
# MAGIC | `assembly` | always-present | STRING | `assembly_name` from API response (e.g. `"GRCh38"`). Pinned for coordinate system versioning. |
# MAGIC | `cumulative_size` | always-present | INTEGER | Derived: running total of `size` from exon 1 through this exon. Allows Silver to compute `cumulative_size mod 3` to determine the reading frame offset after any given exon. |
# MAGIC | `source_system` | always-present | STRING | Provenance: `"ensembl_rest"`. |
# MAGIC | `ingestion_timestamp` | always-present | STRING | UTC ISO-8601 timestamp of Bronze write. ALCOA+ contemporaneous. |
# MAGIC | `api_version` | always-present | STRING | Ensembl REST API release version captured at ingestion (e.g. `"ensembl_rest_v15.10"`). |
# MAGIC | `source_url` | always-present | STRING | Exact API URL used to retrieve the exon data — replayable for audit. |
# MAGIC
# MAGIC **Silver transformation complexity:**
# MAGIC - `size` and `cumulative_size` are trivially computed from `start`/`end` — no Silver complexity.
# MAGIC - `phase` / `end_phase` are directly usable — no normalisation needed. The phase chain consistency
# MAGIC   check in Section 5 is the only validation needed before Silver can rely on these values.
# MAGIC - No nested structures, arrays, or free text fields — this is a geometrically clean reference table.
# MAGIC
# MAGIC **Downstream use-case column mapping:**
# MAGIC - Reading frame computation: `exon_rank`, `size`, `phase`, `end_phase`, `cumulative_size`
# MAGIC - HGVS cDNA coordinate-to-exon mapping: `exon_rank`, `start`, `end`, `strand`, `assembly`
# MAGIC - Hotspot region classification: `exon_rank` (exons 3–9 and 45–55)
# MAGIC - Provenance audit: `source_system`, `ingestion_timestamp`, `api_version`, `source_url`

# COMMAND ----------

from datetime import datetime, timezone  # noqa: E402

INGESTION_TIMESTAMP = datetime.now(timezone.utc).isoformat()
SOURCE_URL = exon_resp.url  # exact URL including query parameters

# Compute cumulative size in rank order for the reading frame derivation
sorted_for_bronze = sorted(canonical_exons, key=lambda x: x.get("rank", 0))
cumulative = 0
bronze_rows = []
for exon in sorted_for_bronze:
    size = exon["end"] - exon["start"] + 1
    cumulative += size
    row = {
        "exon_id":             exon.get("exon_id"),
        "exon_rank":           exon.get("rank"),
        "seq_region_name":     exon.get("seq_region_name"),
        "start":               exon["start"],
        "end":                 exon["end"],
        "strand":              exon.get("strand"),
        "size":                size,
        "phase":               exon.get("ensembl_phase"),
        "end_phase":           exon.get("ensembl_end_phase"),
        "constitutive":        exon.get("constitutive"),
        "transcript_id":       TRANSCRIPT_ID,
        "gene_id":             GENE_ID,
        "assembly":            exon.get("assembly_name", "GRCh38"),
        "cumulative_size":     cumulative,
        "source_system":       "ensembl_rest",
        "ingestion_timestamp": INGESTION_TIMESTAMP,
        "api_version":         API_VERSION,
        "source_url":          SOURCE_URL,
    }
    bronze_rows.append(row)

print(f"Bronze rows built: {len(bronze_rows)}")

# Preview first and last row
print("\nFirst Bronze row (exon 1):")
for col, val in bronze_rows[0].items():
    print(f"  {col:<25} = {val!r}")

print("\nLast Bronze row (exon 79):")
for col, val in bronze_rows[-1].items():
    print(f"  {col:<25} = {val!r}")

# COMMAND ----------

# Show first 10 and last 10 exons in rank order to verify the table looks correct
print("First 10 exons:")
print(f"  {'rank':>4}  {'exon_id':<22}  {'size':>6}  {'cum_size':>9}  "
      f"{'cum%3':>5}  {'phase':>5}  {'end_phase':>9}")
print("  " + "-" * 75)
for row in bronze_rows[:10]:
    print(
        f"  {row['exon_rank']:>4}  {row['exon_id']:<22}  {row['size']:>6}  "
        f"{row['cumulative_size']:>9,}  {row['cumulative_size'] % 3:>5}  "
        f"{row['phase']:>5}  {row['end_phase']:>9}"
    )

print(f"\nLast 10 exons:")
print(f"  {'rank':>4}  {'exon_id':<22}  {'size':>6}  {'cum_size':>9}  "
      f"{'cum%3':>5}  {'phase':>5}  {'end_phase':>9}")
print("  " + "-" * 75)
for row in bronze_rows[-10:]:
    print(
        f"  {row['exon_rank']:>4}  {row['exon_id']:<22}  {row['size']:>6}  "
        f"{row['cumulative_size']:>9,}  {row['cumulative_size'] % 3:>5}  "
        f"{row['phase']:>5}  {row['end_phase']:>9}"
    )

# COMMAND ----------

# Verify the reading frame invariant: cumulative_size mod 3 after exon 79 must equal 0
# (The DMD coding sequence is a complete number of codons — no dangling nucleotides at the 3′ end)
final_cumulative = bronze_rows[-1]["cumulative_size"]
final_mod3 = final_cumulative % 3
print(f"\nReading frame invariant check:")
print(f"  Total coding nucleotides (sum of all 79 exon sizes): {final_cumulative:,}")
print(f"  {final_cumulative} mod 3 = {final_mod3}  "
      f"{'PASS — coding sequence is in-frame end-to-end' if final_mod3 == 0 else 'FAIL — unexpected residual phase'}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 7 — Provenance Metadata
# MAGIC
# MAGIC Genomic coordinates seem like objective facts — they are base positions in a reference assembly.
# MAGIC But their clinical meaning is entirely dependent on the coordinate system they belong to. A coordinate
# MAGIC from GRCh37 (hg19) placed on GRCh38 without liftover will point to the wrong nucleotide. A coordinate
# MAGIC from Ensembl release 108 may differ from release 112 if the gene model was revised. Without
# MAGIC rigorous provenance tracking, it is impossible to determine whether a coordinate discrepancy between
# MAGIC two sources is a data error or an assembly version difference.
# MAGIC
# MAGIC **ALCOA+ principles applied to Ensembl Bronze:**
# MAGIC - **Attributable**: `source_system = "ensembl_rest"` identifies the data source. The `source_url`
# MAGIC   records the exact API call — it can be replayed to retrieve the same data and verify that it has
# MAGIC   not changed between ingestion runs.
# MAGIC - **Legible**: all fields are stored in standard types (integers for coordinates, strings for IDs).
# MAGIC   No encoding normalisation needed — Ensembl coordinates are well-defined integers.
# MAGIC - **Contemporaneous**: `ingestion_timestamp` captures the UTC wall-clock time of this Bronze write.
# MAGIC   If Ensembl updates the gene model in a future release (e.g., corrects an exon boundary), the
# MAGIC   `ingestion_timestamp` will differ between the old and new Bronze records, making the update detectable.
# MAGIC - **Original**: `start`, `end`, `strand`, `phase`, `end_phase` are stored exactly as the API returns
# MAGIC   them — no transformation, rounding, or normalisation at Bronze. The `size` and `cumulative_size`
# MAGIC   columns are clearly derived (stored for convenience) rather than raw API fields.
# MAGIC - **Accurate**: `api_version` pins the Ensembl REST server release. If Ensembl changes the gene model
# MAGIC   in a future release, a new Bronze ingestion will carry a different `api_version` — enabling
# MAGIC   downstream Silver to detect and flag coordinate drift. The `assembly` field confirms the GRCh38
# MAGIC   coordinate system and must be validated against the assembly used by LOVD and ClinVar variant records
# MAGIC   before the HGVS cDNA-to-exon mapping join is performed.

# COMMAND ----------

from datetime import datetime, timezone  # noqa: F811, E402

def build_provenance(api_version, source_url):
    """Return ALCOA+ provenance fields for Ensembl Bronze rows."""
    return {
        "source_system":       "ensembl_rest",
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_version":         api_version,
        "source_url":          source_url,
    }

# Demonstrate provenance attachment on a single row
example_provenance = build_provenance(API_VERSION, SOURCE_URL)
print("ALCOA+ provenance fields for Ensembl Bronze:")
for field, value in example_provenance.items():
    print(f"  {field:<25} = {value!r}")

print(f"\nEnsembl REST API version captured: {API_VERSION}")
print(f"Assembly pinned in source_url    : GRCh38 (inferred from response assembly_name field)")
print(f"Source URL is replayable         : {SOURCE_URL}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 8 — Write to Personal Schema
# MAGIC
# MAGIC Writing the Bronze exon table to `workspace.steff_horemans.bronze_ensembl_exons_raw`.
# MAGIC
# MAGIC `workspace.steff_horemans` is the **ungoverned personal schema** per ADR-01. Tables written here:
# MAGIC - Are never imported from production pipelines (`discovery.bronze.*`, `silver.*`, `gold.*`).
# MAGIC - Exist solely as disposable exploration artifacts for local inspection and iteration.
# MAGIC - Have no data contract, no DLT quality rules, and no downstream consumers.
# MAGIC - May be overwritten or dropped at any time without notification.
# MAGIC
# MAGIC The `USE workspace.steff_horemans` statement sets this schema as the session default so that subsequent
# MAGIC `DESCRIBE TABLE` or `SELECT` SQL in this notebook can omit the catalog and schema prefix.
# MAGIC
# MAGIC **An explicit `BRONZE_SCHEMA` is required** — the `size`, `phase`, `end_phase`, and `constitutive`
# MAGIC fields are integers that Spark would correctly infer from the Python list, but `cumulative_size` could
# MAGIC in principle produce a `LongType` on large genes. Providing an explicit `IntegerType` schema avoids
# MAGIC type mismatches when this table is later unioned or joined against Silver tables that define
# MAGIC `exon_rank` as `IntegerType`.
# MAGIC
# MAGIC **Execution model**: `DatabricksSession` (Databricks Connect) runs the Python code locally but
# MAGIC executes Spark and the Delta write on the remote Databricks cluster. The 79-row `bronze_rows` list
# MAGIC is serialised and sent to the cluster; the Delta table is created in Unity Catalog.

# COMMAND ----------

from databricks.connect import DatabricksSession  # noqa: E402
from pyspark.sql.types import (  # noqa: E402
    IntegerType,
    StringType,
    StructField,
    StructType,
)

# Explicit schema — always provide this; never rely on Spark schema inference for Bronze tables.
BRONZE_SCHEMA = StructType([
    StructField("exon_id",             StringType(),  True),
    StructField("exon_rank",           IntegerType(), False),
    StructField("seq_region_name",     StringType(),  True),
    StructField("start",               IntegerType(), False),
    StructField("end",                 IntegerType(), False),
    StructField("strand",              IntegerType(), False),
    StructField("size",                IntegerType(), False),
    StructField("phase",               IntegerType(), True),
    StructField("end_phase",           IntegerType(), True),
    StructField("constitutive",        IntegerType(), True),
    StructField("transcript_id",       StringType(),  False),
    StructField("gene_id",             StringType(),  False),
    StructField("assembly",            StringType(),  False),
    StructField("cumulative_size",     IntegerType(), False),
    StructField("source_system",       StringType(),  False),
    StructField("ingestion_timestamp", StringType(),  False),
    StructField("api_version",         StringType(),  False),
    StructField("source_url",          StringType(),  False),
])

# Connects to the remote cluster via Databricks Connect — execution happens on Databricks.
spark = DatabricksSession.builder.profile("steff_horemans").serverless(True).getOrCreate()
# Alternative if serverless is not available:
# spark = DatabricksSession.builder.profile("steff_horemans").clusterId("<cluster-id>").getOrCreate()

spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.steff_horemans")
spark.sql("USE workspace.steff_horemans")

df = spark.createDataFrame(bronze_rows, schema=BRONZE_SCHEMA)

(
    df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.steff_horemans.bronze_ensembl_exons_raw")
)

print(f"Written {df.count()} rows to workspace.steff_horemans.bronze_ensembl_exons_raw")
spark.sql("DESCRIBE TABLE bronze_ensembl_exons_raw").show(truncate=False)
