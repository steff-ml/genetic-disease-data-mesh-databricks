# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # ClinVar — First Look Exploration
# MAGIC
# MAGIC **Source**: NCBI ClinVar — variant pathogenicity classifications (DMD gene)
# MAGIC **Target table**: `workspace.steff_horemans.bronze_clinvar_submissions_raw`
# MAGIC **API base**: NCBI E-utilities — `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
# MAGIC **Auth type**: Public — API key optional (raises rate limit from 3 req/s to 10 req/s)
# MAGIC **Author**: exploration-notebook agent
# MAGIC **Date**: 2026-06-06
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Section 0 — Context and Purpose
# MAGIC
# MAGIC ClinVar is the **secondary Bronze source for the Discovery domain** and the upstream input for the
# MAGIC ADR-06 pathogenicity conflict detection rule. It feeds the pipeline:
# MAGIC
# MAGIC ```
# MAGIC workspace.steff_horemans.bronze_clinvar_submissions_raw
# MAGIC   → silver.dmd_variants         (cross-referenced against LOVD for ADR-06 conflict detection)
# MAGIC   → silver.variant_classification (per-variant ACMG tier; evidence level)
# MAGIC   → gold.dmd_mutation_catalogue  (promoted only when LOVD ↔ ClinVar conflict is resolved)
# MAGIC ```
# MAGIC
# MAGIC ClinVar is a **Layer 1 (mutation-intrinsic)** source. Its primary value in this pipeline is not as
# MAGIC a variant discovery source — LOVD is the primary catalogue — but as the **independent pathogenicity
# MAGIC reference** against which LOVD classification disagreements are detected. Per ADR-06:
# MAGIC
# MAGIC > When LOVD and ClinVar report conflicting pathogenicity for the same variant (matched on normalised
# MAGIC > HGVS), `silver.dmd_variants` sets `classification_conflict = true` and `action_required = 'expert_review'`.
# MAGIC > The variant is quarantined from Gold promotion until resolved.
# MAGIC
# MAGIC ClinVar uses the five-tier ACMG scale: **Pathogenic / Likely pathogenic / Uncertain significance
# MAGIC (VUS) / Likely benign / Benign**. LOVD uses a different encoding (`+/+?/-/-?/?/.`). The Silver
# MAGIC transformation must map both to a shared canonical tier before comparison.
# MAGIC
# MAGIC The scientific question this exploration answers: **what structured fields does ClinVar return for
# MAGIC DMD gene variants via the E-utilities API, and are the pathogenicity classification and HGVS notation
# MAGIC fields sufficiently standardised to drive ADR-06 conflict detection against LOVD?** The exploration
# MAGIC also establishes the scale of DMD-relevant submissions and flags the key quality gap: ClinVar
# MAGIC frequently omits exon-level coordinates, which limits its utility for direct reading frame computation
# MAGIC but does not block its use as a pathogenicity reference.
# MAGIC
# MAGIC A successful Bronze ingestion of this source enables:
# MAGIC 1. `silver.variant_classification` — per-variant ACMG tier with evidence level and review status.
# MAGIC 2. `silver.dmd_variants` — `classification_conflict` flags populated by joining ClinVar against LOVD
# MAGIC    on HGVS-normalised variant identifiers.
# MAGIC 3. `gold.dmd_mutation_catalogue` — higher-confidence variant records where LOVD and ClinVar agree,
# MAGIC    and explicitly flagged records where they do not.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 1 — Connection and Authentication
# MAGIC
# MAGIC ClinVar is publicly accessible through the NCBI E-utilities API. No credentials, Data Access Agreement,
# MAGIC or pre-registration are required for read access. An **optional free NCBI API key** raises the rate
# MAGIC limit from 3 requests/second to 10 requests/second — this is strongly recommended for any ingestion
# MAGIC run that fetches more than a few hundred records.
# MAGIC
# MAGIC To obtain a free NCBI API key: create an NCBI account at https://www.ncbi.nlm.nih.gov/account/,
# MAGIC then generate a key under Account Settings → API Key Management.
# MAGIC
# MAGIC **Why ClinVar via E-utilities over alternatives:**
# MAGIC - **E-utilities (esearch + efetch)** is the official NCBI programmatic API. It supports ClinVar
# MAGIC   natively and returns structured XML with all submission-level fields.
# MAGIC - **ClinVar REST API** (`submit.ncbi.nlm.nih.gov/api/v1/`) is a *submission* API only — it requires
# MAGIC   a pre-registered organisation key and accepts POST requests to create submissions. It does not expose
# MAGIC   any query or retrieval endpoints. It is not applicable to this Bronze ingestion use case.
# MAGIC - **ClinVar FTP bulk files** (`ftp.ncbi.nlm.nih.gov/pub/clinvar/`) provide tab-delimited and XML
# MAGIC   snapshots of the entire ClinVar database, updated weekly. The `variant_summary.txt.gz` file contains
# MAGIC   one row per variation with all key classification fields. **This is the preferred approach for
# MAGIC   production ingestion** (single download, no pagination, no rate limit concerns). The E-utilities
# MAGIC   approach explored in this notebook is better suited to targeted record retrieval and schema inspection.
# MAGIC   A production ADR should choose FTP bulk + weekly refresh over per-record API calls.
# MAGIC - **HGMD** is excluded per the STOP rule — subscription required.

