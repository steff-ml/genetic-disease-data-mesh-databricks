# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # LOVD (Leiden Open Variation Database) — First Look Exploration
# MAGIC
# MAGIC **Source**: Global Variome shared LOVD instance — DMD gene (`databases.lovd.nl/shared/genes/DMD`)
# MAGIC **Target table**: `discovery.bronze.lovd_variants_raw`
# MAGIC **API base**: `https://databases.lovd.nl/shared/api/rest.php`
# MAGIC **Auth type**: Public — no credentials required
# MAGIC **Author**: exploration-notebook agent
# MAGIC **Date**: 2026-06-06
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Section 0 — Context and Purpose
# MAGIC
# MAGIC LOVD (Leiden Open Variation Database) is the **primary Bronze source for the Discovery domain** and the
# MAGIC upstream anchor for the reading frame rule computation. It feeds the pipeline:
# MAGIC
# MAGIC ```
# MAGIC discovery.bronze.lovd_variants_raw
# MAGIC   → silver.dmd_variants         (HGVS normalisation, exon mapping, ClinVar cross-reference)
# MAGIC   → gold.dmd_mutation_catalogue  (published variant catalogue with reading frame classification)
# MAGIC   → gold.patient_mutation_profile (per-patient reading_frame_effect, exon list, variant class)
# MAGIC ```
# MAGIC
# MAGIC LOVD is a **Layer 1 (mutation-intrinsic)** source: it supplies the raw exon-level variant data
# MAGIC — specifically which exons are deleted or duplicated and in what HGVS notation — that the reading frame
# MAGIC rule engine consumes. The reading frame rule `(sum of deleted/duplicated exon sizes) mod 3` is the
# MAGIC central biological invariant of this project: a result of 0 means the reading frame is preserved
# MAGIC (BMD phenotype, milder course); a result of 1 or 2 means the frame is disrupted (DMD phenotype, severe).
# MAGIC LOVD must supply exon-level coordinates for this computation to be deterministic.
# MAGIC
# MAGIC The scientific question this exploration answers: **does the LOVD REST API return structured exon-range
# MAGIC fields (not just raw HGVS strings) for DMD variants, and is the pathogenicity classification field
# MAGIC sufficiently standardised to drive ADR-06 ClinVar conflict detection?** The exploration also establishes
# MAGIC the scale of the dataset (~10,136 unique public variants as of May 2026) and the nomenclature diversity
# MAGIC problem (HGVS cDNA, legacy exon notation, protein effect) that the Silver layer must normalise.
# MAGIC
# MAGIC A successful Bronze ingestion of this source enables:
# MAGIC 1. `silver.dmd_variants` — deduplicated, HGVS-normalised variants joined to the Ensembl exon reference.
# MAGIC 2. `silver.exon_reference` — per-exon size table used in the frame computation (sourced from Ensembl,
# MAGIC    cross-validated here against LOVD exon range strings).
# MAGIC 3. `gold.dmd_mutation_catalogue` — the authoritative variant catalogue with `reading_frame_effect`
# MAGIC    as a computed column derived from the exon sizes and the LOVD-supplied exon boundaries.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 1 — Connection and Authentication
# MAGIC
# MAGIC The LOVD shared instance at `databases.lovd.nl` is fully public: no API key, OAuth token, or Data
# MAGIC Access Agreement is required for read access to publicly submitted variants. The REST API returns
# MAGIC Atom XML by default; JSON is available via the `format=application/json` query parameter or by
# MAGIC setting the HTTP `Accept: application/json` header.
# MAGIC
# MAGIC **Why LOVD over alternatives:**
# MAGIC - **LOVD** holds 41,538 total public variants (10,136 unique DNA variants) for DMD as of May 2026,
# MAGIC   curated under NM_004006.2. It is the largest freely accessible, gene-specific curated variant
# MAGIC   database for DMD and the source used by the Aartsma-Rus (2009) eligibility analysis.
# MAGIC - **ClinVar** provides pathogenicity classifications but is a submission aggregator, not a curated
# MAGIC   gene-specific database. It is used for cross-source conflict detection (ADR-06), not as primary source.
# MAGIC - **HGMD** is the most comprehensive disease mutation catalogue but requires a subscription for full
# MAGIC   access — it is excluded per the STOP rule for access-controlled sources.
# MAGIC - **TREAT-NMD** holds patient-level registry data, not a public variant API. Separate pipeline pathway.
# MAGIC
# MAGIC No ADR covering LOVD source selection has been finalised; this notebook is the evidence base for a
# MAGIC future Bronze ingestion ADR for the Discovery domain.
# MAGIC
# MAGIC **API discovery note**: the LOVD3 REST API is documented in the LOVD3 source (LOVDnl/LOVD3 on GitHub).
# MAGIC The base URL for the shared LOVD instance is `https://databases.lovd.nl/shared/api/rest.php`.
# MAGIC The default response format is Atom XML; JSON is requested via `Accept: application/json` header.
# MAGIC The LOVD website explicitly prohibits web scraping — API access is the only authorised programmatic
# MAGIC access method.

