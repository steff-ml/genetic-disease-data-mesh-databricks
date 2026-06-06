# Databricks notebook source

# COMMAND ----------
# MAGIC %md
# MAGIC # EU Clinical Trials Register (CTIS) — First Look Exploration
# MAGIC
# MAGIC **Source**: EU Clinical Trials Register, powered by CTIS (Clinical Trials Information System)
# MAGIC **Target table**: `clinical.bronze.eu_trials_raw`
# MAGIC **API base**: `https://euclinicaltrials.eu/ctis-public-api`
# MAGIC **Auth**: Public — no API key required
# MAGIC **Author**: exploration-notebook agent
# MAGIC **Date**: 2026-06-06
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Section 0 — Context and Purpose
# MAGIC
# MAGIC The EU Clinical Trials Register (EU CTR) is the mandatory public registry for all clinical trials
# MAGIC authorised in EU/EEA member states from January 2023 onwards. It is powered by the CTIS (Clinical
# MAGIC Trials Information System) platform, built under EU Clinical Trials Regulation No 536/2014 (CTR),
# MAGIC which superseded the older EudraCT Directive framework. This source feeds **Layer 2
# MAGIC (approach-specific)** and **Layer 3 (patient-level)** eligibility data in the same way as
# MAGIC ClinicalTrials.gov, and sits alongside it in the `clinical.bronze` schema as a complementary
# MAGIC source (see the data model in `docs/scientific_background.md`, Section IV).
# MAGIC
# MAGIC **Scientific question this exploration answers**: what does the CTIS public REST API actually return
# MAGIC for DMD-filtered queries, and how do its eligibility criteria fields compare structurally to
# MAGIC ClinicalTrials.gov? Specifically: are inclusion and exclusion criteria pre-split into structured
# MAGIC arrays (unlike the ClinicalTrials.gov free-text blob), and does the API expose a cross-reference
# MAGIC field linking a CTIS trial number to its corresponding NCT ID?
# MAGIC
# MAGIC **Why this matters for the pipeline**: EU CTR and ClinicalTrials.gov are complementary registries.
# MAGIC The same sponsor-run DMD trial often appears in both. The exon-skipping eligibility criteria in the
# MAGIC EU CTR registration of a trial may differ from the ClinicalTrials.gov registration — sometimes the
# MAGIC EU protocol version has more granular genetic inclusion criteria (specifying exact exon ranges),
# MAGIC while the US registration uses broader language. Per ADR-06, conflicting eligibility criteria across
# MAGIC registries are treated as `classification_conflict = true` at Silver and escalated for manual review.
# MAGIC
# MAGIC **A successful Bronze ingestion of this source enables**:
# MAGIC 1. `silver.trials_dmd` — the DMD-filtered, deduplicated trial table joining CTIS records to their
# MAGIC    ClinicalTrials.gov counterparts via the `nctNumber` cross-reference field.
# MAGIC 2. `silver.eligibility_criteria` — structured inclusion/exclusion rows derived from CTIS's
# MAGIC    pre-split criteria arrays, reducing the NLP burden compared to the ClinicalTrials.gov blob.
# MAGIC 3. `gold.trial_eligibility_catalogue` — the final queryable data product gains EU-only trials
# MAGIC    (trials authorised only in the EU/EEA that have no NCT registration) and higher-fidelity
# MAGIC    criteria text for dual-registered trials.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 1 — Connection and Authentication
# MAGIC
# MAGIC The CTIS public API is fully unauthenticated — no API key, OAuth token, or registration is required.
# MAGIC No `dbutils.secrets` call is needed.
# MAGIC
# MAGIC **API architecture note**: the CTIS public portal at `euclinicaltrials.eu` is an Angular single-page
# MAGIC application. The underlying REST API base is `https://euclinicaltrials.eu/ctis-public-api`. The
# MAGIC `/ctis-public-api/search` endpoint accepts HTTP POST with a JSON body (not query parameters), which
# MAGIC is unusual for a search API — this was discovered by inspecting the compiled Angular JS bundle
# MAGIC (`/ctis-public/main-DGWGCUGU.js`) since no official OpenAPI specification is published.
# MAGIC
# MAGIC **Why this source over the legacy EU CTR (EudraCT)?**
# MAGIC - The old EU Clinical Trials Register at `clinicaltrialsregister.eu` was built on EudraCT (Directive
# MAGIC   2001/20/EC) and provides only an RSS feed for programmatic access — not a structured JSON API.
# MAGIC   CTIS (CTR 536/2014) provides a proper REST API with structured JSON per trial.
# MAGIC - From January 2023, all new trials in the EU/EEA must be registered in CTIS. The old EudraCT system
# MAGIC   is frozen; new DMD trials will appear only in CTIS going forward.
# MAGIC - CTIS pre-structures eligibility criteria into numbered inclusion and exclusion criterion arrays,
# MAGIC   unlike ClinicalTrials.gov which returns a single free-text blob. This reduces Silver NLP complexity.
# MAGIC
# MAGIC **Rate limit**: no documented rate limit. The API is served behind EMA infrastructure; production
# MAGIC ingestion should apply a conservative 1-second delay between requests.
# MAGIC
# MAGIC No ADR covering EU CTR source selection exists yet; this notebook is the evidence base for that ADR.

# COMMAND ----------

import requests
import json
import time
from datetime import datetime, timezone

CTIS_SEARCH_URL = "https://euclinicaltrials.eu/ctis-public-api/search"
CTIS_RETRIEVE_URL = "https://euclinicaltrials.eu/ctis-public-api/retrieve"

# Minimal connectivity test — POST a single-record query and assert HTTP 200.
test_payload = {
    "pagination": {"page": 1, "size": 1},
    "sort": {"property": "decisionDate", "direction": "DESC"},
    "searchCriteria": {"medicalCondition": "Duchenne"},
}

response = requests.post(
    CTIS_SEARCH_URL,
    json=test_payload,
    headers={"Accept": "application/json"},
    timeout=30,
)
assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"