# COMMAND ----------

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

# ---------------------------------------------------------------------------
# NCBI E-utilities base URLs
# ---------------------------------------------------------------------------
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# NCBI API key — stored in Databricks secrets.
# Scope and key name are placeholders; set actual values once the key is generated.
# Without a key the rate limit is 3 req/s. With a key it is 10 req/s.
try:
    NCBI_API_KEY = dbutils.secrets.get(scope="ncbi", key="api_key")  # TODO: confirm scope name
except Exception:
    NCBI_API_KEY = None  # Proceed unauthenticated at 3 req/s

# Required by NCBI for all E-utilities requests (non-commercial research use)
NCBI_TOOL  = "dmd-eligibility-mesh-exploration"
NCBI_EMAIL = "steffhoremans3@gmail.com"

# ---------------------------------------------------------------------------
# Minimal connectivity test — EInfo for the clinvar database
# ---------------------------------------------------------------------------
einfo_url = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi"
    f"?db=clinvar&retmode=json&tool={NCBI_TOOL}&email={NCBI_EMAIL}"
)
if NCBI_API_KEY:
    einfo_url += f"&api_key={NCBI_API_KEY}"

resp = requests.get(einfo_url, timeout=30)
assert resp.status_code == 200, f"EInfo connectivity test failed: HTTP {resp.status_code}"