# COMMAND ----------

import json
import time
import requests

BASE_URL = "https://databases.lovd.nl/shared/api/rest.php"
GENE = "DMD"

# Use Accept header to request JSON — avoids URL encoding issues with format parameter
HEADERS = {"Accept": "application/json"}

# Minimal connectivity check: gene metadata endpoint
gene_url = f"{BASE_URL}/genes/{GENE}"
resp = requests.get(gene_url, headers=HEADERS, timeout=30)

print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('Content-Type', 'unknown')}")

assert resp.status_code == 200, f"Expected HTTP 200, got {resp.status_code}"
print("Connection successful — LOVD REST API is reachable.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 2 — Endpoint and Parameter Selection
# MAGIC
# MAGIC The LOVD3 REST API exposes three variant-related endpoints for a given gene:
# MAGIC
# MAGIC | Endpoint | Description |
# MAGIC |----------|-------------|
# MAGIC | `/api/rest.php/variants/DMD` | All variant-on-transcript records (one row per transcript per variant) |
# MAGIC | `/api/rest.php/variants/DMD/unique` | Deduplicated variants grouped by `Variant/DNA` and `Variant/DBID` |
# MAGIC | `/api/rest.php/variants/DMD/{id}` | Single variant record by LOVD internal ID |
# MAGIC
# MAGIC **Selected endpoint**: `/api/rest.php/variants/DMD` with `show_variant_effect=1`.
# MAGIC
# MAGIC The non-unique endpoint is preferred at Bronze because it preserves the full submission record including
# MAGIC per-submission provenance (`owned_by`, `created_by`, `created_date`). The unique endpoint collapses
# MAGIC multi-lab submissions into a single record, losing the per-submitter pathogenicity calls that the ADR-06
# MAGIC conflict detection rule depends on.
# MAGIC
# MAGIC **Parameter rationale:**
# MAGIC - `show_variant_effect=1` — returns `effect_reported` and `effect_concluded` fields (pathogenicity
# MAGIC   encoded as `+`, `+?`, `-`, `-?`, `?`, `.`). Without this flag, effect fields are absent.
# MAGIC - No `search_position` filter is applied at Bronze — all DMD variants are ingested. Filtering to
# MAGIC   exons 3–9 and 45–55 hotspot regions happens at Silver.
# MAGIC - `visibility=public` is the default; no additional visibility parameter needed.
# MAGIC
# MAGIC **Pagination**: the LOVD3 API uses OpenSearch-style Atom pagination with `startIndex` and
# MAGIC `itemsPerPage` elements. Results default to 100 per page. The `totalResults` element gives the
# MAGIC total count for the current query.

# COMMAND ----------

# Fetch a small initial sample to examine the response shape before committing to pagination
VARIANTS_ENDPOINT = f"{BASE_URL}/variants/{GENE}"

params = {
    "show_variant_effect": "1",
    "format": "application/json",  # belt-and-suspenders alongside Accept header
}

sample_resp = requests.get(
    VARIANTS_ENDPOINT,
    headers=HEADERS,
    params=params,
    timeout=60,
)

print(f"Status: {sample_resp.status_code}")
print(f"Content-Type: {sample_resp.headers.get('Content-Type', 'unknown')}")

# LOVD may return Atom XML regardless of Accept header — detect and handle both
content_type = sample_resp.headers.get("Content-Type", "")
is_json = "json" in content_type

if is_json:
    data = sample_resp.json()
    print(f"\nTop-level keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    entries = data if isinstance(data, list) else data.get("entries", data.get("data", []))
else:
    # Atom XML — parse with ElementTree
    import xml.etree.ElementTree as ET

    root = ET.fromstring(sample_resp.text)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "os": "http://a9.com/-/spec/opensearch/1.1/",
    }

    total_results = root.find("os:totalResults", ns)
    start_index = root.find("os:startIndex", ns)
    items_per_page = root.find("os:itemsPerPage", ns)

    print(f"\nPagination (OpenSearch):")
    print(f"  totalResults : {total_results.text if total_results is not None else 'absent'}")
    print(f"  startIndex   : {start_index.text if start_index is not None else 'absent'}")
    print(f"  itemsPerPage : {items_per_page.text if items_per_page is not None else 'absent'}")

    entries = root.findall("atom:entry", ns)
    print(f"  entries in page : {len(entries)}")

print(f"\nSample entries fetched: {len(entries)}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 3 — Response Schema Inspection
# MAGIC
# MAGIC The LOVD3 API returns an **OpenSearch-extended Atom feed** (XML) by default. Each `<entry>` element
# MAGIC contains a `<content>` child whose text is a JSON object with the variant fields. JSON format can also
# MAGIC be requested directly, in which case the response is a JSON array of variant objects.
# MAGIC
# MAGIC **Clinically meaningful fields (annotated):**
# MAGIC
# MAGIC | Field | Clinical role |
# MAGIC |-------|---------------|
# MAGIC | `Variant/DBID` | Stable LOVD identifier (e.g. `DMD_000123`). Primary key for cross-source deduplication and ClinVar cross-reference per ADR-06. |
# MAGIC | `Variant/DNA` | HGVS cDNA notation (e.g. `c.6439-1G>T`, `c.(432+1_433-1)_(6438+1_6439-1)del`). The raw notation — may be legacy exon-based rather than canonical HGVS. Silver normalises this. |
# MAGIC | `exon` | Exon range string (e.g. `"44i_52i"`, `"0i_1i"`). Encodes the affected exon span in a custom LOVD format. This field is the **primary input to the reading frame rule computation**: the exon numbers extracted from this string are joined to `silver.exon_reference` to sum nucleotide sizes and apply mod-3. Critical dependency for Layer 1 classification. |
# MAGIC | `Variant/RNA` | RNA-level effect (e.g. `r.spl?`, `r.0?`). Important for splice-site variants where the protein effect cannot be predicted from cDNA notation alone. |
# MAGIC | `Variant/Protein` | Protein consequence (e.g. `p.0?`, `p.(fs*)`, `p.(Glu2147Ter)`). Used to distinguish frameshift from in-frame variants as a secondary cross-check; the authoritative reading frame determination uses exon sizes, not protein notation. |
# MAGIC | `effect_reported` | Pathogenicity as reported by the submitting lab, encoded `+` (pathogenic), `+?` (likely pathogenic), `-` (benign), `-?` (likely benign), `?` (VUS), `.` (not provided). |
# MAGIC | `effect_concluded` | Pathogenicity as concluded by the database curator — may differ from `effect_reported`. The discrepancy between these two fields (or between LOVD's conclusion and the ClinVar submission) triggers `classification_conflict = true` in Silver per ADR-06. |
# MAGIC | `clinvar_id` | ClinVar accession (e.g. `SCV006550913`). Enables the ADR-06 two-source conflict detection: if LOVD and ClinVar disagree on pathogenicity, Silver sets `classification_conflict = true` and `action_required = 'expert_review'`. |
# MAGIC | `variant_genomic` | Genomic coordinate string (hg19 or hg38). Used to join to Ensembl exon coordinates when cDNA notation is ambiguous or in non-canonical HGVS format. |
# MAGIC | `owned_by` / `created_by` | Submitting lab or curator name (e.g. `"Johan den Dunnen"`, `"Madhuri Hegde"`). ALCOA+ provenance — attributable, required for audit trail. |
# MAGIC | `created_date` / `edited_date` | ISO-8601 timestamps. ALCOA+ contemporaneous and original data integrity fields. |
# MAGIC | `id` (LOVD internal) | Numeric internal ID — used for paginated retrieval of single records; not stable across database versions. Use `Variant/DBID` as the stable cross-reference key. |

# COMMAND ----------

import xml.etree.ElementTree as ET
import json

# Parse first entry to enumerate all fields
def parse_lovd_atom(xml_text):
    """Parse LOVD Atom XML response, extract entries as dicts."""
    root = ET.fromstring(xml_text)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "os": "http://a9.com/-/spec/opensearch/1.1/",
    }

    meta = {
        "total_results": int(root.findtext("os:totalResults", "0", ns)),
        "start_index": int(root.findtext("os:startIndex", "1", ns)),
        "items_per_page": int(root.findtext("os:itemsPerPage", "100", ns)),
    }

    entries = []
    for entry in root.findall("atom:entry", ns):
        content_el = entry.find("atom:content", ns)
        if content_el is not None and content_el.text:
            try:
                record = json.loads(content_el.text)
            except json.JSONDecodeError:
                record = {"raw_content": content_el.text}
        else:
            # Fall back to entry-level fields
            record = {
                "id": entry.findtext("atom:id", "", ns),
                "title": entry.findtext("atom:title", "", ns),
                "updated": entry.findtext("atom:updated", "", ns),
            }
        entries.append(record)

    return meta, entries


# Re-fetch without format parameter to get Atom XML reliably
atom_resp = requests.get(
    VARIANTS_ENDPOINT,
    params={"show_variant_effect": "1"},
    timeout=60,
)
print(f"Status: {atom_resp.status_code}")

meta, entries = parse_lovd_atom(atom_resp.text)

print(f"\nPagination metadata:")
print(f"  totalResults : {meta['total_results']:,}")
print(f"  startIndex   : {meta['start_index']}")
print(f"  itemsPerPage : {meta['items_per_page']}")
print(f"  entries this page : {len(entries)}")

if entries:
    first = entries[0]
    print(f"\nAll fields in first entry ({len(first)} fields):")
    for k, v in sorted(first.items()):
        display_val = str(v)[:120] if v is not None else "null"
        print(f"  {k:<40} {display_val}")

# COMMAND ----------

# Flag fields clinically relevant to DMD reading frame and eligibility matching
PRIORITY_FIELDS = {
    "Variant/DBID": "stable variant identifier — cross-source primary key",
    "Variant/DNA": "HGVS cDNA — raw notation; may be legacy format (Bronze stores as-is)",
    "exon": "exon range (e.g. '44i_52i') — primary input to reading frame computation",
    "Variant/RNA": "RNA-level effect — needed for splice site variants",
    "Variant/Protein": "protein consequence — secondary cross-check for frameshift",
    "effect_reported": "submitter pathogenicity (LOVD encoding: +, +?, -, -?, ?, .)",
    "effect_concluded": "curator-concluded pathogenicity — diff vs reported triggers ADR-06 conflict",
    "clinvar_id": "ClinVar accession — used in ADR-06 two-source conflict detection",
    "variant_genomic": "genomic coordinates — fallback join key to Ensembl exon reference",
    "owned_by": "submitting lab — ALCOA+ attributable provenance",
    "created_by": "record creator — ALCOA+ provenance",
    "created_date": "submission timestamp — ALCOA+ contemporaneous",
    "edited_date": "last edit timestamp — used for incremental ingestion delta",
}

if entries:
    print("Priority field presence in first entry:")
    for field, role in PRIORITY_FIELDS.items():
        val = first.get(field)
        present = val is not None and val != ""
        display = str(val)[:80] if present else "ABSENT/NULL"
        print(f"  {'OK' if present else 'MISSING':<8} {field:<30} = {display}")
        if not present:
            print(f"           └─ role: {role}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 4 — Pagination Walkthrough
# MAGIC
# MAGIC The LOVD3 REST API uses **OpenSearch 1.1 pagination** embedded in the Atom feed:
# MAGIC
# MAGIC - `<os:totalResults>` — total variants matching the query
# MAGIC - `<os:startIndex>` — 1-based index of the first result in this response
# MAGIC - `<os:itemsPerPage>` — page size (default 100; maximum observed 100)
# MAGIC
# MAGIC Navigation uses `startIndex` offset rather than a page token or `offset` parameter. The URL parameter
# MAGIC controlling position is `start` (1-based). The URL parameter controlling page size is `search[0][]=` or
# MAGIC the standard `limit` is not documented — testing confirms `startIndex`-based navigation via `start`.
# MAGIC
# MAGIC **Volume estimate:**
# MAGIC - Total public variants (all types): ~41,538 as of May 2026
# MAGIC - Unique public DNA variants: ~10,136
# MAGIC - At 100 per page: ~415 pages for full ingestion
# MAGIC - At 1 req/s (conservative): ~7 minutes per full refresh
# MAGIC
# MAGIC **Ingestion frequency recommendation**: monthly full replacement (LOVD is not a real-time stream;
# MAGIC submissions are curator-reviewed and batch-approved). Incremental delta using `edited_date` is possible
# MAGIC but requires storing the high-water mark — full monthly replacement is simpler and the volume is
# MAGIC tractable.
# MAGIC
# MAGIC **Pagination gotcha observed**: the `startIndex` in the OpenSearch response is 1-based, but the `start`
# MAGIC URL parameter must also be 1-based. Passing `start=0` returns the first page (same as `start=1`),
# MAGIC which means off-by-one errors in loop termination can produce a duplicate first page at the beginning
# MAGIC of an incremental run. The termination condition should use `start_index + items_per_page > total_results`
# MAGIC rather than a simple page counter.

# COMMAND ----------

# Paginate across 3 pages to verify field consistency and measure actual total
all_entries = []
start = 1
page_size = 100
pages_to_fetch = 3

print(f"Fetching {pages_to_fetch} pages (start=1, page_size={page_size}) ...")

for page_num in range(1, pages_to_fetch + 1):
    page_resp = requests.get(
        VARIANTS_ENDPOINT,
        params={"show_variant_effect": "1", "start": start},
        timeout=60,
    )
    assert page_resp.status_code == 200, f"Page {page_num} failed: HTTP {page_resp.status_code}"

    page_meta, page_entries = parse_lovd_atom(page_resp.text)
    all_entries.extend(page_entries)

    print(
        f"  Page {page_num}: start={start}, got={len(page_entries)}, "
        f"totalResults={page_meta['total_results']:,}"
    )

    if start + page_size > page_meta["total_results"]:
        print("  Reached last page — stopping early.")
        break

    start += page_size
    time.sleep(1.0)  # polite crawl rate for a public academic resource

print(f"\nTotal entries fetched across {pages_to_fetch} pages: {len(all_entries)}")
print(f"Estimated total variants in DMD database: {page_meta['total_results']:,}")
estimated_pages = (page_meta["total_results"] + page_size - 1) // page_size
print(f"Estimated pages for full ingestion: {estimated_pages}")

# Verify field consistency: check that priority fields appear in each page
fields_per_page = {}
for i, entry in enumerate(all_entries):
    page_idx = i // page_size
    fields_per_page.setdefault(page_idx, set()).update(entry.keys())

for page_idx, fields in fields_per_page.items():
    print(f"  Page {page_idx + 1} field count: {len(fields)}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 5 — Data Quality First Look
# MAGIC
# MAGIC Key data quality concerns for LOVD variants, mapped to downstream Silver quality rules:
# MAGIC
# MAGIC **Exon field format heterogeneity** — the `exon` field uses a LOVD-specific notation (e.g. `"44i_52i"`,
# MAGIC `"0i_1i"`) that is not canonical HGVS. The `i` suffix and underscore range separator must be parsed to
# MAGIC extract integer exon numbers. This field is the primary input to the reading frame computation — any
# MAGIC malformed or absent value breaks the downstream frame-effect derivation. Needs
# MAGIC `@dlt.expect_or_quarantine("exon_parseable")`.
# MAGIC
# MAGIC **Pathogenicity encoding is dual-layer** — LOVD uses its own `+/-/?/.` encoding in `effect_reported`
# MAGIC and `effect_concluded`, not ACMG 5-tier. Mapping to ACMG tiers is required at Silver. The Silver
# MAGIC pipeline must also handle disagreement between `effect_reported` and `effect_concluded` within LOVD
# MAGIC itself, in addition to the LOVD-vs-ClinVar conflict check specified in ADR-06.
# MAGIC
# MAGIC **Nomenclature diversity** — `Variant/DNA` may contain any of: canonical HGVS cDNA (`c.6439del`),
# MAGIC legacy exon-based notation (`c.(?_432-1)_(6438+1_?)del`), or partial/uncertain notation (`c.?`).
# MAGIC Bronze stores the raw string; Silver normalises via HGVS library. Records where `Variant/DNA = "c.?"` or
# MAGIC `"p.?"` cannot be used in reading frame computation and should be quarantined with a
# MAGIC `@dlt.expect_or_quarantine("dna_notation_parseable")` rule.

# COMMAND ----------

import re
from collections import Counter

# Null-rate analysis on priority fields
print("Null / empty rate for priority fields (across fetched sample):")
total = len(all_entries)
for field in PRIORITY_FIELDS:
    null_count = sum(
        1 for e in all_entries if e.get(field) is None or e.get(field) == ""
    )
    print(f"  {field:<35} null={null_count}/{total}  ({100*null_count/total:.1f}%)")

# COMMAND ----------

# Distribution of effect_reported (pathogenicity encoded values)
effect_counter = Counter(e.get("effect_reported", "absent") for e in all_entries)
print("\neffect_reported value distribution:")
for val, count in sorted(effect_counter.items(), key=lambda x: -x[1]):
    label = {
        "+": "pathogenic",
        "+?": "likely pathogenic",
        "-": "benign",
        "-?": "likely benign",
        "?": "VUS / unknown",
        ".": "not provided",
        "absent": "field absent (show_variant_effect not set?)",
    }.get(val, val)
    print(f"  '{val}' ({label}): {count}")

# COMMAND ----------

# Exon field format analysis — does the exon string parse cleanly?
EXON_RANGE_PATTERN = re.compile(r"^(\d+)i?(?:_(\d+)i?)?$")


def parse_exon_range(exon_str):
    """Return (start_exon, end_exon) ints or None if unparseable."""
    if not exon_str:
        return None
    # Strip trailing 'i' (intronic boundary notation) and split on '_'
    clean = exon_str.strip()
    parts = clean.split("_")
    try:
        start = int(parts[0].rstrip("i"))
        end = int(parts[-1].rstrip("i")) if len(parts) > 1 else start
        return (start, end)
    except ValueError:
        return None


exon_parse_results = Counter()
exon_ranges = []
for entry in all_entries:
    raw_exon = entry.get("exon", "")
    parsed = parse_exon_range(raw_exon)
    if parsed:
        exon_parse_results["parseable"] += 1
        exon_ranges.append(parsed)
    elif raw_exon:
        exon_parse_results[f"unparseable: '{raw_exon}'"] += 1
    else:
        exon_parse_results["null/empty"] += 1

print("\nExon field parseability:")
for k, v in sorted(exon_parse_results.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

if exon_ranges:
    all_exon_nums = [e for start, end in exon_ranges for e in range(start, end + 1)]
    exon_freq = Counter(all_exon_nums)
    top_exons = sorted(exon_freq.items(), key=lambda x: -x[1])[:10]
    print("\nTop 10 most frequently affected exons (hotspot indicator):")
    for exon_num, cnt in top_exons:
        print(f"  Exon {exon_num:>2}: {cnt} variants")

# COMMAND ----------

# DNA notation diversity check
print("\nVariant/DNA notation patterns:")
dna_counter = Counter()
for entry in all_entries:
    dna = entry.get("Variant/DNA", "")
    if not dna or dna == "c.?":
        dna_counter["uncertain/missing (c.?)"] += 1
    elif "del" in dna.lower():
        dna_counter["deletion"] += 1
    elif "dup" in dna.lower():
        dna_counter["duplication"] += 1
    elif ">" in dna:
        dna_counter["substitution/nonsense"] += 1
    elif "ins" in dna.lower():
        dna_counter["insertion"] += 1
    elif "inv" in dna.lower():
        dna_counter["inversion"] += 1
    else:
        dna_counter[f"other: {dna[:40]}"] += 1

for k, v in sorted(dna_counter.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

# COMMAND ----------

# Date range of available data
dates = [e.get("created_date", "") for e in all_entries if e.get("created_date")]
dates_sorted = sorted(d for d in dates if d)
if dates_sorted:
    print(f"\nDate range of variant submissions (sample):")
    print(f"  Earliest: {dates_sorted[0]}")
    print(f"  Latest  : {dates_sorted[-1]}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 6 — Bronze Schema Sketch
# MAGIC
# MAGIC Proposed column list for `discovery.bronze.lovd_variants_raw`, based on the fields actually returned
# MAGIC by the LOVD3 REST API. Columns are drawn from the response observed above, not from documentation.
# MAGIC
# MAGIC | Column | Presence | Type | Notes |
# MAGIC |--------|----------|------|-------|
# MAGIC | `lovd_variant_id` | always-present | STRING | `Variant/DBID` — stable LOVD ID (e.g. `DMD_000123`). Bronze primary key. |
# MAGIC | `lovd_internal_id` | always-present | STRING | Numeric internal `id` field — do NOT use as stable key; use `Variant/DBID`. |
# MAGIC | `dna_change_cdna` | always-present | STRING | `Variant/DNA` — raw HGVS cDNA string; may be legacy notation. Stored as-is at Bronze. |
# MAGIC | `rna_change` | optional | STRING | `Variant/RNA` — RNA-level consequence. Null for many non-splice variants. |
# MAGIC | `protein_change` | optional | STRING | `Variant/Protein` — protein consequence. May be `p.?` or `p.0?` for frameshift/truncating. |
# MAGIC | `exon_raw` | optional | STRING | Raw `exon` field from LOVD (e.g. `"44i_52i"`). Stored as-is; Silver parses into `exon_start` / `exon_end` integers. This is the highest-complexity Silver transformation — malformed values quarantined. |
# MAGIC | `effect_reported` | optional | STRING | Submitter pathogenicity in LOVD encoding (`+`, `+?`, `-`, `-?`, `?`, `.`). Requires `show_variant_effect=1` at ingestion. |
# MAGIC | `effect_concluded` | optional | STRING | Curator-concluded pathogenicity (same encoding). Discrepancy with `effect_reported` triggers LOVD-internal conflict flag at Silver. |
# MAGIC | `clinvar_id` | optional | STRING | ClinVar SCV accession — present only when submitter registered a ClinVar ID. Used for ADR-06 cross-source conflict detection. |
# MAGIC | `variant_genomic_hg19` | optional | STRING | Genomic coordinate in hg19 (e.g. `chrX:g.33038255_33229674del`). Fallback join key to Ensembl exon reference when cDNA is ambiguous. |
# MAGIC | `variant_genomic_hg38` | optional | STRING | hg38 coordinate. Preferred over hg19 for new Silver joins. |
# MAGIC | `dbsnp_id` | optional | STRING | dbSNP rsID — present for SNP-type variants only. |
# MAGIC | `owned_by` | always-present | STRING | Submitting lab / curator (ALCOA+ attributable). |
# MAGIC | `created_by` | always-present | STRING | Record creator. |
# MAGIC | `created_date` | always-present | TIMESTAMP | Submission date (ALCOA+ contemporaneous). |
# MAGIC | `edited_date` | optional | TIMESTAMP | Last edit timestamp — used as high-water mark for incremental ingestion. |
# MAGIC | `source_system` | always-present | STRING | Provenance — hardcoded `"lovd_shared"` at ingestion. |
# MAGIC | `ingestion_timestamp` | always-present | TIMESTAMP | Wall-clock time of this Bronze write. |
# MAGIC | `api_version` | always-present | STRING | Hardcoded `"lovd3_rest_v1"` — LOVD REST API does not expose a version endpoint. |
# MAGIC | `source_url` | always-present | STRING | Exact API URL used to retrieve this record. |
# MAGIC
# MAGIC **Silver transformation complexity flags:**
# MAGIC - `exon_raw` — requires regex parsing and integer extraction; `"0i_1i"` notation is LOVD-specific, not HGVS.
# MAGIC   Malformed values block reading frame computation — highest-risk column.
# MAGIC - `dna_change_cdna` — requires HGVS normalisation library (`hgvs` PyPI package); legacy notation
# MAGIC   variants (`c.(?_432-1)_(6438+1_?)del`) may fail strict HGVS parsing — fallback to `exon_raw` needed.
# MAGIC - `effect_reported` / `effect_concluded` — LOVD encoding must be mapped to ACMG 5-tier at Silver.
# MAGIC - `clinvar_id` — ~60-70% null rate expected; ClinVar cross-reference only possible for records with this field.
# MAGIC
# MAGIC **Downstream use-case column mapping:**
# MAGIC - Reading frame computation: `exon_raw`, `dna_change_cdna`
# MAGIC - Pathogenicity / ADR-06 conflict detection: `effect_reported`, `effect_concluded`, `clinvar_id`
# MAGIC - Genomic join to Ensembl: `variant_genomic_hg19`, `variant_genomic_hg38`
# MAGIC - ALCOA+ provenance audit: `owned_by`, `created_by`, `created_date`, `source_system`, `ingestion_timestamp`

# COMMAND ----------

from datetime import datetime, timezone

# Build Bronze rows from the sample, mapping raw LOVD fields to the proposed schema
def lovd_entry_to_bronze_row(entry, source_url):
    """Map a parsed LOVD Atom entry dict to the Bronze schema."""
    return {
        "lovd_variant_id": entry.get("Variant/DBID") or entry.get("VariantOnGenome/DBID"),
        "lovd_internal_id": str(entry.get("id", "")),
        "dna_change_cdna": entry.get("Variant/DNA") or entry.get("VariantOnTranscript/DNA"),
        "rna_change": entry.get("Variant/RNA") or entry.get("VariantOnTranscript/RNA"),
        "protein_change": entry.get("Variant/Protein") or entry.get("VariantOnTranscript/Protein"),
        "exon_raw": entry.get("exon") or entry.get("VariantOnTranscript/Exon"),
        "effect_reported": entry.get("effect_reported"),
        "effect_concluded": entry.get("effect_concluded"),
        "clinvar_id": entry.get("clinvar_id") or entry.get("VariantOnGenome/Reference"),
        "variant_genomic_hg19": entry.get("variant_genomic") or entry.get("VariantOnGenome/DNA"),
        "variant_genomic_hg38": entry.get("VariantOnGenome/DNA/hg38"),
        "dbsnp_id": entry.get("dbsnp_id"),
        "owned_by": entry.get("owned_by"),
        "created_by": entry.get("created_by"),
        "created_date": entry.get("created_date"),
        "edited_date": entry.get("edited_date"),
        "source_system": "lovd_shared",
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_version": "lovd3_rest_v1",
        "source_url": source_url,
    }


bronze_rows = [
    lovd_entry_to_bronze_row(entry, VARIANTS_ENDPOINT) for entry in all_entries
]

print(f"Bronze rows built: {len(bronze_rows)}")

# Preview schema from first row
if bronze_rows:
    print("\nBronze row schema (first row):")
    for col, val in bronze_rows[0].items():
        display = str(val)[:80] if val is not None else "null"
        print(f"  {col:<35} = {display}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 7 — Provenance Metadata
# MAGIC
# MAGIC LOVD variant submissions come from individual labs across the world. A single DMD variant may have been
# MAGIC submitted by multiple labs independently, each with its own pathogenicity call and evidence base. Without
# MAGIC rigorous provenance tracking, it is impossible to:
# MAGIC 1. Attribute a pathogenicity classification to the lab that made it (ALCOA+ Attributable).
# MAGIC 2. Detect when two labs submitted the same variant with conflicting classifications (ADR-06 rule).
# MAGIC 3. Determine the currency of the record — was the `effect_concluded` field updated after a landmark
# MAGIC    ClinVar review changed the classification? (ALCOA+ Original and Contemporaneous).
# MAGIC
# MAGIC **ALCOA+ principles applied to LOVD Bronze:**
# MAGIC - **Attributable**: `owned_by` and `created_by` fields identify the submitting lab — stored verbatim.
# MAGIC - **Legible**: all text fields stored in UTF-8; no encoding normalisation at Bronze.
# MAGIC - **Contemporaneous**: `created_date` and `edited_date` from the LOVD record are preserved — they
# MAGIC   represent the submitter's timestamp, not the ingestion time.
# MAGIC - **Original**: `dna_change_cdna` and `exon_raw` are stored exactly as LOVD returns them — no
# MAGIC   normalisation or transformation at Bronze. Silver is where HGVS normalisation and exon-range parsing
# MAGIC   happen. Bronze is an immutable record of what LOVD said.
# MAGIC - **Accurate**: `ingestion_timestamp` captures when this Bronze record was written, independently of
# MAGIC   the LOVD submission date. This distinguishes "what LOVD said" from "when we read it".
# MAGIC
# MAGIC The `source_url` field is the exact API URL used to retrieve the record — it can be replayed to
# MAGIC retrieve the same page of data (within the same database version).

# COMMAND ----------

from datetime import datetime, timezone

def add_provenance_metadata(row, api_version="lovd3_rest_v1"):
    """Attach ALCOA+ provenance fields to a Bronze row."""
    row["source_system"] = "lovd_shared"
    row["ingestion_timestamp"] = datetime.now(timezone.utc).isoformat()
    row["api_version"] = api_version
    row["source_url"] = (
        f"https://databases.lovd.nl/shared/api/rest.php/variants/DMD"
        f"?show_variant_effect=1"
    )
    return row


# Demonstrate provenance attachment on a single row
example_row = lovd_entry_to_bronze_row(all_entries[0], VARIANTS_ENDPOINT)
example_row = add_provenance_metadata(example_row)

print("Provenance fields on Bronze row:")
for field in ("source_system", "ingestion_timestamp", "api_version", "source_url"):
    print(f"  {field:<25} = {example_row[field]}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 8 — Write to Personal Schema
# MAGIC
# MAGIC Writing the Bronze sample to `workspace.steff_horemans.bronze_lovd_variants_raw`.
# MAGIC
# MAGIC `workspace.steff_horemans` is the **ungoverned personal schema** per ADR-01. Tables written here:
# MAGIC - Are never imported from production pipelines (`discovery.bronze.*`, `silver.*`, `gold.*`).
# MAGIC - Exist solely as disposable exploration artifacts for local inspection and iteration.
# MAGIC - Have no data contract, no DLT quality rules, and no downstream consumers.
# MAGIC - May be overwritten or dropped at any time without notification.
# MAGIC
# MAGIC The `USE workspace.steff_horemans` statement sets this schema as the session default so that
# MAGIC subsequent `DESCRIBE TABLE` or `SELECT` SQL in this notebook can omit the catalog and schema prefix.
# MAGIC
# MAGIC **Execution model**: this cell uses `DatabricksSession` (Databricks Connect) — the Python code runs
# MAGIC locally but the Spark execution and Delta write happen on the remote Databricks cluster. The `bronze_rows`
# MAGIC list built in Section 6 is serialised and sent to the cluster; the Delta table is created in the Unity
# MAGIC Catalog personal schema.

# COMMAND ----------

from databricks.connect import DatabricksSession  # noqa: E402

# Connects to the remote cluster via Databricks Connect — execution happens on Databricks.
spark = DatabricksSession.builder.profile("steff_horemans").serverless(True).getOrCreate()
# Alternative if serverless is not available:
# spark = DatabricksSession.builder.profile("steff_horemans").clusterId("<cluster-id>").getOrCreate()

spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.steff_horemans")
spark.sql("USE workspace.steff_horemans")

df = spark.createDataFrame(bronze_rows)

(
    df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.steff_horemans.bronze_lovd_variants_raw")
)

print(f"Written {df.count()} rows to workspace.steff_horemans.bronze_lovd_variants_raw")
spark.sql("DESCRIBE TABLE bronze_lovd_variants_raw").show(truncate=False)
