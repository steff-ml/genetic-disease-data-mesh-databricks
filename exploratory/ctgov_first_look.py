# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # ClinicalTrials.gov v2 API — First Look Exploration
# MAGIC
# MAGIC **Source**: ClinicalTrials.gov FDAAA 801 / Final Rule registry (public domain)
# MAGIC **Target table**: `clinical.bronze.clinicaltrials_raw`
# MAGIC **API base**: `https://clinicaltrials.gov/api/v2/studies`
# MAGIC **Author**: exploration-notebook agent
# MAGIC **Date**: 2026-06-06
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Section 0 — Context and Purpose
# MAGIC
# MAGIC ClinicalTrials.gov is the primary source for this project's **Layer 3 (patient-level)** and **Layer 2
# MAGIC (approach-specific)** eligibility data. Every active or completed interventional trial in the DMD space
# MAGIC is registered here, including AON exon-skipping trials, microdystrophin gene therapy programmes,
# MAGIC CRISPR-based reading frame correction studies, and stop-codon read-through trials.
# MAGIC
# MAGIC The scientific question this exploration answers: **what does the ClinicalTrials.gov v2 API actually
# MAGIC return for DMD-filtered queries, and is the raw `eligibilityCriteria` field — a free-text blob — rich
# MAGIC enough to support NLP-based extraction of mutation-specific inclusion/exclusion rules?** Specifically,
# MAGIC we need to determine whether the text reliably encodes exon-skipping targets (e.g. "amenable to exon 51
# MAGIC skipping"), mutation type constraints (deletion / nonsense), and patient-level filters (age, AAV antibody
# MAGIC status, prior treatment).
# MAGIC
# MAGIC A successful Bronze ingestion of this source enables:
# MAGIC 1. The `silver.trials_dmd` filtered table (DMD-only, interventional, phases II–IV).
# MAGIC 2. The `silver.eligibility_criteria` structured rules table, where mutation-specific criteria are
# MAGIC    separated from patient-level criteria via NLP.
# MAGIC 3. The `gold.trial_eligibility_catalogue` — the queryable data product that the eligibility rule engine
# MAGIC    joins against `discovery.gold.patient_mutation_profile` to produce per-patient, per-trial verdicts.
# MAGIC
# MAGIC This source was chosen over the EU Clinical Trials Register as the primary Bronze target because
# MAGIC ClinicalTrials.gov has mandatory registration for US-funded studies (FDAAA 801) and a stable public
# MAGIC REST API with no authentication requirement, making it the broadest and most accessible starting point.
# MAGIC EU CTR will be ingested separately as a complementary Bronze source.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 1 — Connection and Authentication
# MAGIC
# MAGIC The ClinicalTrials.gov v2 API is fully public — no API key, OAuth token, or registration is required.
# MAGIC Rate limit is approximately 10 requests per second per the known constraints for this source.
# MAGIC There is no documented authentication scheme; all requests are unauthenticated HTTPS GET calls.
# MAGIC
# MAGIC The choice of this source over alternatives (EU CTR, WHO ICTRP) reflects:
# MAGIC - **Coverage**: mandatory US registration creates near-complete capture of commercially sponsored
# MAGIC   DMD trials, including all four approved AON sponsors (Sarepta, NS Pharma, Nippon Shinyaku, Solid).
# MAGIC - **API stability**: the v2 API launched in 2023 and supersedes the v1 (legacy) API; v2 uses cursor-based
# MAGIC   pagination and structured JSON rather than the XML-heavy v1 format.
# MAGIC - **No data access agreement**: unlike TREAT-NMD or HGMD, ClinicalTrials.gov data is public domain
# MAGIC   under US law (17 U.S.C. § 105), requiring no DUA or IRB approval for programmatic access.
# MAGIC
# MAGIC No ADR covering source selection has been written yet; this exploration notebook is the evidence base
# MAGIC for a future ADR covering Bronze ingestion design.

# COMMAND ----------

import requests
import json
import time

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

# Minimal connectivity test — fetch a single record and assert HTTP 200.
response = requests.get(
    BASE_URL,
    params={"query.cond": "Duchenne Muscular Dystrophy", "pageSize": 1, "format": "json"},
    timeout=30,
)
assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"

