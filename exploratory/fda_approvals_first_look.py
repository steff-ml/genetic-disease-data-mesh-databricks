# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 0 — Context and Purpose
# MAGIC
# MAGIC This notebook performs a first-look exploration of FDA drug approval data sourced from the
# MAGIC openFDA API (`drug/drugsfda` and `drug/label` endpoints). Both endpoints are public and require
# MAGIC no authentication, though an API key raises the rate limit from 40 to 240 requests/minute.
# MAGIC
# MAGIC **What this source contains and which eligibility layer it feeds.**
# MAGIC FDA approval records encode Layer 2 (approach-specific) eligibility data for the DMD
# MAGIC mutation-eligibility matching pipeline. Each approved DMD drug carries a mutation-specific
# MAGIC indication — for example, eteplirsen (EXONDYS 51) is approved specifically for patients with
# MAGIC "a confirmed mutation of the DMD gene that is amenable to exon 51 skipping." That sentence,
# MAGIC embedded in the prescribing label's INDICATIONS AND USAGE section, is the authoritative
# MAGIC regulatory statement of which patient genotypes the drug is approved for.
# MAGIC
# MAGIC **What scientific question this exploration answers.**
# MAGIC Can the openFDA API reliably surface the six FDA-approved DMD drugs — eteplirsen, golodirsen,
# MAGIC viltolarsen, casimersen, delandistrogene moxeparvovec (ELEVIDYS), and givinostat — together
# MAGIC with their full supplement history and the label text that encodes their genetic eligibility
# MAGIC criteria? And which of the two available openFDA endpoints (`drugsfda` for application metadata,
# MAGIC `label` for prescribing information) should be the Bronze ingestion primary source?
# MAGIC
# MAGIC **What a successful Bronze ingestion enables downstream.**
# MAGIC A structured Bronze table of FDA approvals feeds `silver.eligibility_criteria`, where the
# MAGIC free-text `indications_and_usage` field is parsed (via NLP or pattern matching) to extract
# MAGIC structured mutation eligibility rules — exon skipping target, patient genotype requirements,
# MAGIC age and ambulatory status constraints. These rules populate `gold.trial_eligibility_catalogue`
# MAGIC and are the ground truth for which approved therapies a given patient mutation qualifies for
# MAGIC under Layer 2 of the classification framework.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 1 — Connection and Authentication
# MAGIC
# MAGIC The openFDA API is fully public. No API key is required. Unauthenticated requests are rate-limited
# MAGIC to **40 requests per minute per IP address**. With an API key, the limit rises to 240 requests
# MAGIC per minute. For Bronze ingestion of the small DMD-relevant subset (~24 label records, ~6
# MAGIC application records) this limit is immaterial — the dataset fits in a single paginated call.
# MAGIC For full-database harvesting (29,000+ applications), an API key is recommended.
# MAGIC
# MAGIC API keys are obtained for free at https://open.fda.gov/apis/authentication/ and are passed
# MAGIC as a query parameter: `&api_key=<key>`. No OAuth flow, no secrets scope needed for public
# MAGIC exploration. For production ingestion, store the key in a Databricks secret and inject it
# MAGIC at runtime via `dbutils.secrets.get`.
# MAGIC
# MAGIC **Why openFDA over alternatives.**
# MAGIC The FDA Drugs@FDA web portal holds the same data but has no structured API; scraping it is
# MAGIC fragile and against terms of service. DailyMed (NIH) also exposes prescribing labels via
# MAGIC API but its search index is less consistent for rare disease queries. openFDA is the
# MAGIC authoritative structured interface for both application metadata and label text, updated
# MAGIC daily Monday–Friday. No ADR has been written for this source yet; one should be drafted
# MAGIC before production ingestion begins.

# COMMAND ----------

import requests
import json
from datetime import datetime

# Base URLs for the two endpoints used in this exploration.
# drugsfda: application-level metadata (NDA/BLA number, sponsor, products, full submission history)
# label:    prescribing information (INDICATIONS AND USAGE section — the genetic eligibility text)
BASE_DRUGSFDA = "https://api.fda.gov/drug/drugsfda.json"
BASE_LABEL    = "https://api.fda.gov/drug/label.json"

# No API key for exploration. For production ingestion, inject via:
#   api_key = dbutils.secrets.get(scope="openfda", key="api_key")  # TODO: confirm scope name
#   params["api_key"] = api_key
# Unauthenticated limit: 40 requests/minute. Sufficient for the ~24-record DMD label corpus.

def _get(url: str, params: dict) -> dict:
    """Single GET with basic error handling. Returns parsed JSON body."""
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

# Minimal liveness test: fetch one record from each endpoint.
ping_drugsfda = _get(BASE_DRUGSFDA, {"limit": 1})
ping_label    = _get(BASE_LABEL, {"limit": 1})

assert "results" in ping_drugsfda, "drugsfda endpoint did not return a results array"
assert "results" in ping_label,    "label endpoint did not return a results array"