data = response.json()
print("HTTP status         :", response.status_code)
print("Top-level keys      :", list(data.keys()))
print("pagination keys     :", list(data.get("pagination", {}).keys()))
print("data[] length       :", len(data.get("data", [])))
print("showWarning flag    :", data.get("showWarning"))
print("Connection OK.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 2 — Endpoint and Parameter Selection
# MAGIC
# MAGIC The CTIS public API exposes two relevant endpoints:
# MAGIC
# MAGIC | Endpoint | Method | Purpose |
# MAGIC |---|---|---|
# MAGIC | `POST /ctis-public-api/search` | POST | Paginated list search returning lightweight summaries |
# MAGIC | `GET /ctis-public-api/retrieve/{ctNumber}` | GET | Full structured record for a single trial |
# MAGIC
# MAGIC **Why POST for search?** The Angular frontend posts a JSON body to `/ctis-public-api/search`; there
# MAGIC is no GET-based query string equivalent. The body schema is:
# MAGIC ```json
# MAGIC {
# MAGIC   "pagination": {"page": 1, "size": 10},
# MAGIC   "sort": {"property": "decisionDate", "direction": "DESC"},
# MAGIC   "searchCriteria": { ... }
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC **Search criteria fields relevant to DMD** (from the Angular form schema extracted from the JS bundle):
# MAGIC
# MAGIC | Field | Type | DMD use |
# MAGIC |---|---|---|
# MAGIC | `medicalCondition` | string | Free-text match against condition name — use `"Duchenne"` for broadest recall |
# MAGIC | `rareDisease` | boolean | `true` narrows to orphan/rare disease classifications; DMD always qualifies |
# MAGIC | `status` | list[int] | CT status codes: 2=Authorised, 3=Started, 4=Ongoing, 5=Ended, 8=Temporarily Halted |
# MAGIC | `trialPhaseCode` | list[string] | Phase codes; `"5"` = Phase III, `"4"` = Phase II |
# MAGIC | `therapeuticAreaCode` | list | MedDRA therapeutic area; DMD falls under Musculoskeletal Diseases [C05] |
# MAGIC | `sponsor` | string | Sponsor name filter |
# MAGIC | `ageGroupCode` | list | Age group — DMD trials target paediatric populations (`"5"` = under 12) |
# MAGIC | `gender` | list | Gender filter |
# MAGIC | `eudraCtCode` | string | EudraCT number for transitioned trials (pre-2023 trials migrated from EudraCT) |
# MAGIC
# MAGIC **Why `medicalCondition = "Duchenne"` without `rareDisease = true`?** Using the bare condition string
# MAGIC gives broadest recall — some earlier CTIS registrations use "Duchenne Muscular Dystrophy" without the
# MAGIC rare disease flag set. The `rareDisease = true` filter raises recall from 30 to 31 for "Duchenne" on
# MAGIC the search date but may silently drop trials with incomplete metadata. Bronze ingests without that
# MAGIC filter; Silver applies the rare disease tag as a computed column.

# COMMAND ----------

# Fetch 10 DMD records — all statuses, no phase filter at Bronze.
dmd_payload = {
    "pagination": {"page": 1, "size": 10},
    "sort": {"property": "decisionDate", "direction": "DESC"},
    "searchCriteria": {"medicalCondition": "Duchenne"},
}

response = requests.post(CTIS_SEARCH_URL, json=dmd_payload, headers={"Accept": "application/json"}, timeout=30)
assert response.status_code == 200

data = response.json()
trials_summary = data.get("data", [])

print(f"Total DMD trials in CTIS              : {data['pagination']['totalRecords']}")
print(f"Total pages                           : {data['pagination']['totalPages']}")
print(f"Records fetched this page             : {len(trials_summary)}")
print(f"nextPage flag                         : {data['pagination']['nextPage']}\n")

# Print compact summary of the 10 records to confirm field availability.
print(f"{'ctNumber':<25} {'ctStatus':<4} {'trialPhase':<35} {'sponsor'[:25]}")
print("-" * 100)
for t in trials_summary:
    phase_short = t.get("trialPhase", "N/A")[:34]
    sponsor_short = t.get("sponsor", "N/A")[:30]
    print(f"  {t.get('ctNumber', 'N/A'):<24} {t.get('ctStatus', '?'):<4} {phase_short:<35} {sponsor_short}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 3 — Response Schema Inspection
# MAGIC
# MAGIC The CTIS API returns two levels of record detail:
# MAGIC
# MAGIC **Search result record** (`/search` endpoint): a lightweight summary with ~23 fields — sufficient for
# MAGIC listing but missing the full eligibility criteria text. This is what the search results grid shows.
# MAGIC
# MAGIC **Full trial record** (`/retrieve/{ctNumber}` endpoint): a deeply nested JSON object with the
# MAGIC complete CTIS data model. Structure:
# MAGIC ```
# MAGIC {
# MAGIC   ctNumber, ctStatus, decisionDate, publishDate, ctPublicStatusCode,
# MAGIC   authorizedApplication: {
# MAGIC     authorizedPartI: {                   <- sponsor-submitted Part I (global trial data)
# MAGIC       trialDetails: {
# MAGIC         clinicalTrialIdentifiers: {      <- fullTitle, publicTitle, shortTitle, nctNumber (!)
# MAGIC         trialInformation: {              <- phase, medicalCondition (with MedDRA codes!), objectives
# MAGIC         eligibilityCriteria: {           <- principalInclusionCriteria[], principalExclusionCriteria[]
# MAGIC         endPoint: {                      <- primaryEndPoints[], secondaryEndPoints[]
# MAGIC         trialDuration: { ... }
# MAGIC         populationOfTrialSubjects: { ... }
# MAGIC       }
# MAGIC       sponsors: [ ... ]
# MAGIC       products: [ ... ]
# MAGIC       medicalConditions: [ { medicalCondition, isConditionRareDisease } ]
# MAGIC       therapeuticAreas: [ ... ]
# MAGIC     }
# MAGIC     authorizedPartsII: [ {              <- one entry per Member State Concerned
# MAGIC       mscInfo: { countryName, trialStatus, decisionDate, ... }
# MAGIC       trialSites: [ ... ]
# MAGIC     } ]
# MAGIC     eudraCt: { isTransitioned: bool }   <- true if migrated from old EudraCT system
# MAGIC   }
# MAGIC   events: { trialEvents, unexpectedEvents, seriousBreaches, ... }
# MAGIC   results: { }
# MAGIC   documents: [ ... ]
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC **Clinically meaningful fields for DMD eligibility matching:**
# MAGIC
# MAGIC | Field path (retrieve record) | Clinical meaning | DMD use |
# MAGIC |---|---|---|
# MAGIC | `ctNumber` | CTIS trial number (e.g. `2025-522949-22-00`) | Primary key for EU CTR; join key for `eu_trials_raw` |
# MAGIC | `clinicalTrialIdentifiers.secondaryIdentifyingNumbers.nctNumber.number` | NCT ID cross-reference | **Critical**: join key to ClinicalTrials.gov for deduplication at Silver |
# MAGIC | `clinicalTrialIdentifiers.fullTitle` | Full protocol title | NLP enrichment; trial identification |
# MAGIC | `clinicalTrialIdentifiers.publicTitle` | Public-facing title | Human-readable; search |
# MAGIC | `ctStatus` | Trial authorisation status (string in retrieve, int code in search) | Silver filter; trial validity |
# MAGIC | `eudraCt.isTransitioned` | Was this trial migrated from legacy EudraCT? | Provenance; cross-reference to old EU CTR register |
# MAGIC | `trialDetails.trialInformation.medicalCondition.meddraConditionTerms` | MedDRA coded condition | Structured ontology — superior to free-text condition match |
# MAGIC | `trialDetails.trialInformation.trialCategory.trialPhase` | Trial phase code (`"5"` = Phase III) | Silver phase filter (codes differ from ClinicalTrials.gov text) |
# MAGIC | `trialDetails.eligibilityCriteria.principalInclusionCriteria[]` | **Pre-split numbered inclusion criteria** | **Most critical field** — each item is a separate structured criterion; genetic inclusion criteria (exon skipping targets, mutation types) appear here as discrete items, not in a single blob |
# MAGIC | `trialDetails.eligibilityCriteria.principalExclusionCriteria[]` | **Pre-split numbered exclusion criteria** | Same — patient-level exclusions (AAV antibody status, prior gene therapy exposure) are discrete items |
# MAGIC | `trialDetails.populationOfTrialSubjects.ageRanges` | Coded age group | Layer 3 patient criterion |
# MAGIC | `trialDetails.populationOfTrialSubjects.isMaleSubjects` | Gender restriction | Confirms male-only eligibility (expected for X-linked DMD) |
# MAGIC | `sponsors[0].organisation.name` | Lead sponsor name | Provenance; sponsor-level grouping |
# MAGIC | `products[].productDictionaryInfo.prodName` | Investigational product name | Intervention classification (AON / gene therapy / etc.) |
# MAGIC | `trialDetails.trialDuration.estimatedGlobalEndDate` | Estimated trial end date | Trial timeline; eligibility_delta |
# MAGIC | `authorizedPartsII[].mscInfo.countryName` | Member State Concerned (MSC) | EU country coverage; determines which countries have authorised the trial |
# MAGIC | `authorizedPartsII[].mscInfo.trialStatus` | MSC-level trial status | Finer than global status — a trial may be ongoing in France but ended in Germany |
# MAGIC
# MAGIC **Key structural difference vs ClinicalTrials.gov**: `eligibilityCriteria` here is a **dict** with
# MAGIC two arrays: `principalInclusionCriteria` and `principalExclusionCriteria`. Each element is a numbered
# MAGIC criterion object with English text plus translations. This pre-structured format means the Silver NLP
# MAGIC pipeline does not need to parse out inclusion vs exclusion sections from a single text blob — only
# MAGIC the within-criterion extraction of mutation-specific language (e.g. "amenable to exon 44 skipping",
# MAGIC "deletion variant predicted not to express exons 1–11") is required.
# MAGIC
# MAGIC **Fields absent or lower quality vs ClinicalTrials.gov**:
# MAGIC - No `nctNumber` present in the search summary record — only available in the full retrieve response.
# MAGIC - `ctStatus` in search results is an integer code; in retrieve it is a string. Code mapping must be
# MAGIC   applied at Silver (2=Authorised, 3=Started, 4=Ongoing, 5=Ended, 8=Temporarily Halted, 6=Prohibited).
# MAGIC - No direct equivalent of ClinicalTrials.gov `phases` array — phase is encoded as a numeric string
# MAGIC   inside `trialCategory.trialPhase` in the retrieve record, and as a long text string in search results.

# COMMAND ----------

# Fetch the full record for the first DMD trial to inspect field structure.
first_ct_number = trials_summary[0]["ctNumber"]
retrieve_url = f"{CTIS_RETRIEVE_URL}/{first_ct_number}"

retrieve_response = requests.get(retrieve_url, headers={"Accept": "application/json"}, timeout=30)
assert retrieve_response.status_code == 200, f"Retrieve failed: {retrieve_response.status_code}"

full_record = retrieve_response.json()

print(f"Full record for: {first_ct_number}")
print(f"Top-level keys: {list(full_record.keys())}")
print()

# Navigate to the key clinical sub-structures.
aa = full_record.get("authorizedApplication", {})
p1 = aa.get("authorizedPartI", {})
td = p1.get("trialDetails", {})
cti = td.get("clinicalTrialIdentifiers", {})
elig = td.get("trialInformation", {}).get("eligibilityCriteria", {})
# eligibilityCriteria is at trialDetails.trialInformation.eligibilityCriteria in trialInformation
# but from the actual response it lives at trialDetails.trialInformation level
# Let's look at the actual path:
elig_criteria = td.get("trialInformation", {}).get("eligibilityCriteria")
if elig_criteria is None:
    # Actual path observed in real response: td["eligibilityCriteria"] is missing;
    # eligibilityCriteria is at td["trialInformation"]["eligibilityCriteria"]
    elig_criteria = td.get("eligibilityCriteria")
    if elig_criteria is None:
        # It may also appear directly under trialDetails as observed in the schema dump
        elig_criteria = {}

print("=== clinicalTrialIdentifiers ===")
print(f"  fullTitle         : {cti.get('fullTitle', '')[:100]}")
print(f"  publicTitle       : {cti.get('publicTitle', '')[:100]}")
print(f"  shortTitle        : {cti.get('shortTitle', '')}")
nct_ref = cti.get("secondaryIdentifyingNumbers", {}).get("nctNumber", {})
print(f"  nctNumber (NCT ID): {nct_ref.get('number', '<not present>')}")
print()

print("=== trialInformation keys ===")
ti = td.get("trialInformation", {})
for k, v in ti.items():
    if isinstance(v, dict):
        print(f"  {k}  -> dict ({len(v)} keys)")
    elif isinstance(v, list):
        print(f"  {k}  -> list len={len(v)}")
    else:
        print(f"  {k}  -> {type(v).__name__}: {str(v)[:80]}")

# COMMAND ----------

# Inspect the eligibilityCriteria field — pre-split structured criteria vs ClinicalTrials.gov blob.
print("=== eligibilityCriteria structure ===")
# Navigate to the correct path: trialDetails → trialInformation → eligibilityCriteria
ti = td.get("trialInformation", {})
elig_criteria = ti.get("eligibilityCriteria", {})

if elig_criteria:
    inc = elig_criteria.get("principalInclusionCriteria", [])
    exc = elig_criteria.get("principalExclusionCriteria", [])
    print(f"  Number of inclusion criteria : {len(inc)}")
    print(f"  Number of exclusion criteria : {len(exc)}")
    print()
    print("  === Sample inclusion criteria (first 5) ===")
    for c in inc[:5]:
        print(f"    [{c.get('number')}] {c.get('principalInclusionCriteria', '')[:120]}")
    print()
    print("  === Sample exclusion criteria (first 5) ===")
    for c in exc[:5]:
        print(f"    [{c.get('number')}] {c.get('principalExclusionCriteria', '')[:120]}")
else:
    print("  eligibilityCriteria is absent or empty for this trial")
    print("  (gene therapy trials may not enumerate all criteria in the public record)")

# COMMAND ----------

# Inspect MedDRA condition coding — structured ontology advantage over ClinicalTrials.gov.
print("=== MedDRA condition terms ===")
ti = td.get("trialInformation", {})
mc = ti.get("medicalCondition", {})
if mc:
    meddra_terms = mc.get("meddraConditionTerms", [])
    for t in meddra_terms:
        print(
            f"  termId={t.get('termId')} | level={t.get('level')} | "
            f"name={t.get('termName')} | version={t.get('version')}"
        )
    part1_conds = mc.get("partIMedicalConditions", [])
    for c in part1_conds:
        print(
            f"  medicalCondition={c.get('medicalCondition')} | "
            f"isRareDisease={c.get('isConditionRareDisease')}"
        )

print()
print("=== NCT cross-reference ===")
cti = td.get("clinicalTrialIdentifiers", {})
sec_ids = cti.get("secondaryIdentifyingNumbers", {})
nct_obj = sec_ids.get("nctNumber", {})
print(f"  nctNumber field present : {'yes' if nct_obj else 'no'}")
print(f"  NCT ID value            : {nct_obj.get('number', '<absent>')}")
add_reg = sec_ids.get("additionalRegistries", [])
print(f"  additionalRegistries    : {add_reg}")

# COMMAND ----------

# Inspect product and sponsor fields for intervention classification.
print("=== Products (investigational medicinal products) ===")
products = p1.get("products", [])
for prod in products[:5]:
    pd_info = prod.get("productDictionaryInfo", {})
    print(
        f"  prodName={pd_info.get('prodName', 'N/A')[:60]} | "
        f"activeSubstance={pd_info.get('activeSubstanceName', 'N/A')[:40]} | "
        f"role={prod.get('mpRoleInTrial')}"
    )

print()
print("=== Primary sponsor ===")
sponsors = p1.get("sponsors", [])
for sp in sponsors[:1]:
    org = sp.get("organisation", {})
    print(f"  name={org.get('name')} | type={org.get('type')} | commercial={org.get('commercial')}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 4 — Pagination Walkthrough
# MAGIC
# MAGIC The CTIS search API uses **page-number pagination** (not cursor-based like ClinicalTrials.gov v2).
# MAGIC The response body contains a `pagination` object:
# MAGIC ```json
# MAGIC {
# MAGIC   "totalRecords": 31,
# MAGIC   "currentPage": 1,
# MAGIC   "totalPages": 31,
# MAGIC   "nextPage": true,
# MAGIC   "prevPage": false
# MAGIC }
# MAGIC ```
# MAGIC Pagination increments the `pagination.page` integer in the POST body. When `nextPage` is `false`,
# MAGIC the final page has been reached. Note that `totalPages` equals `totalRecords` when `size=1`; with
# MAGIC `size=10`, `totalPages` = `ceil(totalRecords / size)`.
# MAGIC
# MAGIC **Ingestion volume estimate (as of 2026-06-06):**
# MAGIC - Total DMD trials in CTIS (all statuses, `medicalCondition = "Duchenne"`) : **31 records**
# MAGIC - At `size=10` this is 4 pages; at `size=100` it is a single request.
# MAGIC - This is approximately 6% of the ClinicalTrials.gov DMD record count (~488), reflecting that CTIS
# MAGIC   became mandatory only in January 2023 — trials authorised before 2023 remain in the old EudraCT
# MAGIC   system and are not accessible via the CTIS API. The CTIS count will grow as legacy trials are
# MAGIC   migrated and new trials are authorised.
# MAGIC
# MAGIC **Pagination gotchas observed:**
# MAGIC - The page number is 1-indexed (first page is `page=1`, not `page=0`), which is non-standard.
# MAGIC - `totalRecords` in the response is always correct; `totalPages` depends on the `size` parameter
# MAGIC   used in the same request. Compute `totalPages` as `ceil(totalRecords / size)` in production code
# MAGIC   rather than trusting the `totalPages` field when changing page size between requests.
# MAGIC - No equivalent of `lastModified` cursor exists — full-replacement ingestion (truncate-and-reload)
# MAGIC   is the recommended production strategy, identical to ClinicalTrials.gov. Use `lastPublicationUpdate`
# MAGIC   from the search summary record as the change-detection field at Silver.
# MAGIC
# MAGIC **Retrieve calls are required for full eligibility data**: the search summary does not include
# MAGIC inclusion/exclusion criteria. The production pipeline must call `/retrieve/{ctNumber}` for each trial
# MAGIC to get the structured eligibility criteria arrays. At 31 records total this adds 31 GET requests;
# MAGIC even at 500 records it remains well within a 1 req/s conservative rate limit.

# COMMAND ----------

# Walk 3 pages of DMD search results using page-number pagination. size=5 for readability.
PAGE_SIZE = 5
all_ct_numbers = []
page_num = 1
collected_pages = 0

while collected_pages < 3:
    page_payload = {
        "pagination": {"page": page_num, "size": PAGE_SIZE},
        "sort": {"property": "decisionDate", "direction": "DESC"},
        "searchCriteria": {"medicalCondition": "Duchenne"},
    }
    resp = requests.post(CTIS_SEARCH_URL, json=page_payload, headers={"Accept": "application/json"}, timeout=30)
    assert resp.status_code == 200, f"Page {page_num} failed: {resp.status_code}"
    page_data = resp.json()

    page_trials = page_data.get("data", [])
    page_ids = [t["ctNumber"] for t in page_trials]
    all_ct_numbers.extend(page_ids)

    print(
        f"Page {page_num}: fetched {len(page_trials)} trials | "
        f"nextPage={page_data['pagination']['nextPage']} | "
        f"IDs: {page_ids}"
    )

    if not page_data["pagination"]["nextPage"]:
        print("nextPage is false — final page reached.")
        break

    page_num += 1
    collected_pages += 1
    time.sleep(0.5)  # Conservative delay — no documented rate limit.

print(f"\nTotal ctNumbers collected : {len(all_ct_numbers)}")
print(f"Duplicates across pages  : {len(all_ct_numbers) - len(set(all_ct_numbers))}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 5 — Data Quality First Look
# MAGIC
# MAGIC **EU CTR-specific quality concerns** (not duplicating the ClinicalTrials.gov concerns documented in
# MAGIC `ctgov_first_look.py`):
# MAGIC
# MAGIC 1. **`ctStatus` integer codes in search vs string values in retrieve**: the search endpoint returns
# MAGIC    `ctStatus` as an integer (2=Authorised, 3=Started, 4=Ongoing, 5=Ended, 6=Prohibited,
# MAGIC    8=Temporarily Halted) while the retrieve endpoint returns the string description. The Bronze schema
# MAGIC    must capture both and apply a code-to-label mapping at Silver. Any unrecognised code value is a
# MAGIC    schema change in the CTIS API.
# MAGIC
# MAGIC 2. **No eligibility criteria in search summary records**: unlike ClinicalTrials.gov where a single
# MAGIC    field containing all criteria text is returned in the search response, CTIS omits eligibility
# MAGIC    criteria entirely from search results. The Silver pipeline must call `/retrieve/{ctNumber}` for
# MAGIC    every record. This doubles the ingestion request count, and means a network failure mid-retrieve
# MAGIC    leaves the Bronze table with summary-only records — a partial-record quality flag is needed.
# MAGIC
# MAGIC 3. **Multi-language criteria with encoding artifacts**: eligibility criteria texts and their
# MAGIC    translations may contain Unicode replacement characters (e.g. `\udc9d`, `\xa0`) resulting from
# MAGIC    encoding issues in the CTIS data entry system. These are non-breaking spaces or private-use
# MAGIC    characters that will corrupt downstream regex extraction if not cleaned at Silver.
# MAGIC
# MAGIC 4. **NCT cross-reference absent for new trials**: `secondaryIdentifyingNumbers.nctNumber` is only
# MAGIC    present when the sponsor explicitly registered the cross-reference. New CTIS-only trials
# MAGIC    (no US registration) will have a null `nctNumber`. The Silver deduplication logic at
# MAGIC    `silver.trials_dmd` must handle null NCT IDs — these are EU-only trials, not missing data.
# MAGIC
# MAGIC 5. **`trialPhase` is a human-readable string in search, a numeric code in retrieve**: the search
# MAGIC    result field is `"Therapeutic confirmatory  (Phase III)"` (note the double space — a CTIS
# MAGIC    formatting quirk). The retrieve field `trialCategory.trialPhase` is `"5"`. Silver normalisation
# MAGIC    must map numeric codes: `"1"` = Phase I, `"2"` = Phase II, `"5"` = Phase III. A DLT quarantine
# MAGIC    rule should flag any unknown code.
# MAGIC
# MAGIC **DLT quarantine rules implied by this analysis:**
# MAGIC - `@dlt.expect_or_quarantine("ct_number_not_null", "ct_number IS NOT NULL")`
# MAGIC - `@dlt.expect_or_quarantine("full_title_not_null", "full_title IS NOT NULL")`
# MAGIC - `@dlt.expect_or_warn("retrieve_succeeded", "retrieve_status_code = 200")` — partial record flag
# MAGIC - `@dlt.expect_or_warn("ct_status_known_code", "ct_status_code IN (2, 3, 4, 5, 6, 8)")`
# MAGIC - `@dlt.expect_or_warn("inclusion_criteria_not_empty", "array_size(inclusion_criteria_raw) > 0")`

# COMMAND ----------

# Fetch all 31 DMD records from the search endpoint for quality analysis.
all_summary_records = []
page = 1
while True:
    resp = requests.post(
        CTIS_SEARCH_URL,
        json={
            "pagination": {"page": page, "size": 10},
            "sort": {"property": "decisionDate", "direction": "DESC"},
            "searchCriteria": {"medicalCondition": "Duchenne"},
        },
        headers={"Accept": "application/json"},
        timeout=30,
    )
    assert resp.status_code == 200
    page_data = resp.json()
    all_summary_records.extend(page_data["data"])
    if not page_data["pagination"]["nextPage"]:
        break
    page += 1
    time.sleep(0.3)

print(f"Total summary records fetched: {len(all_summary_records)}")
print()

# --- Null rate analysis on search summary fields ---
fields_to_check = {
    "ctNumber":             lambda t: t.get("ctNumber"),
    "ctTitle":              lambda t: t.get("ctTitle"),
    "ctStatus (code)":      lambda t: t.get("ctStatus"),
    "trialPhase":           lambda t: t.get("trialPhase"),
    "sponsor":              lambda t: t.get("sponsor"),
    "conditions":           lambda t: t.get("conditions"),
    "ageGroup":             lambda t: t.get("ageGroup"),
    "gender":               lambda t: t.get("gender"),
    "totalNumberEnrolled":  lambda t: t.get("totalNumberEnrolled"),
    "primaryEndPoint":      lambda t: t.get("primaryEndPoint"),
    "resultsFirstReceived": lambda t: t.get("resultsFirstReceived"),
    "lastPublicationUpdate":lambda t: t.get("lastPublicationUpdate"),
    "decisionDateOverall":  lambda t: t.get("decisionDateOverall"),
    "shortTitle":           lambda t: t.get("shortTitle"),
    "trialCountries":       lambda t: t.get("trialCountries"),
}

n = len(all_summary_records)
print("=== Null rates (search summary fields) ===")
for field_name, extractor in fields_to_check.items():
    null_count = sum(1 for t in all_summary_records if not extractor(t))
    null_rate = null_count / n * 100
    print(f"  {field_name:<30} null={null_count}/{n} ({null_rate:.0f}%)")

# COMMAND ----------

from collections import Counter

print("\n=== ctStatus code distribution ===")
statuses = Counter(t.get("ctStatus", "MISSING") for t in all_summary_records)
ct_status_labels = {2: "Authorised", 3: "Started", 4: "Ongoing", 5: "Ended", 6: "Prohibited", 8: "Temporarily Halted"}
for code, count in sorted(statuses.items()):
    label = ct_status_labels.get(code, f"UNKNOWN_CODE_{code}")
    print(f"  code={code} ({label:<20}) : {count}")

print("\n=== trialPhase distribution ===")
phases = Counter(t.get("trialPhase", "MISSING") for t in all_summary_records)
for phase, count in phases.most_common():
    print(f"  {count:>2}  {phase}")

print("\n=== gender distribution ===")
genders = Counter(t.get("gender", "MISSING") for t in all_summary_records)
for g, count in genders.most_common():
    print(f"  {count:>2}  {g}")

print("\n=== ageGroup distribution ===")
age_groups = Counter(t.get("ageGroup", "MISSING") for t in all_summary_records)
for ag, count in age_groups.most_common():
    print(f"  {count:>2}  {ag}")

print("\n=== resultsFirstReceived distribution ===")
results_flag = Counter(t.get("resultsFirstReceived", "MISSING") for t in all_summary_records)
for v, count in results_flag.most_common():
    print(f"  {count:>2}  {v}")

# COMMAND ----------

# --- Date range of authorised trials ---
dates = []
for t in all_summary_records:
    d = t.get("decisionDateOverall")
    if d:
        dates.append(d)

if dates:
    dates.sort()
    print("\n=== decisionDateOverall range ===")
    print(f"  Earliest: {dates[0]}")
    print(f"  Latest  : {dates[-1]}")

# --- Quality flags ---
print("\n=== Potential quality flags ===")
for t in all_summary_records:
    ct_num = t.get("ctNumber", "MISSING")
    issues = []
    if not t.get("ctTitle"):
        issues.append("MISSING_TITLE")
    if not t.get("trialPhase"):
        issues.append("MISSING_PHASE")
    if not t.get("sponsor"):
        issues.append("MISSING_SPONSOR")
    enrolled = t.get("totalNumberEnrolled", "")
    if enrolled and not str(enrolled).isdigit():
        issues.append(f"NON_NUMERIC_ENROLLMENT({enrolled})")
    if issues:
        print(f"  {ct_num}: {', '.join(issues)}")

print("\nQuality flag scan complete.")

# COMMAND ----------

# --- Spot-check eligibility criteria quality on the retrieve endpoint ---
# Retrieve 3 records and inspect criterion count and text length.
print("=== Eligibility criteria quality (retrieve sample, 3 records) ===\n")
sample_ct_numbers = [t["ctNumber"] for t in all_summary_records[:3]]

for ct_num in sample_ct_numbers:
    r = requests.get(
        f"{CTIS_RETRIEVE_URL}/{ct_num}",
        headers={"Accept": "application/json"},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"  {ct_num}: retrieve HTTP {r.status_code} — MISSING_RETRIEVE")
        continue

    rec = r.json()
    aa = rec.get("authorizedApplication", {})
    p1 = aa.get("authorizedPartI", {})
    td = p1.get("trialDetails", {})
    ti = td.get("trialInformation", {})
    ec = ti.get("eligibilityCriteria", {})
    inc = ec.get("principalInclusionCriteria", []) if ec else []
    exc = ec.get("principalExclusionCriteria", []) if ec else []
    cti = td.get("clinicalTrialIdentifiers", {})
    nct_obj = cti.get("secondaryIdentifyingNumbers", {}).get("nctNumber", {})
    nct_id = nct_obj.get("number", "<no NCT>")

    # Check for encoding artifacts.
    all_criteria_text = " ".join(
        c.get("principalInclusionCriteria", "") for c in inc
    ) + " ".join(
        c.get("principalExclusionCriteria", "") for c in exc
    )
    has_encoding_artifact = any(ord(ch) > 0xD800 and ord(ch) < 0xDFFF for ch in all_criteria_text)
    has_nbsp = "\xa0" in all_criteria_text

    print(f"  {ct_num} | nct={nct_id}")
    print(f"    inclusion criteria : {len(inc)} items")
    print(f"    exclusion criteria : {len(exc)} items")
    print(f"    encoding artifacts : surrogate_chars={has_encoding_artifact}, nbsp={has_nbsp}")
    if inc:
        # Check if any criterion mentions exon, mutation, dystrophin, amenable.
        mutation_criteria = [
            c.get("principalInclusionCriteria", "")
            for c in inc
            if any(kw in c.get("principalInclusionCriteria", "").lower()
                   for kw in ["exon", "mutation", "dystrophin", "amenable", "deletion", "duplication", "gene"])
        ]
        print(f"    DMD-relevant inclusion criteria found : {len(mutation_criteria)}")
        for mc in mutation_criteria[:2]:
            print(f"      -> {mc[:120]}")
    print()
    time.sleep(0.5)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 6 — Bronze Schema Sketch
# MAGIC
# MAGIC The proposed Bronze schema for `clinical.bronze.eu_trials_raw` stores the raw retrieve JSON alongside
# MAGIC flattened top-level and first-level columns for partitioning and filtering. The search summary fields
# MAGIC are a subset of the retrieve fields and are reproduced here from the retrieve response.
# MAGIC
# MAGIC **Column presence convention:**
# MAGIC - `[ALWAYS]` — present in every retrieve response; safe as NOT NULL.
# MAGIC - `[OPTIONAL]` — absent in some records; Silver must handle nulls.
# MAGIC - `[NESTED]` — stored as JSON string in Bronze; requires `from_json` + `EXPLODE` at Silver.
# MAGIC
# MAGIC **Field naming mapping: EU CTR vs ClinicalTrials.gov**
# MAGIC
# MAGIC | EU CTR field | ClinicalTrials.gov equivalent | Notes |
# MAGIC |---|---|---|
# MAGIC | `ct_number` | `nct_id` | Primary key; different format (`YYYY-NNNNNN-NN-NN` vs `NCTNNNNNNNN`) |
# MAGIC | `nct_number` | — (is the NCT ID itself) | Cross-reference from EU CTR to ClinicalTrials.gov; NULL for EU-only trials |
# MAGIC | `full_title` | `official_title` | Full protocol title |
# MAGIC | `public_title` | `brief_title` | Short public-facing title |
# MAGIC | `ct_status` | `overall_status` | Different vocabulary; integer code in search, string in retrieve |
# MAGIC | `trial_phase_code` | `phases_raw` | Numeric code ("5") vs text array (["PHASE3"]) |
# MAGIC | `inclusion_criteria_raw` | `eligibility_criteria_text` | **Array vs blob** — EU CTR pre-splits; CTgov does not |
# MAGIC | `exclusion_criteria_raw` | (embedded in blob) | EU CTR separates explicitly; major structural advantage |
# MAGIC | `meddra_condition_terms_raw` | `mesh_conditions_raw` | MedDRA (EU) vs MeSH (US) coding systems |
# MAGIC | `is_transitioned` | — | EU CTR only: was this trial migrated from legacy EudraCT? |
# MAGIC | `member_states_raw` | — | EU CTR only: per-MSC authorisation status; no ClinicalTrials.gov equivalent |
# MAGIC | `eudract_number` | — | Legacy EudraCT number for transitioned trials; needed for cross-reference to old EU CTR |
# MAGIC
# MAGIC | Column name | Source path (retrieve) | Presence | Silver complexity | Use case |
# MAGIC |---|---|---|---|---|
# MAGIC | `ct_number` | `ctNumber` | ALWAYS | Low — direct extract | Primary key; join key |
# MAGIC | `ct_status_code` | `ctPublicStatusCode` | ALWAYS | Low — integer | Silver filter by status |
# MAGIC | `ct_status_label` | `ctStatus` | ALWAYS | Low — controlled vocab | Human-readable status |
# MAGIC | `decision_date` | `decisionDate` | ALWAYS | Low — ISO datetime | Trial timeline |
# MAGIC | `publish_date` | `publishDate` | ALWAYS | Low — ISO datetime | Last publish timestamp |
# MAGIC | `full_title` | `trialDetails.clinicalTrialIdentifiers.fullTitle` | ALWAYS | Low | NLP input; trial ID |
# MAGIC | `public_title` | `trialDetails.clinicalTrialIdentifiers.publicTitle` | OPTIONAL | Low | Display |
# MAGIC | `short_title` | `trialDetails.clinicalTrialIdentifiers.shortTitle` | OPTIONAL | Low | Display |
# MAGIC | `nct_number` | `trialDetails.clinicalTrialIdentifiers.secondaryIdentifyingNumbers.nctNumber.number` | OPTIONAL | Low | Silver dedup join to ClinicalTrials.gov |
# MAGIC | `trial_phase_code` | `trialDetails.trialInformation.trialCategory.trialPhase` | OPTIONAL | Low — code map | Silver phase filter |
# MAGIC | `is_rare_disease` | `authorizedPartI.medicalConditions[0].isConditionRareDisease` | OPTIONAL | Low | Secondary DMD confirmation |
# MAGIC | `meddra_condition_terms_raw` | `trialDetails.trialInformation.medicalCondition.meddraConditionTerms` | OPTIONAL | **HIGH — nested** | MedDRA ontology enrichment at Silver |
# MAGIC | `inclusion_criteria_raw` | `trialDetails.trialInformation.eligibilityCriteria.principalInclusionCriteria` | OPTIONAL | **MEDIUM — array of objects** | Input to `silver.eligibility_criteria` mutation criterion extraction |
# MAGIC | `exclusion_criteria_raw` | `trialDetails.trialInformation.eligibilityCriteria.principalExclusionCriteria` | OPTIONAL | **MEDIUM — array of objects** | Patient-level exclusion criteria at Silver |
# MAGIC | `primary_endpoint_raw` | `trialDetails.trialInformation.endPoint.primaryEndPoints` | OPTIONAL | Medium — array | Trial endpoint classification |
# MAGIC | `estimated_global_end_date` | `trialDetails.trialInformation.trialDuration.estimatedGlobalEndDate` | OPTIONAL | Low — date parse | Trial timeline; eligibility_delta |
# MAGIC | `sponsor_name` | `authorizedPartI.sponsors[0].organisation.name` | OPTIONAL | Low | Provenance |
# MAGIC | `sponsor_type` | `authorizedPartI.sponsors[0].organisation.type` | OPTIONAL | Low | Commercial vs academic |
# MAGIC | `products_raw` | `authorizedPartI.products` | OPTIONAL | **HIGH — nested** | Intervention classification |
# MAGIC | `member_states_raw` | `authorizedPartsII[].mscInfo` | OPTIONAL | **HIGH — EXPLODE** | Per-MSC authorisation tracking |
# MAGIC | `is_transitioned` | `authorizedApplication.eudraCt.isTransitioned` | ALWAYS | Low | Provenance; EudraCT cross-reference |
# MAGIC | `trial_region_code` | `trialRegionCode` | OPTIONAL | Low | EEA-only vs global |
# MAGIC | `total_enrolled` | (from search summary) | OPTIONAL | Low | Cohort size estimate |
# MAGIC | `raw_json` | full retrieve response | ALWAYS | N/A | Full fidelity archive |
# MAGIC | `source_system` | hardcoded | ALWAYS | N/A | Provenance |
# MAGIC | `ingestion_timestamp` | runtime | ALWAYS | N/A | ALCOA+ contemporaneous provenance |
# MAGIC | `api_version` | hardcoded | ALWAYS | N/A | Schema version tracking |
# MAGIC | `source_url` | constructed from ctNumber | ALWAYS | N/A | Attributable provenance link |
# MAGIC
# MAGIC **Silver transformation complexity summary:**
# MAGIC - `inclusion_criteria_raw` and `exclusion_criteria_raw` are pre-split arrays of criterion objects —
# MAGIC   each element contains `number`, English text, and translations. The Silver NLP task is narrower
# MAGIC   than for ClinicalTrials.gov: only within-criterion extraction of mutation-specific language is needed,
# MAGIC   not full inclusion/exclusion boundary detection.
# MAGIC - `member_states_raw` requires `EXPLODE` to produce per-MSC rows for the Silver trials_dmd table —
# MAGIC   a trial may be Authorised in France but Ongoing in Germany.
# MAGIC - `meddra_condition_terms_raw` contains versioned MedDRA term codes with level (PT/LLT/HLT) —
# MAGIC   useful for cross-mapping to OMOP concept IDs at Silver without free-text NLP.
# MAGIC - `products_raw` is deeply nested (product → productDictionaryInfo → activeSubstanceName etc.);
# MAGIC   requires flattening at Silver to extract the investigational product name and active substance.

# COMMAND ----------

# Materialise the Bronze schema as a sample DataFrame built from retrieve responses.
import json as json_lib

rows = []

# Fetch full records for the first 10 summary records.
for summary in all_summary_records[:10]:
    ct_num = summary["ctNumber"]
    r = requests.get(
        f"{CTIS_RETRIEVE_URL}/{ct_num}",
        headers={"Accept": "application/json"},
        timeout=30,
    )
    retrieve_ok = r.status_code == 200
    full_rec = r.json() if retrieve_ok else {}

    # Navigate to nested structures safely.
    aa = full_rec.get("authorizedApplication", {}) if full_rec else {}
    p1 = aa.get("authorizedPartI", {})
    td = p1.get("trialDetails", {})
    cti = td.get("clinicalTrialIdentifiers", {})
    ti = td.get("trialInformation", {})
    ec = ti.get("eligibilityCriteria", {}) or {}
    tc = ti.get("trialCategory", {}) or {}
    td_dur = ti.get("trialDuration", {}) or {}
    pop = ti.get("populationOfTrialSubjects", {}) or {}
    sponsors = p1.get("sponsors", [])
    eudra_ct = aa.get("eudraCt", {})
    nct_obj = cti.get("secondaryIdentifyingNumbers", {}).get("nctNumber", {}) if cti else {}

    row = {
        "ct_number":                  ct_num,
        "ct_status_code":             full_rec.get("ctPublicStatusCode"),
        "ct_status_label":            full_rec.get("ctStatus"),
        "decision_date":              full_rec.get("decisionDate"),
        "publish_date":               full_rec.get("publishDate"),
        "full_title":                 cti.get("fullTitle") if cti else None,
        "public_title":               cti.get("publicTitle") if cti else None,
        "short_title":                cti.get("shortTitle") if cti else None,
        "nct_number":                 nct_obj.get("number") if nct_obj else None,
        "trial_phase_code":           tc.get("trialPhase"),
        "is_rare_disease":            p1.get("medicalConditions", [{}])[0].get("isConditionRareDisease") if p1.get("medicalConditions") else None,
        "inclusion_criteria_raw":     json_lib.dumps(ec.get("principalInclusionCriteria", [])),
        "exclusion_criteria_raw":     json_lib.dumps(ec.get("principalExclusionCriteria", [])),
        "meddra_condition_terms_raw": json_lib.dumps(ti.get("medicalCondition", {}).get("meddraConditionTerms", [])),
        "estimated_global_end_date":  td_dur.get("estimatedGlobalEndDate"),
        "sponsor_name":               sponsors[0].get("organisation", {}).get("name") if sponsors else None,
        "sponsor_type":               sponsors[0].get("organisation", {}).get("type") if sponsors else None,
        "products_raw":               json_lib.dumps(p1.get("products", [])),
        "member_states_raw":          json_lib.dumps([
                                          p2.get("mscInfo", {})
                                          for p2 in aa.get("authorizedPartsII", [])
                                      ]),
        "is_transitioned":            eudra_ct.get("isTransitioned") if eudra_ct else None,
        "trial_region_code":          full_rec.get("trialRegionCode"),
        "retrieve_status_code":       r.status_code,  # QA: flag partial records
        "raw_json":                   json_lib.dumps(full_rec) if full_rec else None,
    }
    rows.append(row)
    time.sleep(0.3)  # Conservative rate limiting.

# Display summary of materialised rows.
print(f"Bronze schema sample — {len(rows)} rows\n")
print(f"{'ct_number':<28} {'ct_status_label':<15} {'phase':<5} {'nct_number':<15} {'inc_n':<6} {'exc_n'}")
print("-" * 100)
for row in rows:
    inc_criteria = json_lib.loads(row.get("inclusion_criteria_raw", "[]"))
    exc_criteria = json_lib.loads(row.get("exclusion_criteria_raw", "[]"))
    print(
        f"  {str(row.get('ct_number', '')):<27} "
        f"{str(row.get('ct_status_label', '')):<15} "
        f"{str(row.get('trial_phase_code', '')):<5} "
        f"{str(row.get('nct_number', '')):<15} "
        f"{len(inc_criteria):<6} "
        f"{len(exc_criteria)}"
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 7 — Provenance Metadata
# MAGIC
# MAGIC Clinical data integrity standards require **ALCOA+ provenance** — data that is Attributable,
# MAGIC Legible, Contemporaneous, Original, and Accurate, plus Complete, Consistent, Enduring, and Available.
# MAGIC These principles were established for GCP (Good Clinical Practice) in pharmaceutical trials and apply
# MAGIC directly to data infrastructure feeding a clinical trial matching system.
# MAGIC
# MAGIC **Why ALCOA+ matters specifically for EU CTR data:**
# MAGIC - **Attributable**: CTIS trial records are authoritative EU regulatory documents. The `source_url`
# MAGIC   (constructed as `https://euclinicaltrials.eu/ctis-public/view/{ctNumber}`) links each Bronze
# MAGIC   record to its public-facing regulatory page, allowing any record to be traced back to its
# MAGIC   authoritative source without re-ingestion.
# MAGIC - **Contemporaneous**: CTIS records can be amended post-authorisation (e.g., protocol modifications
# MAGIC   changing eligibility criteria). The `ingestion_timestamp` and `publish_date` together establish
# MAGIC   which version of the trial document a downstream eligibility verdict was computed from — critical
# MAGIC   for audit if a patient-trial eligibility decision is ever questioned.
# MAGIC - **Original**: the `raw_json` column stores the complete, unmodified retrieve response. EU CTR
# MAGIC   records include multi-language translations; the raw archive preserves these for future NLP work
# MAGIC   even if the Bronze schema does not extract them initially.
# MAGIC - **Versioned**: the `api_version` field records the CTIS API generation. Since no official
# MAGIC   versioning is published, this is set to `"ctis-public-api-2024"` (the observed API base path as
# MAGIC   of the CTIS platform version launched 2024). Any endpoint path change would require a new version
# MAGIC   string and a schema migration.
# MAGIC - **Cross-registry consistency**: for dual-registered trials (both CTIS `ct_number` and NCT ID
# MAGIC   present), the `source_url` links to the EU record, while `nct_number` allows the ClinicalTrials.gov
# MAGIC   record to be retrieved. This two-source provenance chain supports ADR-06 conflict detection.

# COMMAND ----------

def attach_provenance(record: dict, ct_number: str) -> dict:
    """Attach ALCOA+ provenance metadata to a Bronze EU CTR record."""
    record["source_system"]       = "eu_clinical_trials_register"
    record["api_version"]         = "ctis-public-api-2024"
    record["ingestion_timestamp"] = datetime.now(timezone.utc).isoformat()
    # Source URL links to the public-facing CTIS portal page, not the REST endpoint.
    record["source_url"]          = f"https://euclinicaltrials.eu/ctis-public/view/{ct_number}"
    return record

# Demonstrate provenance attachment on the first sample record.
sample_with_provenance = attach_provenance(
    {
        "ct_number":   rows[0]["ct_number"],
        "nct_number":  rows[0]["nct_number"],
        "raw_json":    "<truncated for display>",
    },
    rows[0]["ct_number"],
)

print("=== Provenance metadata sample ===")
for k, v in sample_with_provenance.items():
    print(f"  {k:<30} : {v}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Section 8 — Write to Personal Schema
# MAGIC
# MAGIC Persists the Bronze schema sample to `workspace.steff_horemans.bronze_eu_trials_raw` for interactive
# MAGIC Silver prototyping — specifically to experiment with parsing the pre-structured inclusion/exclusion
# MAGIC criteria arrays and with the MedDRA condition code mapping.
# MAGIC
# MAGIC **`workspace.steff_horemans` is the ungoverned personal schema (ADR-01)**: tables written here are
# MAGIC never imported from production pipelines. The `USE` statement sets this schema as the session default
# MAGIC so subsequent `SELECT` and `DESCRIBE` calls in this notebook can omit the catalog and schema prefix.
# MAGIC This is a deliberate convention — the personal schema is for exploration, not a staging area for
# MAGIC production data. Any Silver prototyping work done against `bronze_eu_trials_raw` must be migrated
# MAGIC to a proper DLT pipeline before being promoted to the `clinical` domain.

# COMMAND ----------

from databricks.connect import DatabricksSession  # noqa: E402

# Connects to the remote cluster via Databricks Connect — execution happens on Databricks.
spark = DatabricksSession.builder.profile("steff_horemans").serverless(True).getOrCreate()
# Alternative if serverless is not available:
# spark = DatabricksSession.builder.profile("steff_horemans").clusterId("<cluster-id>").getOrCreate()

spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.steff_horemans")
spark.sql("USE workspace.steff_horemans")

# Attach provenance to all rows before writing.
rows_with_provenance = [attach_provenance(dict(row), row["ct_number"]) for row in rows]

df = spark.createDataFrame(rows_with_provenance)
(
    df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.steff_horemans.bronze_eu_trials_raw")
)

print(f"Written {df.count()} rows to workspace.steff_horemans.bronze_eu_trials_raw")
spark.sql("DESCRIBE TABLE bronze_eu_trials_raw").show(truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Appendix A — Field Priority List for DMD Silver Transformation
# MAGIC
# MAGIC This list was drafted before writing the notebook, based on the domain context from
# MAGIC `docs/scientific_background.md` and the actual API response observed in Section 3.
# MAGIC
# MAGIC **Tier 1 — Always extract, never nullable in Silver**
# MAGIC - `ct_number` — primary key
# MAGIC - `full_title` — human-readable trial identity
# MAGIC - `ct_status_label` — trial validity; drives eligibility_catalogue freshness
# MAGIC - `ingestion_timestamp` — ALCOA+ provenance
# MAGIC
# MAGIC **Tier 2 — Extract; nullable acceptable; high clinical value**
# MAGIC - `nct_number` — cross-registry deduplication; NULL = EU-only trial (expected, not missing)
# MAGIC - `inclusion_criteria_raw` / `exclusion_criteria_raw` — core input to eligibility_criteria Silver table
# MAGIC - `trial_phase_code` — Silver filter: Phase II+ only for eligibility matching
# MAGIC - `meddra_condition_terms_raw` — structured condition coding; replaces free-text condition matching
# MAGIC - `sponsor_name` — Sarepta / BioMarin / Solid Biosciences / Avidity grouping for intervention class
# MAGIC - `is_transitioned` — provenance; needed to check if a parallel EudraCT record exists
# MAGIC
# MAGIC **Tier 3 — Retain in raw_json; extract at Silver on demand**
# MAGIC - `products_raw` — investigational product name and active substance (intervention classification)
# MAGIC - `member_states_raw` — per-MSC authorisation status (EU geographic coverage)
# MAGIC - `primary_endpoint_raw` — endpoint classification (functional vs biomarker)
# MAGIC - `estimated_global_end_date` — trial timeline for eligibility_delta
# MAGIC
# MAGIC **Likely always null or low signal for DMD trials**
# MAGIC - `results` object — CTIS results reporting is not yet widely adopted; expect null for most records
# MAGIC - Multi-language criterion translations — low signal for English-language NLP pipeline; retain in
# MAGIC   raw_json for future multilingual work but do not extract at Silver initially

# COMMAND ----------
# MAGIC %md
# MAGIC ## Appendix B — Production Ingestion Sketch (DLT)
# MAGIC
# MAGIC Non-executable reference showing how the Bronze DLT table would be defined. The two-call pattern
# MAGIC (search for CT numbers, then retrieve for each) is preserved in the production pipeline.
# MAGIC
# MAGIC ```python
# MAGIC import dlt
# MAGIC import requests
# MAGIC import json
# MAGIC import time
# MAGIC from datetime import datetime, timezone
# MAGIC from pyspark.sql import functions as F
# MAGIC
# MAGIC CTIS_SEARCH_URL  = "https://euclinicaltrials.eu/ctis-public-api/search"
# MAGIC CTIS_RETRIEVE_URL = "https://euclinicaltrials.eu/ctis-public-api/retrieve"
# MAGIC DMD_SEARCH_CRITERIA = {"medicalCondition": "Duchenne"}
# MAGIC
# MAGIC @dlt.table(
# MAGIC     name="eu_trials_raw",
# MAGIC     comment="Bronze layer: raw CTIS API retrieve responses for all DMD-matched EU trials.",
# MAGIC     table_properties={"quality": "bronze", "pipelines.autoOptimize.managed": "true"},
# MAGIC )
# MAGIC @dlt.expect_or_quarantine("ct_number_not_null",         "ct_number IS NOT NULL")
# MAGIC @dlt.expect_or_quarantine("full_title_not_null",        "full_title IS NOT NULL")
# MAGIC @dlt.expect_or_warn("retrieve_succeeded",              "retrieve_status_code = 200")
# MAGIC @dlt.expect_or_warn("ct_status_known_code",            "ct_status_code IN (2, 3, 4, 5, 6, 8)")
# MAGIC @dlt.expect_or_warn("inclusion_criteria_not_empty",   "array_size(from_json(inclusion_criteria_raw, ...)) > 0")
# MAGIC def eu_trials_raw():
# MAGIC     # Step 1: paginate search to collect all CT numbers.
# MAGIC     ct_numbers = []
# MAGIC     page = 1
# MAGIC     while True:
# MAGIC         resp = requests.post(CTIS_SEARCH_URL, json={
# MAGIC             "pagination": {"page": page, "size": 100},
# MAGIC             "sort": {"property": "decisionDate", "direction": "DESC"},
# MAGIC             "searchCriteria": DMD_SEARCH_CRITERIA,
# MAGIC         }, headers={"Accept": "application/json"}, timeout=30)
# MAGIC         data = resp.json()
# MAGIC         ct_numbers.extend([t["ctNumber"] for t in data["data"]])
# MAGIC         if not data["pagination"]["nextPage"]:
# MAGIC             break
# MAGIC         page += 1
# MAGIC         time.sleep(1.0)
# MAGIC
# MAGIC     # Step 2: retrieve full records for each CT number.
# MAGIC     rows = []
# MAGIC     for ct_num in ct_numbers:
# MAGIC         r = requests.get(f"{CTIS_RETRIEVE_URL}/{ct_num}",
# MAGIC                          headers={"Accept": "application/json"}, timeout=30)
# MAGIC         # ... extract fields, attach provenance, append to rows ...
# MAGIC         time.sleep(1.0)
# MAGIC
# MAGIC     return spark.createDataFrame(rows, schema=BRONZE_EU_TRIALS_SCHEMA)
# MAGIC ```