data = response.json()
print("HTTP status       :", response.status_code)
print("Top-level keys    :", list(data.keys()))
print("Studies returned  :", len(data.get("studies", [])))
print("nextPageToken     :", data.get("nextPageToken", "<none>"))
print("Connection OK.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 2 — Endpoint and Parameter Selection
# MAGIC
# MAGIC The v2 API exposes a single primary endpoint: `GET /api/v2/studies`. All filtering is done through
# MAGIC query parameters passed to this endpoint. No separate endpoint exists for DMD-specific records.
# MAGIC
# MAGIC **Why these parameters specifically:**
# MAGIC
# MAGIC - `query.cond = "Duchenne Muscular Dystrophy"` — the condition search field performs a full-text
# MAGIC   match against the trial's condition list and MeSH terms. Using the full disease name rather than
# MAGIC   the ORPHA code (ORPHA:98896) or OMIM ID (310200) ensures broadest recall, since many older
# MAGIC   registrations do not use structured ontology codes.
# MAGIC
# MAGIC - `filter.overallStatus` — restricts to studies that are actively recruiting, not yet recruiting,
# MAGIC   or currently active but not recruiting. Completed and terminated studies are retained in a separate
# MAGIC   pass because their eligibility criteria text still encodes the mutation-specific inclusion logic
# MAGIC   that informs the reading frame eligibility model. The Bronze layer ingests all statuses; status
# MAGIC   filtering happens at Silver.
# MAGIC
# MAGIC - `countTotal=true` — forces the API to return a `totalCount` field, which is not computed by
# MAGIC   default (it is expensive). Required once to size the ingestion pipeline; omitted on subsequent
# MAGIC   paginated pulls for performance.
# MAGIC
# MAGIC - `pageSize=10` — below the practical maximum of 1000; kept small here for exploration readability.
# MAGIC   Production ingestion will use pageSize=1000 to minimise request count against the 10 req/s limit.
# MAGIC
# MAGIC - `format=json` — the v2 API also supports CSV; JSON is required here to preserve nested structures
# MAGIC   (eligibility criteria, interventions, phases array) which are lost in flat CSV format.

# COMMAND ----------

# Fetch 10 DMD records — all statuses, no phase filter at Bronze (phase filtering is a Silver concern).
params = {
    "query.cond": "Duchenne Muscular Dystrophy",
    "pageSize": 10,
    "format": "json",
    "countTotal": "true",
}

response = requests.get(BASE_URL, params=params, timeout=30)
assert response.status_code == 200

data = response.json()
studies = data.get("studies", [])

print(f"Total DMD records in ClinicalTrials.gov : {data.get('totalCount', 'N/A')}")
print(f"Records fetched this page               : {len(studies)}")
print(f"nextPageToken                           : {data.get('nextPageToken', '<none>')}\n")

# Print a compact summary of the 10 records to confirm field availability.
for s in studies:
    id_mod = s["protocolSection"]["identificationModule"]
    status_mod = s["protocolSection"]["statusModule"]
    design_mod = s["protocolSection"].get("designModule", {})
    print(
        f"  {id_mod['nctId']} | "
        f"status={status_mod['overallStatus']} | "
        f"phases={design_mod.get('phases', ['N/A'])} | "
        f"title={id_mod.get('briefTitle', '')[:60]}"
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 3 — Response Schema Inspection
# MAGIC
# MAGIC The v2 API returns a two-section structure per study: `protocolSection` (investigator-submitted data)
# MAGIC and `derivedSection` (ClinicalTrials.gov-computed data including MeSH browse hierarchies). A boolean
# MAGIC `hasResults` flag indicates whether results have been posted.
# MAGIC
# MAGIC **Clinically meaningful fields for DMD eligibility matching:**
# MAGIC
# MAGIC | Field path | Clinical meaning | DMD use |
# MAGIC |---|---|---|
# MAGIC | `identificationModule.nctId` | Unique trial identifier | Primary join key across all tables |
# MAGIC | `identificationModule.briefTitle` | Short trial title | Human-readable trial identifier |
# MAGIC | `statusModule.overallStatus` | Current recruiting status | Filter at Silver; drives trial_eligibility_catalogue validity |
# MAGIC | `designModule.phases` | Trial phase (I / II / III / IV) | Phase filtering at Silver — mutation-specific trials typically Phase II–III |
# MAGIC | `eligibilityModule.eligibilityCriteria` | **Free-text inclusion/exclusion criteria** | **Most critical field** — contains the genetic mutation criteria (e.g. "amenable to exon 51 skipping", "confirmed deletion of exons 48-50") that must be parsed by the Silver NLP pipeline to populate `silver.eligibility_criteria` |
# MAGIC | `eligibilityModule.minimumAge` / `stdAges` | Patient age eligibility | Layer 3 patient-level criterion — AAV gene therapy trials frequently restrict to paediatric or ambulatory patients |
# MAGIC | `armsInterventionsModule.interventions` | Intervention names and types | Classifies trial as AON / gene therapy / CRISPR / small molecule — determines which Layer 2 eligibility rules apply |
# MAGIC | `sponsorCollaboratorsModule.leadSponsor.name` | Lead sponsor | Provenance; helps identify Sarepta / Nippon Shinyaku / NS Pharma trials by AON class |
# MAGIC | `statusModule.primaryCompletionDateStruct.date` | Expected or actual primary endpoint date | Trial timeline; used in `gold.patient_trial_eligibility_delta` to detect upcoming completions |
# MAGIC | `designModule.studyType` | Interventional vs observational | Filter at Bronze or Silver — only interventional studies matter for eligibility matching |
# MAGIC | `conditionsModule.conditions` | Condition list | Secondary confirmation of DMD vs BMD classification |
# MAGIC | `derivedSection.conditionBrowseModule` | MeSH condition hierarchy | Structured ontology enrichment usable for condition normalisation at Silver |
# MAGIC
# MAGIC **Fields likely always null or unreliable for DMD trials:**
# MAGIC - `eligibilityModule.healthyVolunteers` — almost universally false for DMD; low signal
# MAGIC - `ipdSharingStatementModule` — rarely populated; not needed for eligibility matching
# MAGIC - `referencesModule` — inconsistently populated; useful for research provenance but not for pipeline logic
# MAGIC
# MAGIC **Silver transformation complexity flags:**
# MAGIC - `eligibilityCriteria` is a single free-text blob. Genetic criteria are buried within it and require
# MAGIC   NLP extraction (regex patterns + LLM-assisted classification) at Silver. This is the highest
# MAGIC   complexity field in the schema.
# MAGIC - `interventions` is an array of objects; requires `EXPLODE` at Silver.
# MAGIC - `phases` is an array of strings; Phase III trials may list both PHASE2 and PHASE3.

# COMMAND ----------

# Inspect the full field structure of the first returned study.
first_study = studies[0]

def print_keys(d, prefix="", max_depth=3, current_depth=0):
    """Recursively print key paths and value types up to max_depth."""
    if current_depth >= max_depth:
        return
    if isinstance(d, dict):
        for k, v in d.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                print(f"  {path}  -> dict ({len(v)} keys)")
                print_keys(v, path, max_depth, current_depth + 1)
            elif isinstance(v, list):
                item_type = type(v[0]).__name__ if v else "empty"
                print(f"  {path}  -> list[{item_type}] (len={len(v)})")
                if v and isinstance(v[0], dict):
                    print_keys(v[0], f"{path}[0]", max_depth, current_depth + 1)
            else:
                print(f"  {path}  -> {type(v).__name__}: {repr(v)[:80]}")

print("=== Top-level study keys ===")
print_keys(first_study, max_depth=1)

print("\n=== protocolSection modules ===")
print_keys(first_study["protocolSection"], max_depth=2)

# COMMAND ----------

# Spot-check the eligibilityCriteria field — the most important field for DMD matching.
print("=== eligibilityCriteria sample (first 2 studies) ===\n")
for s in studies[:2]:
    nct = s["protocolSection"]["identificationModule"]["nctId"]
    elig = s["protocolSection"].get("eligibilityModule", {}).get("eligibilityCriteria", "<missing>")
    print(f"--- {nct} ---")
    print(elig[:800])
    print()

# COMMAND ----------

# Spot-check interventions field structure.
print("=== Interventions field structure (first 3 studies) ===\n")
for s in studies[:3]:
    nct = s["protocolSection"]["identificationModule"]["nctId"]
    arms_mod = s["protocolSection"].get("armsInterventionsModule", {})
    interventions = arms_mod.get("interventions", [])
    print(f"--- {nct} ---")
    for iv in interventions:
        print(f"  type={iv.get('type')} | name={iv.get('name', '')[:60]}")
    if not interventions:
        print("  <no interventions listed>")
    print()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 4 — Pagination Walkthrough
# MAGIC
# MAGIC The v2 API uses **cursor-based pagination** via a `nextPageToken` field returned at the top level of
# MAGIC each response. When `nextPageToken` is absent from the response, the final page has been reached.
# MAGIC
# MAGIC This is preferable to offset-based pagination for ingestion pipelines because:
# MAGIC - The cursor position is stable even if records are added or updated during a long-running fetch.
# MAGIC - There is no risk of offset drift causing duplicate or missing records across pages.
# MAGIC
# MAGIC **Ingestion volume estimate (as of 2026-06-06):**
# MAGIC - Total DMD records (all statuses): ~488
# MAGIC - Actively recruiting: ~63
# MAGIC - Active but not recruiting: ~28
# MAGIC - Not yet recruiting: ~21
# MAGIC - **Active pipeline-relevant records**: ~112 (recruiting + active + not-yet-recruiting)
# MAGIC - At pageSize=1000 this is a single request; at pageSize=100 it is 2 requests — well within the
# MAGIC   10 req/s rate limit.
# MAGIC
# MAGIC **Pagination gotcha observed**: the `totalCount` field is only returned when `countTotal=true` is
# MAGIC explicitly set in the request. Omitting it reduces response latency. In the production DLT pipeline,
# MAGIC include `countTotal=true` only on the first page fetch for logging; omit it on subsequent pages.
# MAGIC
# MAGIC **Re-ingestion strategy**: ClinicalTrials.gov does not expose a `lastModified` cursor in the v2 API
# MAGIC for incremental pulls. The recommended production approach is full-replacement Bronze ingestion
# MAGIC (truncate-and-reload) on a weekly cadence, with row-level deduplication and delta detection handled
# MAGIC at Silver using `nctId` as the primary key and `statusModule.statusVerifiedDate` as the change indicator.

# COMMAND ----------

# Walk 3 pages of DMD results using cursor-based pagination. pageSize=5 for readability.
PAGE_SIZE = 5
all_nct_ids = []
page_num = 0
next_token = None

while page_num < 3:
    params = {
        "query.cond": "Duchenne Muscular Dystrophy",
        "pageSize": PAGE_SIZE,
        "format": "json",
    }
    if next_token:
        params["pageToken"] = next_token

    resp = requests.get(BASE_URL, params=params, timeout=30)
    assert resp.status_code == 200, f"Page {page_num} failed: {resp.status_code}"
    page_data = resp.json()

    page_studies = page_data.get("studies", [])
    page_ids = [s["protocolSection"]["identificationModule"]["nctId"] for s in page_studies]
    all_nct_ids.extend(page_ids)

    print(f"Page {page_num}: fetched {len(page_studies)} studies | IDs: {page_ids}")

    next_token = page_data.get("nextPageToken")
    if not next_token:
        print("No nextPageToken — final page reached.")
        break

    page_num += 1
    time.sleep(0.1)  # Stay within 10 req/s rate limit.

print(f"\nTotal NCT IDs collected: {len(all_nct_ids)}")
print(f"Duplicates across pages: {len(all_nct_ids) - len(set(all_nct_ids))}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 5 — Data Quality First Look
# MAGIC
# MAGIC **Why data quality matters here specifically**: the `eligibilityCriteria` field is the single most
# MAGIC important field for this pipeline. If it is systematically absent, truncated, or inconsistently
# MAGIC structured, the Silver NLP pipeline cannot extract mutation-specific criteria, which breaks the entire
# MAGIC downstream matching chain. Quality issues in this field need `@dlt.expect_or_quarantine` rules in
# MAGIC the production DLT pipeline.
# MAGIC
# MAGIC **Key quality concerns to check:**
# MAGIC 1. **Null rate for `eligibilityCriteria`** — early-phase trials (Phase I) sometimes omit it. Phase II+
# MAGIC    trials almost always include it, but the text quality varies widely.
# MAGIC 2. **Null rate for `phases`** — observational studies and expanded access programmes often have
# MAGIC    `phases = ["NA"]` or are absent entirely. These should be quarantined at Silver.
# MAGIC 3. **Null rate for `primaryCompletionDateStruct`** — inconsistently populated for older registrations.
# MAGIC 4. **`overallStatus` controlled vocabulary** — must be one of the enumerated v2 status values;
# MAGIC    any deviation indicates a schema change in the API.
# MAGIC 5. **Date format consistency** — dates are returned as `YYYY-MM-DD` or `YYYY-MM` depending on the
# MAGIC    precision level specified by the registrant. Silver must handle both formats.
# MAGIC
# MAGIC **DLT quarantine rules implied by this analysis:**
# MAGIC - `@dlt.expect_or_quarantine("nct_id_not_null", "nctId IS NOT NULL")`
# MAGIC - `@dlt.expect_or_quarantine("eligibility_criteria_not_null", "eligibilityCriteria IS NOT NULL")`
# MAGIC - `@dlt.expect_or_warn("phase_not_na", "phases != ['NA']")` — warn only; Phase I records are
# MAGIC   valuable for provenance even if excluded from eligibility matching.
# MAGIC - `@dlt.expect_or_warn("primary_completion_date_not_null", "primaryCompletionDate IS NOT NULL")`

# COMMAND ----------

# Fetch a larger sample for quality analysis — 50 records across all DMD statuses.
SAMPLE_SIZE = 50
quality_params = {
    "query.cond": "Duchenne Muscular Dystrophy",
    "pageSize": SAMPLE_SIZE,
    "format": "json",
}
qresp = requests.get(BASE_URL, params=quality_params, timeout=30)
assert qresp.status_code == 200
qdata = qresp.json()
qstudies = qdata.get("studies", [])

print(f"Sample size: {len(qstudies)} studies\n")

# --- Null rate analysis ---
fields_to_check = {
    "nctId":                  lambda s: s["protocolSection"]["identificationModule"].get("nctId"),
    "briefTitle":             lambda s: s["protocolSection"]["identificationModule"].get("briefTitle"),
    "overallStatus":          lambda s: s["protocolSection"]["statusModule"].get("overallStatus"),
    "phases":                 lambda s: s["protocolSection"].get("designModule", {}).get("phases"),
    "eligibilityCriteria":    lambda s: s["protocolSection"].get("eligibilityModule", {}).get("eligibilityCriteria"),
    "leadSponsor":            lambda s: s["protocolSection"].get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
    "primaryCompletionDate":  lambda s: s["protocolSection"]["statusModule"].get("primaryCompletionDateStruct", {}).get("date") if s["protocolSection"]["statusModule"].get("primaryCompletionDateStruct") else None,
    "interventions":          lambda s: s["protocolSection"].get("armsInterventionsModule", {}).get("interventions"),
    "minimumAge":             lambda s: s["protocolSection"].get("eligibilityModule", {}).get("minimumAge"),
    "studyType":              lambda s: s["protocolSection"].get("designModule", {}).get("studyType"),
}

print("=== Null rates ===")
for field_name, extractor in fields_to_check.items():
    null_count = sum(1 for s in qstudies if not extractor(s))
    null_rate = null_count / len(qstudies) * 100
    print(f"  {field_name:<30} null={null_count}/{len(qstudies)} ({null_rate:.0f}%)")

# COMMAND ----------

# --- Value distributions for controlled vocabulary fields ---
from collections import Counter

print("\n=== overallStatus distribution ===")
statuses = [s["protocolSection"]["statusModule"].get("overallStatus", "MISSING") for s in qstudies]
for status, count in Counter(statuses).most_common():
    print(f"  {status:<35} {count}")

print("\n=== phases distribution ===")
all_phases = []
for s in qstudies:
    phases = s["protocolSection"].get("designModule", {}).get("phases", ["NA"])
    all_phases.extend(phases)
for phase, count in Counter(all_phases).most_common():
    print(f"  {phase:<20} {count}")

print("\n=== studyType distribution ===")
study_types = [s["protocolSection"].get("designModule", {}).get("studyType", "MISSING") for s in qstudies]
for st, count in Counter(study_types).most_common():
    print(f"  {st:<25} {count}")

# COMMAND ----------

# --- Date range of available data ---
dates = []
for s in qstudies:
    start = s["protocolSection"]["statusModule"].get("startDateStruct", {}).get("date")
    if start:
        dates.append(start)

if dates:
    dates.sort()
    print(f"\n=== Study start date range ===")
    print(f"  Earliest: {dates[0]}")
    print(f"  Latest  : {dates[-1]}")

# --- Eligibility criteria length distribution ---
print("\n=== eligibilityCriteria text length (chars) ===")
elig_lengths = []
for s in qstudies:
    elig = s["protocolSection"].get("eligibilityModule", {}).get("eligibilityCriteria")
    if elig:
        elig_lengths.append(len(elig))

if elig_lengths:
    print(f"  Min    : {min(elig_lengths)}")
    print(f"  Median : {sorted(elig_lengths)[len(elig_lengths)//2]}")
    print(f"  Max    : {max(elig_lengths)}")
    print(f"  Present: {len(elig_lengths)}/{len(qstudies)}")

# COMMAND ----------

# --- Flag malformed or unexpected values ---
print("\n=== Potential quality flags ===")
for s in qstudies:
    nct = s["protocolSection"]["identificationModule"].get("nctId", "MISSING")
    issues = []

    # Missing eligibility criteria in an interventional study.
    if s["protocolSection"].get("designModule", {}).get("studyType") == "INTERVENTIONAL":
        elig = s["protocolSection"].get("eligibilityModule", {}).get("eligibilityCriteria")
        if not elig:
            issues.append("MISSING_ELIGIBILITY_CRITERIA")

    # Phase NA in an interventional study.
    phases = s["protocolSection"].get("designModule", {}).get("phases", [])
    if "NA" in phases and s["protocolSection"].get("designModule", {}).get("studyType") == "INTERVENTIONAL":
        issues.append("PHASE_NA_INTERVENTIONAL")

    # Suspiciously short eligibility criteria (< 100 chars likely truncated or placeholder).
    elig = s["protocolSection"].get("eligibilityModule", {}).get("eligibilityCriteria", "")
    if elig and len(elig) < 100:
        issues.append(f"SHORT_ELIGIBILITY_CRITERIA(len={len(elig)})")

    if issues:
        print(f"  {nct}: {', '.join(issues)}")

print("\nQuality flag scan complete.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 6 — Bronze Schema Sketch
# MAGIC
# MAGIC The proposed Bronze schema for `clinical.bronze.clinicaltrials_raw` stores the full API response
# MAGIC as a raw JSON string alongside a set of top-level extracted columns that enable efficient partitioning
# MAGIC and filtering without parsing the nested JSON at every query.
# MAGIC
# MAGIC **Column presence convention:**
# MAGIC - `[ALWAYS]` — present in every response record; safe to use as NOT NULL constraint.
# MAGIC - `[OPTIONAL]` — frequently missing; Silver must handle nulls.
# MAGIC - `[NESTED]` — requires `from_json` + `EXPLODE` or `LATERAL VIEW` at Silver; stored as STRING in Bronze.
# MAGIC
# MAGIC | Column name | Source field path | Presence | Silver complexity | Use case |
# MAGIC |---|---|---|---|---|
# MAGIC | `nct_id` | `identificationModule.nctId` | ALWAYS | Low — direct extract | Primary key; join key for all downstream tables |
# MAGIC | `brief_title` | `identificationModule.briefTitle` | ALWAYS | Low | Human-readable display; trial search |
# MAGIC | `official_title` | `identificationModule.officialTitle` | OPTIONAL | Low | More precise title; NLP input |
# MAGIC | `overall_status` | `statusModule.overallStatus` | ALWAYS | Low — controlled vocab | Silver filter; trial_eligibility_catalogue validity |
# MAGIC | `phases_raw` | `designModule.phases` | OPTIONAL | Medium — array | Silver phase filter (Phase II–IV inclusion) |
# MAGIC | `study_type` | `designModule.studyType` | OPTIONAL | Low | Silver filter — INTERVENTIONAL only |
# MAGIC | `eligibility_criteria_text` | `eligibilityModule.eligibilityCriteria` | OPTIONAL | **HIGH — NLP required** | Core input to mutation criterion extraction at Silver |
# MAGIC | `minimum_age` | `eligibilityModule.minimumAge` | OPTIONAL | Low | Layer 3 patient criterion |
# MAGIC | `std_ages_raw` | `eligibilityModule.stdAges` | OPTIONAL | Medium — array | Layer 3 patient criterion (CHILD / ADULT / OLDER_ADULT) |
# MAGIC | `lead_sponsor_name` | `sponsorCollaboratorsModule.leadSponsor.name` | OPTIONAL | Low | Provenance; sponsor-level grouping |
# MAGIC | `lead_sponsor_class` | `sponsorCollaboratorsModule.leadSponsor.class` | OPTIONAL | Low | Industry vs NIH vs other |
# MAGIC | `primary_completion_date` | `statusModule.primaryCompletionDateStruct.date` | OPTIONAL | Low — date parse | Timeline; trial_eligibility_delta |
# MAGIC | `start_date` | `statusModule.startDateStruct.date` | OPTIONAL | Low — date parse | Trial age; ingestion freshness check |
# MAGIC | `enrollment_count` | `designModule.enrollmentInfo.count` | OPTIONAL | Low | Cohort size estimate |
# MAGIC | `interventions_raw` | `armsInterventionsModule.interventions` | OPTIONAL | **HIGH — EXPLODE** | Intervention type classification at Silver |
# MAGIC | `conditions_raw` | `conditionsModule.conditions` | OPTIONAL | Medium — array | Secondary condition confirmation |
# MAGIC | `brief_summary` | `descriptionModule.briefSummary` | OPTIONAL | Low | NLP enrichment; keyword extraction |
# MAGIC | `mesh_conditions_raw` | `derivedSection.conditionBrowseModule` | OPTIONAL | HIGH — nested | MeSH ontology enrichment at Silver |
# MAGIC | `mesh_interventions_raw` | `derivedSection.interventionBrowseModule` | OPTIONAL | HIGH — nested | MeSH intervention classification |
# MAGIC | `has_results` | `hasResults` | ALWAYS | Low | Filter for completed trials with posted results |
# MAGIC | `raw_json` | full study object | ALWAYS | N/A | Full fidelity archive; re-parse without re-ingestion |
# MAGIC | `source_system` | hardcoded | ALWAYS | N/A | Provenance |
# MAGIC | `ingestion_timestamp` | runtime | ALWAYS | N/A | ALCOA+ contemporaneous provenance |
# MAGIC | `api_version` | hardcoded | ALWAYS | N/A | Schema version tracking |
# MAGIC | `source_url` | constructed from nctId | ALWAYS | N/A | Attributable provenance link |
# MAGIC
# MAGIC **Silver transformation complexity summary:**
# MAGIC - `eligibility_criteria_text`: highest complexity — regex + LLM-assisted NLP to split into
# MAGIC   `mutation_criteria` and `patient_criteria` rows in `silver.eligibility_criteria`.
# MAGIC - `interventions_raw`: requires `EXPLODE` then classification logic (AON / gene therapy / CRISPR /
# MAGIC   small molecule) to populate `silver.trials_dmd.intervention_class`.
# MAGIC - `mesh_conditions_raw` / `mesh_interventions_raw`: deeply nested; useful for ontology enrichment
# MAGIC   but not on the critical path for the first Silver release.

# COMMAND ----------

# Materialise the Bronze schema sketch as a sample DataFrame showing extracted top-level columns.
import json

rows = []
for s in qstudies:
    id_mod = s["protocolSection"]["identificationModule"]
    status_mod = s["protocolSection"]["statusModule"]
    design_mod = s["protocolSection"].get("designModule", {})
    elig_mod = s["protocolSection"].get("eligibilityModule", {})
    sponsor_mod = s["protocolSection"].get("sponsorCollaboratorsModule", {})
    desc_mod = s["protocolSection"].get("descriptionModule", {})

    row = {
        "nct_id":                    id_mod.get("nctId"),
        "brief_title":               id_mod.get("briefTitle"),
        "overall_status":            status_mod.get("overallStatus"),
        "phases_raw":                json.dumps(design_mod.get("phases")),
        "study_type":                design_mod.get("studyType"),
        "eligibility_criteria_text": elig_mod.get("eligibilityCriteria"),
        "minimum_age":               elig_mod.get("minimumAge"),
        "lead_sponsor_name":         sponsor_mod.get("leadSponsor", {}).get("name"),
        "primary_completion_date":   status_mod.get("primaryCompletionDateStruct", {}).get("date") if status_mod.get("primaryCompletionDateStruct") else None,
        "has_results":               s.get("hasResults", False),
        "raw_json":                  json.dumps(s),  # Full fidelity archive.
    }
    rows.append(row)

# Display first 5 rows (top-level columns only, truncate long text fields).
print(f"Bronze schema sample — {len(rows)} rows\n")
print(f"{'nct_id':<15} {'overall_status':<30} {'study_type':<20} {'has_results':<12} {'elig_criteria_len'}")
print("-" * 100)
for r in rows[:5]:
    elig_len = len(r["eligibility_criteria_text"]) if r["eligibility_criteria_text"] else 0
    print(
        f"{str(r['nct_id']):<15} "
        f"{str(r['overall_status']):<30} "
        f"{str(r['study_type']):<20} "
        f"{str(r['has_results']):<12} "
        f"{elig_len}"
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 7 — Provenance Metadata
# MAGIC
# MAGIC Clinical data integrity standards require **ALCOA+ provenance** — data that is Attributable,
# MAGIC Legible, Contemporaneous, Original, and Accurate, plus Complete, Consistent, Enduring, and Available.
# MAGIC These principles were established for GCP (Good Clinical Practice) in pharmaceutical trials and are
# MAGIC directly applicable to data infrastructure feeding a clinical trial matching system.
# MAGIC
# MAGIC **Why ALCOA+ matters for this source specifically:**
# MAGIC - **Attributable**: every Bronze record must be traceable to the exact API call that produced it.
# MAGIC   The `source_url` field (constructed as `https://clinicaltrials.gov/study/{nctId}`) provides this.
# MAGIC - **Contemporaneous**: the `ingestion_timestamp` records when the record was fetched. ClinicalTrials.gov
# MAGIC   updates trial records continuously; two ingestions of the same NCT ID on different dates may return
# MAGIC   different eligibility criteria text (e.g., amended criteria after protocol modification). Without
# MAGIC   the timestamp, it is impossible to know which version of the eligibility text a downstream verdict
# MAGIC   was computed from — a critical audit requirement if this data product informs patient care.
# MAGIC - **Original**: the `raw_json` column stores the complete, unmodified API response. No transformation
# MAGIC   is applied at Bronze. This ensures that if a Silver transformation introduces a parsing error, the
# MAGIC   original data can be re-processed without re-ingestion.
# MAGIC - **Versioned**: the `api_version` field records the API version (`v2`) so that schema changes (if
# MAGIC   ClinicalTrials.gov ever releases v3) are detectable in the Bronze table without examining code history.
# MAGIC
# MAGIC **Production implementation note:** in the DLT pipeline, provenance columns will be added as computed
# MAGIC columns in the `@dlt.table` decorator, not inside the transformation logic, so they cannot be omitted
# MAGIC or overwritten by a data processing error.

# COMMAND ----------

from datetime import datetime, timezone

def attach_provenance(record: dict, nct_id: str) -> dict:
    """Attach ALCOA+ provenance metadata to a Bronze record."""
    record["source_system"]        = "clinicaltrials_gov"
    record["api_version"]          = "v2"
    record["ingestion_timestamp"]  = datetime.now(timezone.utc).isoformat()
    record["source_url"]           = f"https://clinicaltrials.gov/study/{nct_id}"
    return record

# Demonstrate provenance attachment on the first sample record.
sample_provenance = attach_provenance(
    {
        "nct_id":    rows[0]["nct_id"],
        "raw_json":  "<truncated for display>",
    },
    rows[0]["nct_id"],
)

print("=== Provenance metadata sample ===")
for k, v in sample_provenance.items():
    print(f"  {k:<25} : {v}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 8 — Write to Personal Schema
# MAGIC
# MAGIC Persists the Bronze schema sample to `workspace.steff_horemans.bronze_clinicaltrials_raw`
# MAGIC for interactive Silver prototyping and eligibility parsing experiments. This table lives in
# MAGIC the ungoverned personal schema — it is **never imported from production pipelines** (ADR-01).
# MAGIC
# MAGIC The schema `workspace.steff_horemans` is created here if it does not already exist, and set
# MAGIC as the default for this session so subsequent `SELECT` and `DESCRIBE` calls can omit the catalog prefix.

# COMMAND ----------

from databricks.connect import DatabricksSession  # noqa: E402

# Connects to the remote cluster configured in Databricks Connect.
# Requires a running cluster; execution happens on Databricks, not locally.
spark = DatabricksSession.builder.profile("steff_horemans").serverless(True).getOrCreate()
# Alternative if serverless is not available:
# spark = DatabricksSession.builder.profile("steff_horemans").clusterId("<cluster-id>").getOrCreate()

spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.steff_horemans")
spark.sql("USE workspace.steff_horemans")

df = spark.createDataFrame(rows)
(
    df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.steff_horemans.bronze_clinicaltrials_raw")
)

print(f"Written {df.count()} rows to workspace.steff_horemans.bronze_clinicaltrials_raw")
spark.sql("DESCRIBE TABLE bronze_clinicaltrials_raw").show(truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Appendix — Production Ingestion Sketch (DLT)
# MAGIC
# MAGIC The following is a non-executable reference sketch showing how the Bronze DLT table would be defined.
# MAGIC It is included here as a guide for the pipeline author — it is **not** part of this exploration
# MAGIC notebook's executable cells.
# MAGIC
# MAGIC ```python
# MAGIC import dlt
# MAGIC from pyspark.sql import functions as F
# MAGIC from datetime import datetime, timezone
# MAGIC
# MAGIC CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"
# MAGIC CTGOV_PARAMS = {
# MAGIC     "query.cond": "Duchenne Muscular Dystrophy",
# MAGIC     "pageSize": 1000,
# MAGIC     "format": "json",
# MAGIC }
# MAGIC
# MAGIC @dlt.table(
# MAGIC     name="clinicaltrials_raw",
# MAGIC     comment="Bronze layer: raw ClinicalTrials.gov v2 API responses for all DMD-matched studies.",
# MAGIC     table_properties={"quality": "bronze", "pipelines.autoOptimize.managed": "true"},
# MAGIC )
# MAGIC @dlt.expect_or_quarantine("nct_id_not_null", "nct_id IS NOT NULL")
# MAGIC @dlt.expect_or_quarantine("eligibility_criteria_not_null", "eligibility_criteria_text IS NOT NULL")
# MAGIC @dlt.expect_or_warn("phase_not_na", "phases_raw != '[\"NA\"]'")
# MAGIC def clinicaltrials_raw():
# MAGIC     # ... pagination loop producing rows ...
# MAGIC     # ... attach provenance via attach_provenance() ...
# MAGIC     # ... return spark.createDataFrame(rows, schema=BRONZE_SCHEMA) ...
# MAGIC     pass
# MAGIC ```