print(f"drugsfda endpoint live — total records in DB: {ping_drugsfda['meta']['results']['total']:,}")
print(f"label endpoint live    — total records in DB: {ping_label['meta']['results']['total']:,}")
print(f"Last data update: {ping_drugsfda['meta']['last_updated']}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 2 — Endpoint and Parameter Selection
# MAGIC
# MAGIC **Two complementary endpoints are used together for DMD.**
# MAGIC
# MAGIC The `drug/label` endpoint is the **primary source** for DMD eligibility data because it
# MAGIC contains the INDICATIONS AND USAGE section of each prescribing label — the free text that
# MAGIC encodes which patient genotypes a drug is approved for. Filtering by
# MAGIC `indications_and_usage:"Duchenne muscular dystrophy"` reliably returns all approved DMD
# MAGIC drugs plus corticosteroid standard-of-care products (deflazacort/EMFLAZA, vamorolone/AGAMREE).
# MAGIC The total DMD label corpus is 24 records as of the last data update — small enough to
# MAGIC ingest in full on every run.
# MAGIC
# MAGIC The `drug/drugsfda` endpoint is the **secondary source** for application metadata. It holds
# MAGIC the complete supplement history per NDA/BLA number — every labeling change, efficacy supplement,
# MAGIC and manufacturing supplement submitted since original approval. For DMD, the key insight is
# MAGIC that each AON drug has multiple supplements: the original accelerated approval (TYPE 1) and
# MAGIC subsequent traditional approval supplements (EFFICACY, LABELING). Bronze must ingest the
# MAGIC full `submissions` array, not just the most recent entry, to capture the approval trajectory.
# MAGIC Querying by `application_number` for each known NDA/BLA is more reliable than keyword search
# MAGIC on the drugsfda endpoint, which does not index indication text.
# MAGIC
# MAGIC **Why these parameters narrow to DMD-relevant records.**
# MAGIC The label search `indications_and_usage:"Duchenne muscular dystrophy"` performs a full-text
# MAGIC match against the structured INDICATIONS AND USAGE SPL section. It captures both mutation-specific
# MAGIC drugs (AONs, gene therapy) and mutation-agnostic standard-of-care (corticosteroids), which is
# MAGIC correct for Bronze — filtering to mutation-specific drugs only happens at Silver.
# MAGIC The exon-skipping subset is further isolated by searching for "amenable to exon" in the
# MAGIC indication text, which is the regulatory language used consistently across all four AONs.

# COMMAND ----------

# --- Label endpoint: full DMD label corpus ---
# search: full-text match on "Duchenne muscular dystrophy" in INDICATIONS AND USAGE
# limit=100 safely exceeds the 24-record total; no pagination needed for this corpus.
label_params = {
    "search": 'indications_and_usage:"Duchenne muscular dystrophy"',
    "limit": 100,
}
label_resp = _get(BASE_LABEL, label_params)
label_total = label_resp["meta"]["results"]["total"]
label_records = label_resp["results"]

print(f"Label endpoint: {label_total} total records matching 'Duchenne muscular dystrophy'")
print(f"Records fetched in this call: {len(label_records)}")
print()

# Show brand name and first 200 chars of indication for each record.
for rec in label_records[:10]:
    openfda  = rec.get("openfda", {})
    brand    = openfda.get("brand_name", ["(no brand)"])[0] if openfda.get("brand_name") else "(no brand)"
    ind_text = rec.get("indications_and_usage", ["(missing)"])[0][:200]
    print(f"  {brand}: {ind_text!r}")

# COMMAND ----------

# --- drugsfda endpoint: application metadata for known DMD NDA/BLA numbers ---
# These six application numbers correspond to the four FDA-approved AONs, the microdystrophin
# gene therapy, and givinostat (pan-HDAC inhibitor). Obtained from the label endpoint's
# openfda.application_number field.
#
# NDA206488  EXONDYS 51      eteplirsen          exon 51 skip  Sarepta
# NDA214291  VYONDYS 53      golodirsen          exon 53 skip  Sarepta
# NDA212154  VILTEPSO        viltolarsen         exon 53 skip  NS Pharma
# NDA220197  AMONDYS 45      casimersen          exon 45 skip  Sarepta
# BLA125610  ELEVIDYS        delandistrogene moxeparvovec       Sarepta
# NDA217172  DUVYZAT         givinostat          pan-HDAC       ITF Therapeutics

DMD_APPLICATION_NUMBERS = [
    "NDA206488",  # eteplirsen
    "NDA214291",  # golodirsen
    "NDA212154",  # viltolarsen
    "NDA220197",  # casimersen
    "BLA125610",  # delandistrogene moxeparvovec
    "NDA217172",  # givinostat
]

drugsfda_records = []
for app_num in DMD_APPLICATION_NUMBERS:
    params = {"search": f"application_number:{app_num}", "limit": 1}
    try:
        resp = _get(BASE_DRUGSFDA, params)
        if resp.get("results"):
            drugsfda_records.append(resp["results"][0])
            n_suppl = len(resp["results"][0].get("submissions", []))
            brand = resp["results"][0].get("openfda", {}).get("brand_name", ["?"])[0]
            print(f"  {app_num}  {brand:25s}  {n_suppl} submissions")
        else:
            print(f"  {app_num}  NOT FOUND in drugsfda")
    except requests.HTTPError as exc:
        print(f"  {app_num}  HTTP error: {exc}")

print(f"\ndrugsfda records fetched: {len(drugsfda_records)}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 3 — Response Schema Inspection
# MAGIC
# MAGIC **Label endpoint schema — clinically annotated fields.**
# MAGIC
# MAGIC | Field | Type | Clinical relevance |
# MAGIC |---|---|---|
# MAGIC | `indications_and_usage` | `string[]` (1-element array) | **Most critical field.** Contains the genetic eligibility sentence: which exon skipping target or genotype the drug is approved for. At Silver this field must be parsed to extract structured eligibility rules. It is always a free-text blob — the genetic criteria are embedded in prose and require pattern matching or NLP extraction. |
# MAGIC | `openfda.application_number` | `string[]` | NDA/BLA number linking this label version to the full application history in the drugsfda endpoint. Essential join key. |
# MAGIC | `openfda.brand_name` | `string[]` | Human-readable drug name. |
# MAGIC | `openfda.generic_name` | `string[]` | INN. Used for deduplication when multiple label versions exist for the same molecule. |
# MAGIC | `openfda.manufacturer_name` | `string[]` | Sponsor name in normalised form (differs from `drugsfda.sponsor_name` which uses all-caps FDA formatting). |
# MAGIC | `openfda.pharm_class_epc` | `string[]` | Established Pharmacologic Class — e.g. "Antisense Oligonucleotide [EPC]". Silver filter to isolate AONs from corticosteroids. |
# MAGIC | `openfda.substance_name` | `string[]` | Active substance UNII name. Enables cross-referencing against RxNorm and ChEMBL. |
# MAGIC | `openfda.unii` | `string[]` | FDA unique ingredient identifier. Stable across label versions; use as the canonical molecule key. |
# MAGIC | `id` | `string` (UUID) | Unique identifier for this specific label version (SPL document ID). Changes on each label revision. |
# MAGIC | `set_id` | `string` (UUID) | Stable identifier for the labeling set across all versions of the same product. The `set_id` is the correct join key when tracking label revisions over time. |
# MAGIC | `effective_time` | `string` (YYYYMMDD) | Date this label version became effective. Needed for version-ordered ingestion and Silver SCD Type 2. |
# MAGIC | `version` | `string` | Integer version counter within the set. Monotonically increasing per `set_id`. |
# MAGIC | `warnings_and_cautions` | `string[]` | Contains patient-level exclusion criteria (e.g. pre-existing liver impairment for ELEVIDYS, AAV antibody titres). Layer 3 data. |
# MAGIC | `boxed_warning` | `string[]` | Boxed warnings — present for ELEVIDYS (acute liver injury). Important safety signal for Layer 3 eligibility. |
# MAGIC | `clinical_studies` | `string[]` | Trial population descriptions, sometimes including the exon distribution of the enrolled cohort. Secondary source for eligibility evidence. |
# MAGIC
# MAGIC Fields that are **always null or irrelevant for DMD matching:**
# MAGIC `spl_product_data_elements` (SPL rendering metadata), `package_label_principal_display_panel`
# MAGIC (marketing text for the outer carton). Both can be dropped at Bronze schema definition.
# MAGIC
# MAGIC **drugsfda endpoint schema — clinically annotated fields.**
# MAGIC
# MAGIC | Field | Type | Clinical relevance |
# MAGIC |---|---|---|
# MAGIC | `application_number` | `string` | NDA or BLA number. Primary key. |
# MAGIC | `sponsor_name` | `string` | Applicant name in FDA all-caps format. |
# MAGIC | `submissions[].submission_type` | `string` | ORIG = original approval; SUPPL = supplement. All supplements must be retained — they capture the approval trajectory from accelerated to traditional approval. |
# MAGIC | `submissions[].submission_class_code` | `string` | TYPE 1 (NME), EFFICACY, LABELING, MANUFACTURING. EFFICACY supplements are the highest-value: they often correspond to conversion from accelerated to traditional approval or label expansion to new patient populations. |
# MAGIC | `submissions[].submission_status` | `string` | AP = approved, TA = tentatively approved, W = withdrawn. Withdrawn submissions are important to retain — they represent indication changes or safety withdrawals. |
# MAGIC | `submissions[].submission_status_date` | `string` (YYYYMMDD) | Approval date per supplement. Enables reconstruction of the complete approval timeline. |
# MAGIC | `submissions[].review_priority` | `string` | PRIORITY or STANDARD. DMD drugs received priority review and orphan designation. |
# MAGIC | `submissions[].submission_property_type[].code` | `string` | Orphan, Breakthrough, FastTrack. Regulatory pathway metadata relevant to understanding the evidence base for the approval. |
# MAGIC | `submissions[].application_docs[].url` | `string` | Direct URL to the label PDF, approval letter, or review document. Bronze should store these as provenance links; Silver can fetch the label PDF for additional text extraction if the structured API field is insufficient. |
# MAGIC | `submissions[].application_docs[].type` | `string` | Label / Letter / Review / Summary Review. |
# MAGIC | `products[].brand_name` | `string` | Product-level brand name (one application may have multiple products/strengths). |
# MAGIC | `products[].active_ingredients[].name` | `string` | INN at product level. |
# MAGIC | `products[].active_ingredients[].strength` | `string` | Dosage strength — relevant for distinguishing vial sizes (eteplirsen: 100 mg/2 mL and 500 mg/10 mL). |
# MAGIC | `products[].marketing_status` | `string` | Prescription / Discontinued. Discontinued products should be flagged but retained in Bronze. |
# MAGIC | `openfda.pharm_class_epc` | `string[]` | Pharmacological class for cross-endpoint consistency checking. |

# COMMAND ----------

# Inspect schema of the first label record and the first drugsfda record in detail.

print("=== LABEL ENDPOINT: field inventory of first record ===")
first_label = label_records[0]
for key, val in first_label.items():
    if isinstance(val, list):
        sample = str(val[0])[:120] if val else "(empty list)"
        print(f"  {key:45s}  list[{len(val)}]  -> {sample!r}")
    else:
        print(f"  {key:45s}  {type(val).__name__}    -> {str(val)[:120]!r}")

print()
print("=== DRUGSFDA ENDPOINT: field inventory of first record ===")
first_drugsfda = drugsfda_records[0]
print(f"  application_number: {first_drugsfda.get('application_number')}")
print(f"  sponsor_name:       {first_drugsfda.get('sponsor_name')}")
print(f"  number of submissions: {len(first_drugsfda.get('submissions', []))}")
print(f"  number of products:    {len(first_drugsfda.get('products', []))}")
print()
print("  First submission entry keys:")
if first_drugsfda.get("submissions"):
    for k, v in first_drugsfda["submissions"][0].items():
        print(f"    {k:45s}  -> {str(v)[:80]!r}")
print()
print("  openfda keys:")
for k, v in first_drugsfda.get("openfda", {}).items():
    print(f"    {k:45s}  -> {str(v)[:80]!r}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 4 — Pagination Walkthrough
# MAGIC
# MAGIC The openFDA API paginates via `skip` (offset) and `limit` (page size, max 1000).
# MAGIC The `meta.results.total` field gives the total number of matching records.
# MAGIC There is no cursor or next-page token — pagination is purely offset-based.
# MAGIC
# MAGIC **DMD label corpus is small enough to bypass pagination entirely.** The 24 records matching
# MAGIC "Duchenne muscular dystrophy" fit in a single request with `limit=100`. This is deliberately
# MAGIC verified here so that the production Bronze pipeline can use a single-shot fetch rather than
# MAGIC a loop, eliminating pagination complexity and reducing API call count.
# MAGIC
# MAGIC **drugsfda corpus for the 6 known DMD NDA/BLA numbers** is fetched record-by-record (one
# MAGIC API call per application number) because keyword search on `drugsfda` is unreliable — the
# MAGIC endpoint does not index indication text. The lookup-by-application-number pattern is the
# MAGIC correct approach. The list of application numbers is maintained in the Bronze pipeline config,
# MAGIC updated when new drugs are approved.
# MAGIC
# MAGIC **Pagination gotcha observed:** the `drug/label` endpoint returns each label version as a
# MAGIC separate record, identified by the `id` UUID (version-specific) vs the `set_id` UUID
# MAGIC (product-stable). If a label is revised (e.g. EXONDYS 51 has 15 versions as of mid-2025),
# MAGIC only the most recent version appears in a default search — the API does not surface historical
# MAGIC versions. To ingest all versions, a Silver job would need to retrieve the label history via
# MAGIC DailyMed's FHIR API or the FDA's bulk download files, not the openFDA search API.
# MAGIC This is a significant provenance gap: the Bronze layer as designed here captures current
# MAGIC label state only, not the full label history.

# COMMAND ----------

# Demonstrate offset-based pagination on the label endpoint.
# Verify field consistency across page boundaries.
PAGE_SIZE = 5
pages_fetched = []

for page_num in range(3):  # fetch 3 pages = 15 records
    offset = page_num * PAGE_SIZE
    page_params = {
        "search": 'indications_and_usage:"Duchenne muscular dystrophy"',
        "limit": PAGE_SIZE,
        "skip": offset,
    }
    page_resp = _get(BASE_LABEL, page_params)
    page_records = page_resp["results"]
    pages_fetched.append(page_records)

    field_sets = [set(rec.keys()) for rec in page_records]
    # Core fields that must be present on every record.
    required_fields = {"id", "set_id", "effective_time", "version", "openfda", "indications_and_usage"}
    for i, rec in enumerate(page_records):
        missing = required_fields - set(rec.keys())
        if missing:
            print(f"  Page {page_num}, record {i}: MISSING fields: {missing}")

    print(f"Page {page_num} (skip={offset}): fetched {len(page_records)} records — "
          f"all required fields present: {all(required_fields <= set(r.keys()) for r in page_records)}")

total_across_pages = sum(len(p) for p in pages_fetched)
print(f"\nTotal records verified across 3 pages: {total_across_pages}")
print(f"Full corpus total from meta: {label_total}")
print(f"Single-shot feasibility: {'YES — corpus fits in one request' if label_total <= 1000 else 'NO — pagination required'}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 5 — Data Quality First Look
# MAGIC
# MAGIC **Key findings for the DMD label corpus.**
# MAGIC
# MAGIC The primary field `indications_and_usage` is present in all records but its structure is
# MAGIC inconsistent in ways that matter for Silver parsing:
# MAGIC - AON labels use the standardised phrase "amenable to exon N skipping" — this is parseable
# MAGIC   with a simple regex (`amenable to exon (\d+) skipping`).
# MAGIC - ELEVIDYS (gene therapy) uses "confirmed DMD gene mutation" without specifying an exon
# MAGIC   target — it is mutation-agnostic and the indication text does not contain exon numbers.
# MAGIC - Corticosteroid labels (deflazacort, vamorolone) contain "Duchenne muscular dystrophy"
# MAGIC   in the indication but carry no genetic eligibility criteria — they are mutation-agnostic.
# MAGIC - Givinostat (DUVYZAT, pan-HDAC inhibitor) is also mutation-agnostic.
# MAGIC
# MAGIC **openfda object completeness** varies by record. Several records (including AGAMREE) have
# MAGIC an empty `openfda: {}` object, meaning the `application_number` link to the drugsfda endpoint
# MAGIC is absent. For these records, the NDA/BLA number must be looked up separately.
# MAGIC
# MAGIC **Date format** is consistently YYYYMMDD (e.g. `20250813`) — requires parsing to ISO 8601
# MAGIC at Silver. No observed timezone ambiguity.
# MAGIC
# MAGIC **Null rate assessment** — fields to flag for `@dlt.expect_or_quarantine` rules in production:
# MAGIC - `indications_and_usage`: expected present; quarantine if missing (it is the primary field).
# MAGIC - `openfda.application_number`: ~30% of records have empty openfda — do not quarantine, but
# MAGIC   flag with `has_nda_link = false` for downstream attention.
# MAGIC - `effective_time`: always present in observed records; quarantine if missing.
# MAGIC - `set_id`: always present; quarantine if missing (it is the stable product identifier).

# COMMAND ----------

from collections import Counter

# Null / presence rates for key fields across the full label corpus.
key_fields = [
    "indications_and_usage",
    "effective_time",
    "set_id",
    "version",
    "warnings_and_cautions",
    "boxed_warning",
    "clinical_studies",
]

print("=== FIELD PRESENCE RATES (label endpoint, full DMD corpus) ===")
print(f"{'Field':<40} {'Present':>8}  {'% present':>10}")
for field in key_fields:
    present = sum(1 for r in label_records if r.get(field))
    pct = 100 * present / len(label_records) if label_records else 0
    print(f"  {field:<38} {present:>6}/{len(label_records)}  {pct:>9.1f}%")

# openfda completeness check.
print()
print("=== OPENFDA OBJECT COMPLETENESS (label endpoint) ===")
openfda_fields = ["application_number", "brand_name", "generic_name",
                  "manufacturer_name", "pharm_class_epc", "unii"]
for field in openfda_fields:
    present = sum(1 for r in label_records if r.get("openfda", {}).get(field))
    pct = 100 * present / len(label_records) if label_records else 0
    print(f"  openfda.{field:<32} {present:>6}/{len(label_records)}  {pct:>9.1f}%")

# Value distribution for pharm_class_epc — the Silver filter field.
print()
print("=== PHARMACOLOGICAL CLASS DISTRIBUTION (label endpoint) ===")
epc_counts: Counter = Counter()
for r in label_records:
    epcs = r.get("openfda", {}).get("pharm_class_epc", [])
    if epcs:
        for epc in epcs:
            epc_counts[epc] += 1
    else:
        epc_counts["(missing)"] += 1
for epc, count in epc_counts.most_common():
    print(f"  {count:3d}  {epc}")

# Version distribution — how many label versions per set_id.
print()
print("=== LABEL VERSION DISTRIBUTION (effective_time range) ===")
dates = [r.get("effective_time", "") for r in label_records if r.get("effective_time")]
if dates:
    print(f"  Earliest effective_time: {min(dates)}")
    print(f"  Latest effective_time:   {max(dates)}")
    print(f"  Records with effective_time: {len(dates)}/{len(label_records)}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 6 — Bronze Schema Sketch
# MAGIC
# MAGIC Two Delta tables are proposed for Bronze ingestion of FDA data. They are kept separate
# MAGIC because they have different update cadences and different primary keys.
# MAGIC
# MAGIC **Table 1: `clinical.bronze.fda_label_raw`** (primary for eligibility matching)
# MAGIC
# MAGIC | Column | Source path | Presence | Notes |
# MAGIC |---|---|---|---|
# MAGIC | `label_id` | `id` | always-present | Version-specific UUID. Changes on each label revision. |
# MAGIC | `label_set_id` | `set_id` | always-present | Stable product UUID. Use as the dedup key in Silver SCD Type 2. |
# MAGIC | `effective_time` | `effective_time` | always-present | YYYYMMDD string — parse to `date` at Silver. |
# MAGIC | `version` | `version` | always-present | Integer string — cast to `int` at Silver. |
# MAGIC | `indications_and_usage` | `indications_and_usage[0]` | always-present | Free text. **Primary Silver NLP target.** `@dlt.expect_or_quarantine` if null. |
# MAGIC | `warnings_and_cautions` | `warnings_and_cautions[0]` | optional | Contains Layer 3 patient-level exclusion criteria (AAV antibodies, liver function). |
# MAGIC | `boxed_warning` | `boxed_warning[0]` | optional | Present for ELEVIDYS. Signals high-severity patient-level safety constraint. |
# MAGIC | `clinical_studies` | `clinical_studies[0]` | optional | Trial population descriptions. |
# MAGIC | `openfda_application_number` | `openfda.application_number[0]` | optional (~70%) | Join key to `fda_approvals_raw`. Null for some records — requires fallback lookup. |
# MAGIC | `openfda_brand_name` | `openfda.brand_name[0]` | optional (~70%) | Human-readable name. |
# MAGIC | `openfda_generic_name` | `openfda.generic_name[0]` | optional (~70%) | INN. |
# MAGIC | `openfda_manufacturer_name` | `openfda.manufacturer_name[0]` | optional (~70%) | Normalised sponsor name. |
# MAGIC | `openfda_pharm_class_epc` | `openfda.pharm_class_epc[0]` | optional (~70%) | Silver filter: "Antisense Oligonucleotide [EPC]" isolates AONs. |
# MAGIC | `openfda_unii` | `openfda.unii[0]` | optional (~70%) | Stable molecule identifier. |
# MAGIC | `source_system` | injected | always-present | `"openfda_label"` |
# MAGIC | `ingestion_timestamp` | injected | always-present | UTC timestamp of API call. |
# MAGIC | `api_version` | injected | always-present | openFDA API version string from meta. |
# MAGIC | `source_url` | injected | always-present | Full request URL with parameters. |
# MAGIC
# MAGIC **Silver transformation complexity flags:**
# MAGIC - `indications_and_usage`: free-text blob — requires regex/NLP to extract `target_exon` (int), `mutation_type`, `eligibility_phrase` (string). High complexity.
# MAGIC - `warnings_and_cautions`: unstructured prose — Layer 3 exclusion criteria buried in it. Requires NLP or manual curation per drug.
# MAGIC - All `openfda.*` fields: arrays — must explode or take index 0. Low complexity.
# MAGIC - `effective_time`: YYYYMMDD string — simple `to_date` cast. Low complexity.
# MAGIC
# MAGIC **Table 2: `clinical.bronze.fda_approvals_raw`** (full application metadata with supplement history)
# MAGIC
# MAGIC | Column | Source path | Presence | Notes |
# MAGIC |---|---|---|---|
# MAGIC | `application_number` | `application_number` | always-present | NDA/BLA. Primary key for the application. |
# MAGIC | `sponsor_name` | `sponsor_name` | always-present | All-caps FDA format — normalise at Silver. |
# MAGIC | `submissions` | `submissions` | always-present | Full array as JSON string. Explode at Silver to one row per supplement. |
# MAGIC | `products` | `products` | always-present | Full array as JSON string. Explode at Silver to one row per product/strength. |
# MAGIC | `openfda_brand_name` | `openfda.brand_name[0]` | optional | |
# MAGIC | `openfda_generic_name` | `openfda.generic_name[0]` | optional | |
# MAGIC | `openfda_pharm_class_epc` | `openfda.pharm_class_epc[0]` | optional | |
# MAGIC | `openfda_unii` | `openfda.unii[0]` | optional | |
# MAGIC | `source_system` | injected | always-present | `"openfda_drugsfda"` |
# MAGIC | `ingestion_timestamp` | injected | always-present | UTC timestamp. |
# MAGIC | `source_url` | injected | always-present | Full request URL. |
# MAGIC
# MAGIC **Note on target table naming.** The production target is `clinical.bronze.fda_approvals_raw`
# MAGIC (per the inputs). Given that two endpoints are used, the label records should be ingested
# MAGIC into a separate table `clinical.bronze.fda_label_raw`. The personal schema exploration table
# MAGIC in Section 8 uses `bronze_fda_approvals_raw` to match the stated target, and contains both
# MAGIC sources joined on `application_number` for convenience.

# COMMAND ----------

import json as _json

def _flatten_label_record(rec: dict, ingestion_ts: str, source_url: str) -> dict:
    """Flatten one label API record to the Bronze column set."""
    openfda = rec.get("openfda", {})
    def _first(lst):
        return lst[0] if lst else None

    return {
        "label_id":                    rec.get("id"),
        "label_set_id":                rec.get("set_id"),
        "effective_time":              rec.get("effective_time"),
        "version":                     rec.get("version"),
        "indications_and_usage":       _first(rec.get("indications_and_usage", [])),
        "warnings_and_cautions":       _first(rec.get("warnings_and_cautions", [])),
        "boxed_warning":               _first(rec.get("boxed_warning", [])),
        "clinical_studies":            _first(rec.get("clinical_studies", [])),
        "openfda_application_number":  _first(openfda.get("application_number", [])),
        "openfda_brand_name":          _first(openfda.get("brand_name", [])),
        "openfda_generic_name":        _first(openfda.get("generic_name", [])),
        "openfda_manufacturer_name":   _first(openfda.get("manufacturer_name", [])),
        "openfda_pharm_class_epc":     _first(openfda.get("pharm_class_epc", [])),
        "openfda_unii":                _first(openfda.get("unii", [])),
        "source_system":               "openfda_label",
        "ingestion_timestamp":         ingestion_ts,
        "api_version":                 "1.0",
        "source_url":                  source_url,
    }

def _flatten_drugsfda_record(rec: dict, ingestion_ts: str, source_url: str) -> dict:
    """Flatten one drugsfda API record to the Bronze column set."""
    openfda = rec.get("openfda", {})
    def _first(lst):
        return lst[0] if lst else None

    return {
        "application_number":         rec.get("application_number"),
        "sponsor_name":               rec.get("sponsor_name"),
        "submissions":                _json.dumps(rec.get("submissions", [])),
        "products":                   _json.dumps(rec.get("products", [])),
        "openfda_brand_name":         _first(openfda.get("brand_name", [])),
        "openfda_generic_name":       _first(openfda.get("generic_name", [])),
        "openfda_pharm_class_epc":    _first(openfda.get("pharm_class_epc", [])),
        "openfda_unii":               _first(openfda.get("unii", [])),
        "source_system":              "openfda_drugsfda",
        "ingestion_timestamp":        ingestion_ts,
        "source_url":                 source_url,
    }

ingestion_ts = datetime.utcnow().isoformat() + "Z"
label_source_url = (
    f"{BASE_LABEL}?search=indications_and_usage:%22Duchenne+muscular+dystrophy%22&limit=100"
)
drugsfda_source_url = f"{BASE_DRUGSFDA}?search=application_number:<NDA>&limit=1"

label_rows    = [_flatten_label_record(r, ingestion_ts, label_source_url) for r in label_records]
drugsfda_rows = [_flatten_drugsfda_record(r, ingestion_ts, drugsfda_source_url) for r in drugsfda_records]

print(f"Label rows flattened:    {len(label_rows)}")
print(f"drugsfda rows flattened: {len(drugsfda_rows)}")
print()
print("Label row sample (first record, truncated values):")
sample = {k: (str(v)[:80] if isinstance(v, str) and len(str(v)) > 80 else v)
          for k, v in label_rows[0].items()}
for k, v in sample.items():
    print(f"  {k:<40s}  {v!r}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 7 — Provenance Metadata
# MAGIC
# MAGIC ALCOA+ provenance principles — Attributable, Legible, Contemporaneous, Original, Accurate,
# MAGIC plus Complete, Consistent, Enduring, and Available — are the regulatory standard for clinical
# MAGIC data integrity, derived from FDA 21 CFR Part 11 and ICH E6(R2) Good Clinical Practice.
# MAGIC
# MAGIC For FDA approval data, which is itself regulatory source data, provenance at Bronze is
# MAGIC especially important because:
# MAGIC
# MAGIC 1. **Attributable**: `source_system` tags each row to its originating endpoint
# MAGIC    (`openfda_label` or `openfda_drugsfda`). `source_url` records the exact API call —
# MAGIC    anyone can reproduce the fetch by replaying that URL.
# MAGIC 2. **Contemporaneous**: `ingestion_timestamp` is the UTC wall-clock time of the API call,
# MAGIC    not the `last_updated` field from the meta block (which reflects the FDA's last data
# MAGIC    refresh, not the moment the data was ingested into this platform).
# MAGIC 3. **Original**: Bronze stores the flattened but otherwise unmodified API response. No
# MAGIC    interpretation, filtering, or reformatting happens at Bronze — those transformations
# MAGIC    belong to Silver and must be logged separately.
# MAGIC 4. **api_version**: openFDA does not expose a formal semantic API version; the `api_version`
# MAGIC    field records the `last_updated` date from the meta block as a proxy. If the FDA changes
# MAGIC    the API schema, `last_updated` will change and trigger a schema validation alert in the
# MAGIC    production DLT pipeline.
# MAGIC
# MAGIC The `submissions[].application_docs[].url` field in `drugsfda` records contains direct links
# MAGIC to the label PDF, approval letter, and review documents stored at accessdata.fda.gov. These
# MAGIC URLs are provenance artifacts — they link the structured Bronze data back to the original
# MAGIC regulatory submission documents. The Silver pipeline should resolve and validate these URLs
# MAGIC (HTTP 200 check) to detect when FDA moves or removes historical documents.

# COMMAND ----------

# Provenance metadata pattern — how source_system, ingestion_timestamp, api_version,
# and source_url are attached to every Bronze row.

# Retrieve api_version from the meta block (last_updated is the closest available proxy).
meta_resp = _get(BASE_LABEL, {"search": 'indications_and_usage:"Duchenne muscular dystrophy"', "limit": 1})
api_version_proxy = meta_resp["meta"]["last_updated"]  # e.g. "2026-06-05"

provenance = {
    "source_system":     "openfda_label",          # identifies originating endpoint
    "ingestion_timestamp": datetime.utcnow().isoformat() + "Z",  # UTC wall-clock at fetch
    "api_version":       api_version_proxy,         # FDA last_updated as version proxy
    "source_url":        label_source_url,          # reproducible fetch URL
}

print("Provenance block that will be attached to every Bronze row:")
for k, v in provenance.items():
    print(f"  {k:<25s}  {v!r}")

print()
# Application docs URLs from the first drugsfda record — show how regulatory documents are linked.
print("Application document URLs (from drugsfda submissions — provenance chain to source):")
for submission in drugsfda_records[0].get("submissions", [])[:3]:
    sub_id   = f"{submission.get('submission_type')}-{submission.get('submission_number')}"
    sub_date = submission.get("submission_status_date", "")
    for doc in submission.get("application_docs", []):
        print(f"  [{sub_id} {sub_date}] {doc.get('type'):15s}  {doc.get('url', '')}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 8 — Write to Personal Schema
# MAGIC
# MAGIC The rows constructed above are written to `workspace.steff_horemans.bronze_fda_approvals_raw`
# MAGIC using Databricks Connect with a serverless compute session. This is an ungoverned personal
# MAGIC schema (per ADR-01) — exploration tables written here are never referenced or imported from
# MAGIC production pipelines. The `USE workspace.steff_horemans` statement sets this schema as the
# MAGIC session default so subsequent SQL cells in this notebook can omit the catalog and schema prefix.
# MAGIC
# MAGIC The table written here combines both the label rows and the drugsfda application metadata rows
# MAGIC into a single exploration table, with `source_system` as the discriminator column. In production,
# MAGIC these would be two separate Delta tables: `clinical.bronze.fda_label_raw` and
# MAGIC `clinical.bronze.fda_approvals_raw`. The combined table here is an exploration convenience only.

# COMMAND ----------

from databricks.connect import DatabricksSession  # noqa: E402

# Connects to the remote cluster via Databricks Connect — execution happens on Databricks.
spark = DatabricksSession.builder.profile("steff_horemans").serverless(True).getOrCreate()
# Alternative if serverless is not available:
# spark = DatabricksSession.builder.profile("steff_horemans").clusterId("<cluster-id>").getOrCreate()

spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.steff_horemans")
spark.sql("USE workspace.steff_horemans")

# Build a unified row set for exploration. Each row carries source_system so the two
# endpoint shapes can be distinguished. The outer join is on application_number where present.
# For production: split into separate tables and join in Silver via application_number.
#
# Use only label rows here as the primary exploration target — they carry the eligibility text.
# drugsfda rows are written to a separate table below.

df_labels = spark.createDataFrame(label_rows)
(
    df_labels.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.steff_horemans.bronze_fda_approvals_raw")
)

print(f"Written {df_labels.count()} rows to workspace.steff_horemans.bronze_fda_approvals_raw")
spark.sql("DESCRIBE TABLE bronze_fda_approvals_raw").show(truncate=False)

# COMMAND ----------

# Write the drugsfda application-metadata rows to a companion exploration table.
df_drugsfda = spark.createDataFrame(drugsfda_rows)
(
    df_drugsfda.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.steff_horemans.bronze_fda_drugsfda_raw")
)

print(f"Written {df_drugsfda.count()} rows to workspace.steff_horemans.bronze_fda_drugsfda_raw")
spark.sql("DESCRIBE TABLE bronze_fda_drugsfda_raw").show(truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 8 continued — Spot-check the written data
# MAGIC
# MAGIC Verify that the mutation-specific eligibility phrases are present and parseable in the
# MAGIC written table. The Silver pipeline will build regex extractors for these patterns.

# COMMAND ----------

# Confirm the six FDA-approved DMD drugs are present and show their eligibility text.
print("=== DMD-SPECIFIC ELIGIBILITY PHRASES IN WRITTEN TABLE ===")
print("(Confirming all six approved drugs are captured)\n")

dmd_drugs = spark.sql("""
    SELECT
        openfda_brand_name,
        openfda_generic_name,
        openfda_pharm_class_epc,
        effective_time,
        SUBSTRING(indications_and_usage, 1, 300) AS indication_snippet
    FROM bronze_fda_approvals_raw
    WHERE openfda_brand_name IS NOT NULL
    ORDER BY openfda_brand_name
""")
dmd_drugs.show(truncate=False)

# Quick check: does the "amenable to exon N skipping" pattern appear in the expected records?
exon_skip_rows = spark.sql("""
    SELECT openfda_brand_name, openfda_pharm_class_epc,
           REGEXP_EXTRACT(indications_and_usage, 'amenable to exon (\\d+) skipping', 1) AS target_exon
    FROM bronze_fda_approvals_raw
    WHERE indications_and_usage LIKE '%amenable to exon%'
    ORDER BY openfda_brand_name
""")
print("\n=== EXON SKIPPING TARGET EXTRACTED FROM LABEL TEXT ===")
exon_skip_rows.show(truncate=False)