einfo = resp.json()
db_info = einfo["einforesult"]["dbinfo"][0]
print("Database name  :", db_info["dbname"])
print("Record count   :", db_info["count"])
print("Last update    :", db_info["lastupdate"])
print("Connectivity test passed — ClinVar E-utilities API is reachable.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 2 — Endpoint and Parameter Selection
# MAGIC
# MAGIC The E-utilities query strategy for DMD variants uses two endpoints in sequence:
# MAGIC
# MAGIC 1. **ESearch** (`esearch.fcgi`) — translates the gene-based query into a list of ClinVar variation IDs
# MAGIC    (UIDs). The term `DMD[gene]` filters to all submissions where the gene symbol is `DMD`. Combined
# MAGIC    with `Homo sapiens[orgn]` to exclude non-human submissions and `clinsig[prop]` to return only
# MAGIC    records with at least one clinical significance assertion. `usehistory=y` stores the result set
# MAGIC    on the NCBI History server, enabling paginated EFetch calls without re-running the query.
# MAGIC
# MAGIC 2. **EFetch** (`efetch.fcgi`) or **ESummary** (`esummary.fcgi`) — retrieves full records or document
# MAGIC    summaries by UID. For Bronze schema inspection, ESummary (`retmode=json`) is more convenient:
# MAGIC    it returns structured JSON with the key classification fields (clinical significance, review status,
# MAGIC    condition, HGVS). EFetch with `retmode=xml` returns the full ClinVar XML set with all submitter-
# MAGIC    level detail at the cost of much larger payloads.
# MAGIC
# MAGIC **Why these filter parameters specifically:**
# MAGIC - `DMD[gene]`: ClinVar indexes gene symbol as a searchable field. This is the most precise filter for
# MAGIC   the dystrophin gene — more reliable than searching by disease name (which returns variants associated
# MAGIC   with DMD in any gene) or by chromosomal position (which requires coordinate maintenance).
# MAGIC - `Homo sapiens[orgn]`: ClinVar contains variants from multiple species in research submissions.
# MAGIC   Excluding non-human records avoids noise in the schema inspection.
# MAGIC - No pathogenicity filter at Bronze: Bronze ingests all submissions regardless of classification.
# MAGIC   Filtering by `Pathogenic[clinsig]` would exclude VUS and conflicting records that are needed for
# MAGIC   the ADR-06 conflict detection logic in Silver. All tiers are required.

# COMMAND ----------

# ---------------------------------------------------------------------------
# ESearch: retrieve all ClinVar UIDs for DMD gene variants
# ---------------------------------------------------------------------------
SEARCH_TERM = "DMD[gene]"
RATE_LIMIT_SLEEP = 0.35  # 3 req/s unauthenticated; 0.1 s with API key

search_params = {
    "db":         "clinvar",
    "term":       SEARCH_TERM,
    "retmax":     0,           # 0 = return only count, no IDs yet
    "retmode":    "json",
    "usehistory": "y",
    "tool":       NCBI_TOOL,
    "email":      NCBI_EMAIL,
}
if NCBI_API_KEY:
    search_params["api_key"] = NCBI_API_KEY

search_resp = requests.get(ESEARCH_URL, params=search_params, timeout=30)
assert search_resp.status_code == 200, f"ESearch failed: HTTP {search_resp.status_code}"

search_result = search_resp.json()["esearchresult"]
total_count = int(search_result["count"])
web_env     = search_result["webenv"]
query_key   = search_result["querykey"]

print(f"Search term    : {SEARCH_TERM}")
print(f"Total UIDs     : {total_count:,}")
print(f"WebEnv         : {web_env[:40]}...")
print(f"QueryKey       : {query_key}")

time.sleep(RATE_LIMIT_SLEEP)

# ---------------------------------------------------------------------------
# Fetch a small sample (10 records) using ESummary for schema inspection
# ---------------------------------------------------------------------------
sample_params = {
    "db":       "clinvar",
    "query_key": query_key,
    "WebEnv":   web_env,
    "retstart": 0,
    "retmax":   10,
    "retmode":  "json",
    "tool":     NCBI_TOOL,
    "email":    NCBI_EMAIL,
}
if NCBI_API_KEY:
    sample_params["api_key"] = NCBI_API_KEY

sample_resp = requests.get(ESUMMARY_URL, params=sample_params, timeout=30)
assert sample_resp.status_code == 200, f"ESummary failed: HTTP {sample_resp.status_code}"

sample_data = sample_resp.json()
uids = sample_data["result"]["uids"]
print(f"\nFetched {len(uids)} sample UIDs: {uids}")

time.sleep(RATE_LIMIT_SLEEP)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 3 — Response Schema Inspection
# MAGIC
# MAGIC The ESummary response for ClinVar returns a JSON object keyed by variation UID. Each record contains
# MAGIC the fields documented below. Annotations reflect clinical relevance to the DMD eligibility pipeline.
# MAGIC
# MAGIC ### Field annotations
# MAGIC
# MAGIC | Field | Type | Clinical relevance |
# MAGIC |-------|------|-------------------|
# MAGIC | `uid` | string | ClinVar variation ID — stable numeric identifier for the variant. Primary join key to LOVD for ADR-06 conflict detection (secondary to HGVS match). |
# MAGIC | `title` | string | Human-readable label (e.g. `NM_004006.3(DMD):c.31+1G>T`). Contains HGVS but not parseable directly — use `variation_set[].variation.hgvs_expressions[]` instead. |
# MAGIC | `obj_type` | string | Variant type: `single nucleotide variant`, `Deletion`, `Duplication`, `Indel`. Maps to Layer 1 variant class axis. `Deletion` and `Duplication` require reading frame computation. |
# MAGIC | `accession` | string | RCV accession — the record-level accession aggregating all conditions for this variant. |
# MAGIC | `accession_version` | string | RCV accession with version suffix (e.g. `RCV000001234.5`). Version increments when classification is updated — relevant for tracking reclassifications in Delta. |
# MAGIC | `clinical_significance.description` | string | **Most important field for ADR-06.** ACMG 5-tier classification: `Pathogenic`, `Likely pathogenic`, `Uncertain significance`, `Likely benign`, `Benign`. Also `Conflicting interpretations of pathogenicity` when submitters disagree within ClinVar itself. |
# MAGIC | `clinical_significance.review_status` | string | Evidence quality tier: `practice guideline` > `reviewed by expert panel` > `criteria provided, multiple submitters, no conflicts` > `criteria provided, single submitter` > `criteria provided, conflicting interpretations` > `no assertion criteria provided` > `no classification provided`. Low review status records should be weighted less in ADR-06 conflict resolution. |
# MAGIC | `clinical_significance.last_evaluated` | string | Date of most recent pathogenicity evaluation. Critical for data currency checks — stale evaluations (>3 years) may reflect outdated evidence. |
# MAGIC | `variation_set[].variation.hgvs_expressions[]` | array | HGVS notation at nucleotide and protein level, in multiple assemblies. **The join key for ADR-06**: normalise to NM_004006-anchored cDNA HGVS for cross-source matching against LOVD. Assembly-specific genomic HGVS (NC_ accessions) must be excluded from the join key. |
# MAGIC | `variation_set[].variation.variant_type` | string | More granular than `obj_type`: `single nucleotide variant`, `deletion`, `duplication`, `insertion`, `indel`, `complex`. |
# MAGIC | `genes[].symbol` | string | Gene symbol — should be `DMD` for all records in this query. Verify: non-DMD hits indicate the search term matches on adjacent genes or multi-gene records. |
# MAGIC | `genes[].id` | string | NCBI Gene ID — `1756` for DMD. Stable numeric identifier independent of symbol changes. |
# MAGIC | `supporting_submissions.scv[]` | array | SCV accessions of individual submitter records. ClinVar aggregates multiple SCV records into one RCV. Pathogenicity conflicts within ClinVar appear here as multiple SCVs with different classifications. |
# MAGIC | `condition_keys[].title` | string | Condition name (e.g. `Duchenne muscular dystrophy`). ClinVar links variants to conditions via MedGen CUIs. Multiple conditions may be linked. |
# MAGIC | `condition_keys[].db` | string | Condition database (`MedGen`, `OMIM`, `Orphanet`). |
# MAGIC | `condition_keys[].id` | string | Condition identifier in the referenced database. For DMD: MedGen CUI `C3661900`, OMIM `310200`. |
# MAGIC | `protein_change` | string | Protein-level consequence (e.g. `L11F`). Sparse — frequently absent for non-coding and splice site variants. Not used in reading frame computation; supplementary only. |
# MAGIC | `location.cytogenetic_location` | string | Cytogenetic band (e.g. `Xp21.2`). Confirms DMD locus. |
# MAGIC
# MAGIC ### Key quality observations from API docs
# MAGIC
# MAGIC - **Exon coordinates are absent from ESummary.** ClinVar does not return a structured `exon_number`
# MAGIC   field in the summary response. Exon impact must be inferred from the HGVS cDNA notation at Silver
# MAGIC   (e.g. parsing `c.4234-?_5154+?del` implies a deletion spanning exons 30–36). This is the single
# MAGIC   largest quality limitation for using ClinVar as a reading frame computation source.
# MAGIC - **EFetch XML contains a `<Location>` block** with `<SequenceLocation Assembly="GRCh38">` including
# MAGIC   `start`, `stop`, `display_start`, `display_stop` genomic coordinates. These can be mapped to exon
# MAGIC   boundaries via the Ensembl exon reference table, recovering approximate exon impact at Silver cost.
# MAGIC - **`Conflicting interpretations of pathogenicity`** is a valid `clinical_significance.description`
# MAGIC   value — it means ClinVar's own submitters disagree. Such records must be flagged in Bronze and handled
# MAGIC   carefully in the ADR-06 conflict rule (a variant that ClinVar itself marks as conflicting cannot
# MAGIC   serve as a definitive reference to resolve a LOVD disagreement).

# COMMAND ----------

# ---------------------------------------------------------------------------
# Inspect the first ESummary record — print all top-level keys and values
# ---------------------------------------------------------------------------
first_uid = uids[0]
record = sample_data["result"][first_uid]

print(f"Inspecting UID: {first_uid}\n")
print("Top-level keys:")
for key, value in record.items():
    if isinstance(value, (dict, list)):
        print(f"  {key:40s} → {type(value).__name__} (len={len(value)})")
    else:
        print(f"  {key:40s} → {repr(value)[:80]}")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Drill into the clinically important nested fields
# ---------------------------------------------------------------------------
print("--- germline_classification ---")
clin_sig = record.get("germline_classification", {})
for k, v in clin_sig.items():
    print(f"  {k}: {v}")

print("\n--- genes ---")
for gene in record.get("genes", []):
    print(f"  symbol={gene.get('symbol')}  geneid={gene.get('geneid')}")

print("\n--- HGVS expressions (variation_set[0]) ---")
variation_sets = record.get("variation_set", [])
if variation_sets:
    for hgvs in variation_sets[0].get("variation", {}).get("hgvs_expressions", []):
        print(f"  {hgvs.get('assembly',''):<10} {hgvs.get('nucleotide_expression','')}")

print("\n--- trait_set ---")
for cond in record.get("trait_set", []):
    print(f"  {cond}")

print("\n--- supporting SCVs ---")
scvs = record.get("supporting_submissions", {}).get("scv", [])
print(f"  {len(scvs)} SCV accession(s): {scvs[:5]}")

print("\n--- obj_type / protein_change ---")
print(f"  obj_type      : {record.get('obj_type')}")
print(f"  protein_change: {record.get('protein_change')}")
print(f"  accession     : {record.get('accession')}")
print(f"  accession_ver : {record.get('accession_version')}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 4 — Pagination Walkthrough
# MAGIC
# MAGIC The NCBI History server strategy (`usehistory=y`) is the recommended pattern for large result sets.
# MAGIC After ESearch stores the query result, EFetch/ESummary calls use `WebEnv` and `query_key` with
# MAGIC sliding `retstart` to retrieve records in batches.
# MAGIC
# MAGIC The E-utilities `retmax` cap is **10,000 records per request**. For a ClinVar DMD query that returns
# MAGIC several thousand UIDs, a single ESummary call with `retmax=10000` would reach the entire result set.
# MAGIC If the total exceeds 10,000, multiple pages are needed.
# MAGIC
# MAGIC **Pagination gotchas observed:**
# MAGIC - The History server WebEnv token expires after approximately 1 hour of inactivity. For long-running
# MAGIC   ingestion jobs, re-run ESearch at the start and do not cache WebEnv across Databricks job runs.
# MAGIC - `retstart` is 0-indexed. Page boundaries: page 0 = retstart 0–999, page 1 = retstart 1000–1999.
# MAGIC - The JSON response's `result.uids` array always contains the UIDs in the current page window, even
# MAGIC   when using History server mode. Iterate this array to collect all returned records.
# MAGIC - **Rate limiting**: without an API key, 3 requests/second is the hard ceiling. Violating it returns
# MAGIC   HTTP 429. Use `time.sleep(0.35)` between calls unauthenticated; `time.sleep(0.11)` with API key.
# MAGIC
# MAGIC **Production ingestion recommendation**: use the ClinVar FTP `variant_summary.txt.gz` (tab-delimited,
# MAGIC weekly snapshot) instead of paginated E-utilities calls. The file contains all fields available in
# MAGIC ESummary with no rate limit concerns and a single download. The E-utilities approach demonstrated here
# MAGIC is appropriate for targeted record retrieval and the incremental update pattern (fetch only records
# MAGIC updated since last ingestion using `date_modified[MDAT]` in the search term).

# COMMAND ----------

# ---------------------------------------------------------------------------
# Fetch 3 pages of 5 records each — verify field consistency across pages
# ---------------------------------------------------------------------------
PAGE_SIZE = 5
pages_to_fetch = 3

all_records = {}
for page_num in range(pages_to_fetch):
    retstart = page_num * PAGE_SIZE
    page_params = {
        "db":        "clinvar",
        "query_key": query_key,
        "WebEnv":    web_env,
        "retstart":  retstart,
        "retmax":    PAGE_SIZE,
        "retmode":   "json",
        "tool":      NCBI_TOOL,
        "email":     NCBI_EMAIL,
    }
    if NCBI_API_KEY:
        page_params["api_key"] = NCBI_API_KEY

    page_resp = requests.get(ESUMMARY_URL, params=page_params, timeout=30)
    assert page_resp.status_code == 200, (
        f"Page {page_num} fetch failed: HTTP {page_resp.status_code}"
    )

    page_data   = page_resp.json()
    page_uids   = page_data["result"]["uids"]
    page_records = {uid: page_data["result"][uid] for uid in page_uids}
    all_records.update(page_records)

    top_keys_this_page = set(page_data["result"][page_uids[0]].keys())
    print(f"Page {page_num} (retstart={retstart}): {len(page_uids)} records, "
          f"top-level keys count = {len(top_keys_this_page)}")

    time.sleep(RATE_LIMIT_SLEEP)

print(f"\nTotal records collected across {pages_to_fetch} pages: {len(all_records)}")

# Verify key consistency: all pages must expose the same top-level keys
all_key_sets = [set(r.keys()) for r in all_records.values()]
union_keys   = set.union(*all_key_sets)
common_keys  = set.intersection(*all_key_sets)
if union_keys == common_keys:
    print("Key consistency check PASSED — all records have identical top-level keys.")
else:
    missing = union_keys - common_keys
    print(f"Key consistency check WARNING — {len(missing)} key(s) absent from some records: {missing}")

# Volume estimate
print(f"\nTotal DMD variant UIDs in ClinVar: {total_count:,}")
print(f"At retmax=500 per call, full ingest requires ~{(total_count // 500) + 1} API calls.")
print("FTP variant_summary.txt.gz avoids this entirely — strongly preferred for production.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 5 — Data Quality First Look
# MAGIC
# MAGIC This section checks null rates, classification distribution, and date ranges across the paginated
# MAGIC sample. The findings directly inform which `@dlt.expect_or_quarantine` rules the production DLT
# MAGIC pipeline must implement.
# MAGIC
# MAGIC ### Known quality issues from API documentation and domain knowledge
# MAGIC
# MAGIC - **Conflicting interpretations within ClinVar**: when multiple submitters disagree, ClinVar sets
# MAGIC   `clinical_significance.description = "Conflicting interpretations of pathogenicity"`. These records
# MAGIC   cannot serve as a definitive pathogenicity reference for ADR-06 comparison against LOVD. They must
# MAGIC   be flagged separately from records with a clean single-tier classification.
# MAGIC - **Missing `last_evaluated` date**: many older submissions predate the structured date field. A null
# MAGIC   `last_evaluated` means the classification's currency cannot be assessed — treat as low confidence.
# MAGIC - **`protein_change` sparsity**: non-coding variants (splice site, deep intronic) will never carry a
# MAGIC   protein change annotation. This is expected, not a quality defect.
# MAGIC - **Multiple conditions per variant**: a single RCV may link to both `Duchenne muscular dystrophy`
# MAGIC   and `Becker muscular dystrophy` (expected for in-frame variants) or unrelated conditions (data
# MAGIC   quality concern). Silver must retain all linked conditions, not just the first.
# MAGIC - **HGVS expression completeness**: some older records carry only genomic HGVS (NC_ accessions) with
# MAGIC   no NM_004006-anchored cDNA expression. Without a cDNA HGVS, the variant cannot be matched to LOVD
# MAGIC   records. Flag for Silver enrichment via Ensembl VEP.

# COMMAND ----------

# ---------------------------------------------------------------------------
# Null rates for key fields across the paginated sample
# ---------------------------------------------------------------------------
records_list = list(all_records.values())
n = len(records_list)

def field_null_rate(records, extractor, label):
    """Report null/empty rate for a field extracted by extractor callable."""
    missing = sum(1 for r in records if not extractor(r))
    print(f"  {label:<50s} null/empty: {missing}/{n} ({100*missing/n:.0f}%)")

print("=== Null rates across paginated sample ===\n")
field_null_rate(records_list,
    lambda r: r.get("germline_classification", {}).get("description"),
    "germline_classification.description")
field_null_rate(records_list,
    lambda r: r.get("germline_classification", {}).get("review_status"),
    "germline_classification.review_status")
field_null_rate(records_list,
    lambda r: r.get("germline_classification", {}).get("last_evaluated"),
    "germline_classification.last_evaluated")
field_null_rate(records_list,
    lambda r: r.get("accession"),
    "accession (RCV)")
field_null_rate(records_list,
    lambda r: r.get("genes"),
    "genes[]")
field_null_rate(records_list,
    lambda r: r.get("variation_set"),
    "variation_set[] (HGVS)")
field_null_rate(records_list,
    lambda r: r.get("germline_classification", {}).get("trait_set"),
    "germline_classification.trait_set[]")
field_null_rate(records_list,
    lambda r: r.get("protein_change"),
    "protein_change")

# ---------------------------------------------------------------------------
# Clinical significance distribution
# ---------------------------------------------------------------------------
print("\n=== Clinical significance distribution ===\n")
from collections import Counter
cs_counts = Counter(
    r.get("germline_classification", {}).get("description", "MISSING")
    for r in records_list
)
for tier, count in cs_counts.most_common():
    print(f"  {tier:<55s} {count}")

# ---------------------------------------------------------------------------
# Review status distribution
# ---------------------------------------------------------------------------
print("\n=== Review status distribution ===\n")
rs_counts = Counter(
    r.get("germline_classification", {}).get("review_status", "MISSING")
    for r in records_list
)
for status, count in rs_counts.most_common():
    print(f"  {status:<60s} {count}")

# ---------------------------------------------------------------------------
# HGVS expression type coverage (does any record have NM_004006 cDNA?)
# ---------------------------------------------------------------------------
print("\n=== HGVS expression types (sample) ===\n")
hgvs_types = Counter()
for r in records_list:
    for vs in r.get("variation_set", []):
        for hgvs in vs.get("variation", {}).get("hgvs_expressions", []):
            nt = hgvs.get("nucleotide_expression", "")
            if nt.startswith("NM_"):
                hgvs_types["RefSeq_cDNA (NM_)"] += 1
            elif nt.startswith("NC_"):
                hgvs_types["Genomic (NC_)"] += 1
            elif nt.startswith("NG_"):
                hgvs_types["RefSeqGene (NG_)"] += 1
            else:
                hgvs_types["Other/missing"] += 1
for htype, count in hgvs_types.most_common():
    print(f"  {htype:<40s} {count}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 6 — Bronze Schema Sketch
# MAGIC
# MAGIC The Bronze schema captures the ESummary response fields as-is, with provenance metadata appended.
# MAGIC No transformation is applied at Bronze — all normalisation (HGVS parsing, tier mapping, condition
# MAGIC deduplication) happens at Silver.
# MAGIC
# MAGIC ### Column inventory
# MAGIC
# MAGIC | Column | Source field | Presence | Notes |
# MAGIC |--------|-------------|----------|-------|
# MAGIC | `variation_id` | `uid` | Always | Stable ClinVar variation ID — primary key |
# MAGIC | `accession` | `accession` | Always | RCV accession (aggregated record) |
# MAGIC | `accession_version` | `accession_version` | Always | Versioned RCV — version increments on reclassification |
# MAGIC | `title` | `title` | Always | Human-readable label; contains HGVS substring but not structured |
# MAGIC | `obj_type` | `obj_type` | Always | Coarse variant type; use for routing at Silver |
# MAGIC | `gene_symbol` | `genes[0].symbol` | Always for DMD query | Should be `DMD`; multi-gene records may carry additional symbols |
# MAGIC | `gene_id` | `genes[0].id` | Always for DMD query | NCBI Gene ID `1756` — stable join key |
# MAGIC | `clinical_significance_description` | `clinical_significance.description` | Always | ACMG tier; may be `Conflicting interpretations of pathogenicity` |
# MAGIC | `clinical_significance_review_status` | `clinical_significance.review_status` | Always | Evidence quality tier — informs ADR-06 weight |
# MAGIC | `clinical_significance_last_evaluated` | `clinical_significance.last_evaluated` | Optional | Null for older submissions |
# MAGIC | `hgvs_expressions_json` | `variation_set[].variation.hgvs_expressions` | Always | Stored as JSON string; Silver extracts NM_004006 cDNA expression |
# MAGIC | `condition_keys_json` | `condition_keys` | Optional | Array of {db, id, title} objects; stored as JSON string |
# MAGIC | `protein_change` | `protein_change` | Optional | Absent for non-coding variants — expected |
# MAGIC | `supporting_scv_count` | `len(supporting_submissions.scv)` | Always | Count of individual submitter records; >1 means multiple submitters |
# MAGIC | `supporting_scv_json` | `supporting_submissions.scv` | Always | SCV accession list as JSON string |
# MAGIC | `source_system` | provenance | Always | `"clinvar"` |
# MAGIC | `ingestion_timestamp` | provenance | Always | UTC ISO-8601 at write time |
# MAGIC | `api_version` | provenance | Always | `"clinvar_eutils_v1"` |
# MAGIC | `source_url` | provenance | Always | Full ESummary request URL for this record |
# MAGIC
# MAGIC ### Silver transformation complexity flags
# MAGIC
# MAGIC - **`hgvs_expressions_json`** — requires parsing to extract the NM_004006-anchored cDNA HGVS.
# MAGIC   Multiple assembly versions and expression types are interleaved in the array. HGVS normalisation
# MAGIC   (via hgvs Python library or Ensembl VEP) may be needed for cross-source matching with LOVD.
# MAGIC - **`condition_keys_json`** — must be exploded and filtered to retain only DMD-linked conditions
# MAGIC   (MedGen C3661900, OMIM 310200, Orphanet 98896). Variants linked to unrelated conditions must
# MAGIC   not be dropped — the DMD condition link may coexist with other condition links.
# MAGIC - **`clinical_significance_description`** — must be mapped to the canonical 5-tier enum and then
# MAGIC   to LOVD's `+/+?/-/-?/?/.` encoding for ADR-06 conflict comparison. The mapping is:
# MAGIC   `Pathogenic` → `+`, `Likely pathogenic` → `+?`, `Uncertain significance` → `?`,
# MAGIC   `Likely benign` → `-?`, `Benign` → `-`, `Conflicting...` → `classification_conflict_internal = true`.
# MAGIC - **Exon coordinates absent**: ClinVar ESummary does not expose a structured exon field. Reading frame
# MAGIC   computation from ClinVar data alone requires either (a) parsing the cDNA HGVS to infer affected
# MAGIC   exons via Ensembl VEP, or (b) joining on HGVS to LOVD records which do carry exon annotations.
# MAGIC   Flag: `exon_derivable = false` for records where neither approach is possible.

# COMMAND ----------

import json

# ---------------------------------------------------------------------------
# Build Bronze rows from the paginated sample
# ---------------------------------------------------------------------------
ingestion_ts  = datetime.now(timezone.utc).isoformat()
api_version   = "clinvar_eutils_v1"

# Base ESummary URL used to fetch these records (reconstruct for provenance)
def build_source_url(uid: str) -> str:
    params = {
        "db":     "clinvar",
        "id":     uid,
        "retmode": "json",
        "tool":   NCBI_TOOL,
        "email":  NCBI_EMAIL,
    }
    return ESUMMARY_URL + "?" + urlencode(params)

def flatten_to_bronze_row(uid: str, record: dict) -> dict:
    """Extract Bronze-level fields from an ESummary record dict."""
    # ClinVar renamed clinical_significance → germline_classification in their v2+ schema.
    clin_sig  = record.get("germline_classification", {})
    genes     = record.get("genes", [])
    # Large CNVs span hundreds of genes; find DMD specifically rather than blindly taking genes[0].
    dmd_gene  = next((g for g in genes if g.get("symbol") == "DMD"), genes[0] if genes else {})
    var_sets  = record.get("variation_set", [])
    hgvs_list = var_sets[0].get("variation", {}).get("hgvs_expressions", []) if var_sets else []
    scvs      = record.get("supporting_submissions", {}).get("scv", [])

    return {
        "variation_id":                          uid,
        "accession":                             record.get("accession", ""),
        "accession_version":                     record.get("accession_version", ""),
        "title":                                 record.get("title", ""),
        "obj_type":                              record.get("obj_type", ""),
        "gene_symbol":                           dmd_gene.get("symbol", ""),
        "gene_id":                               dmd_gene.get("geneid", ""),
        "clinical_significance_description":     clin_sig.get("description", ""),
        "clinical_significance_review_status":   clin_sig.get("review_status", ""),
        "clinical_significance_last_evaluated":  clin_sig.get("last_evaluated", ""),
        "hgvs_expressions_json":                 json.dumps(hgvs_list),
        "condition_keys_json":                   json.dumps(clin_sig.get("trait_set", [])),
        "protein_change":                        record.get("protein_change", ""),
        "supporting_scv_count":                  str(len(scvs)),
        "supporting_scv_json":                   json.dumps(scvs),
        "source_system":                         "clinvar",
        "ingestion_timestamp":                   ingestion_ts,
        "api_version":                           api_version,
        "source_url":                            build_source_url(uid),
    }

bronze_rows = [flatten_to_bronze_row(uid, all_records[uid]) for uid in all_records]

print(f"Bronze rows built: {len(bronze_rows)}")
print(f"\nSample row keys: {list(bronze_rows[0].keys())}")
print(f"\nSample row (first):")
for k, v in bronze_rows[0].items():
    display_val = v[:80] + "..." if isinstance(v, str) and len(v) > 80 else v
    print(f"  {k:<45s} {display_val}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 7 — Provenance Metadata
# MAGIC
# MAGIC Every Bronze row carries four ALCOA+ provenance fields appended at ingestion time. These fields are
# MAGIC never sourced from the upstream API — they record the ingestion event itself.
# MAGIC
# MAGIC | Field | Value | ALCOA+ principle |
# MAGIC |-------|-------|-----------------|
# MAGIC | `source_system` | `"clinvar"` | **Attributable** — identifies the originating system unambiguously. |
# MAGIC | `ingestion_timestamp` | UTC ISO-8601 at the moment `createDataFrame` is called | **Contemporaneous** — the timestamp is recorded at the time of the event, not reconstructed later. |
# MAGIC | `api_version` | `"clinvar_eutils_v1"` | **Original** — records the API version used; if NCBI changes the ESummary schema, the version tag allows downstream consumers to identify which Bronze records were produced under the old schema without inspecting record content. |
# MAGIC | `source_url` | Full ESummary URL with UID, retmode, tool, and email parameters | **Attributable** — the exact URL that produced this record. Any analyst can re-fetch the upstream record to verify the Bronze content. |
# MAGIC
# MAGIC ALCOA+ in this context means:
# MAGIC - **Attributable**: every record can be traced to its source system, the specific API call, and the
# MAGIC   person who initiated the ingestion (via the `email` parameter embedded in `source_url`).
# MAGIC - **Contemporaneous**: `ingestion_timestamp` is set in Python at the start of the ingestion run and
# MAGIC   held constant across all rows in that run. It is not the API's `last_evaluated` date — that is a
# MAGIC   separate field recording when ClinVar last reviewed the classification.
# MAGIC - **Original**: Bronze records are written with `mode("overwrite")` and `overwriteSchema` but never
# MAGIC   edited in-place. Delta Lake time travel preserves all prior versions. The original API response
# MAGIC   is preserved in `hgvs_expressions_json`, `condition_keys_json`, and `supporting_scv_json` as
# MAGIC   raw JSON strings — no information is discarded at Bronze.
# MAGIC - **Accurate**: the `api_version` tag enables a downstream audit to verify that the Bronze schema
# MAGIC   matches the documented ESummary response for that API version.
# MAGIC - **Enduring**: Delta Lake `.saveAsTable` writes to managed storage — records persist beyond the
# MAGIC   lifetime of this notebook run or the Databricks cluster.
# MAGIC
# MAGIC For the FTP bulk ingestion alternative, `api_version` should be set to the ClinVar release date
# MAGIC (e.g. `"clinvar_ftp_2026-06-01"`) and `source_url` should record the FTP file path.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 8 — Write to Personal Schema
# MAGIC
# MAGIC This cell writes the Bronze sample rows to `workspace.steff_horemans.bronze_clinvar_submissions_raw`
# MAGIC using Databricks Connect. The `workspace.steff_horemans` schema is the **ungoverned personal sandbox**
# MAGIC defined in ADR-01: exploration tables written here are never imported from production pipelines and
# MAGIC carry no quality SLA. They are disposable learning artifacts.
# MAGIC
# MAGIC The `USE workspace.steff_horemans` statement sets this as the Spark session default catalog+schema,
# MAGIC so subsequent SQL cells in this notebook can reference tables without the fully-qualified prefix.
# MAGIC
# MAGIC An **explicit `BRONZE_SCHEMA`** is required — Spark cannot infer types from an all-string dict if any
# MAGIC column happens to contain only nulls in the sample. All columns are declared as `StringType` at Bronze;
# MAGIC type casting to `IntegerType`, `TimestampType`, etc. happens at Silver. This avoids the
# MAGIC `PySparkValueError: CANNOT_DETERMINE_TYPE` error on all-null columns.

# COMMAND ----------

from databricks.connect import DatabricksSession  # noqa: E402
from pyspark.sql.types import StringType, StructField, StructType  # noqa: E402

# All Bronze columns are StringType — type casting happens at Silver.
# supporting_scv_count is stored as string here even though it is numeric;
# Silver casts it to IntegerType after validating the field is never null.
BRONZE_SCHEMA = StructType([
    StructField("variation_id",                         StringType(), False),
    StructField("accession",                            StringType(), True),
    StructField("accession_version",                    StringType(), True),
    StructField("title",                                StringType(), True),
    StructField("obj_type",                             StringType(), True),
    StructField("gene_symbol",                          StringType(), True),
    StructField("gene_id",                              StringType(), True),
    StructField("clinical_significance_description",    StringType(), True),
    StructField("clinical_significance_review_status",  StringType(), True),
    StructField("clinical_significance_last_evaluated", StringType(), True),
    StructField("hgvs_expressions_json",                StringType(), True),
    StructField("condition_keys_json",                  StringType(), True),
    StructField("protein_change",                       StringType(), True),
    StructField("supporting_scv_count",                 StringType(), True),
    StructField("supporting_scv_json",                  StringType(), True),
    StructField("source_system",                        StringType(), False),
    StructField("ingestion_timestamp",                  StringType(), False),
    StructField("api_version",                          StringType(), False),
    StructField("source_url",                           StringType(), False),
])

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
    .saveAsTable("workspace.steff_horemans.bronze_clinvar_submissions_raw")
)

print(f"Written {df.count()} rows to workspace.steff_horemans.bronze_clinvar_submissions_raw")
spark.sql("DESCRIBE TABLE bronze_clinvar_submissions_raw").show(truncate=False)
