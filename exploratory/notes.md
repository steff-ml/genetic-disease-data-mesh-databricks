# Exploratory Data Source Notes

Notes from first-look exploration of all API sources investigated for the DMD data mesh. See the corresponding `*_first_look.py` file for runnable code.

---

## ClinicalTrials.gov

**Notebook**: `ctgov_first_look.py` | **Target**: `clinical.bronze.clinicaltrials_raw` | **Date**: 2026-06-06

### Endpoint

```
GET https://clinicaltrials.gov/api/v2/studies
    ?query.cond=Duchenne Muscular Dystrophy
    &pageSize=1000
    &format=json
    &countTotal=true   # first page only; expensive
```

Public, no authentication. Rate limit ~10 req/s. Cursor-based pagination via `nextPageToken`.

### Record counts

| Status | Count |
|--------|-------|
| All statuses | ~488 |
| Recruiting | ~63 |
| Active, not recruiting | ~28 |
| Not yet recruiting | ~21 |
| **Pipeline-relevant total** | **~112** |

At `pageSize=1000` this is a single request per full refresh. Weekly full-replacement ingestion recommended (no `lastModified` cursor available for incremental pulls).

### Data quality concerns

1. **`eligibilityCriteria` is a single free-text blob.** Mutation-specific criteria (e.g. "amenable to exon 51 skipping") are buried in a continuous inclusion/exclusion narrative alongside patient-level criteria. Silver NLP pipeline must parse this blob — highest-risk transformation in the pipeline. Needs `@dlt.expect_or_quarantine("eligibility_criteria_not_null")`.

2. **`phases: ["NA"]` appears on interventional studies.** Expanded access programmes and some Phase I studies register without a phase. Must be quarantined or segregated at Silver to protect the Phase II–IV eligibility catalogue.

3. **Date precision is inconsistent.** Dates are returned as `YYYY-MM-DD` or `YYYY-MM` depending on registrant precision. Silver date parsing must handle both without coercing `YYYY-MM` to a specific day.

---

## EU Clinical Trials Register (CTIS)

**Notebook**: `eu_ctr_first_look.py` | **Target**: `clinical.bronze.eu_trials_raw` | **Date**: 2026-06-06

### Endpoints

The CTIS API is **undocumented** — endpoints were discovered by reading the compiled Angular JS bundle at `/ctis-public/main-DGWGCUGU.js`. Two endpoints required in combination:

```
POST https://euclinicaltrials.eu/ctis-public-api/search
Body: {"pagination": {"page": 1, "size": 100}, "searchCriteria": {"medicalCondition": "Duchenne"}}
→ Returns lightweight summaries; NO eligibility criteria
```

```
GET https://euclinicaltrials.eu/ctis-public-api/retrieve/{ctNumber}
→ Returns full structured record including principalInclusionCriteria and principalExclusionCriteria arrays
```

Public, no authentication. API base path and parameters derived from JS source — subject to silent breaking changes.

### Record counts

~31 DMD trials as of 2026-06-06. Low count because CTIS only became mandatory in January 2023 — pre-2023 trials remain in the frozen EudraCT system. Count will grow as legacy trials migrate.

### Data quality concerns

1. **`ctStatus` code mismatch between endpoints.** Search returns integer codes (2, 3, 4, 5, 6, 8); retrieve returns string labels ("Authorised", "Ongoing"). Bronze must store both; Silver must maintain a code-to-label mapping and quarantine records with unknown codes.

2. **Eligibility criteria require a separate retrieve call per trial.** Unlike ClinicalTrials.gov, the search endpoint contains no eligibility text. A network failure mid-retrieve leaves partial records. Need a `retrieve_status_code` field and `@dlt.expect_or_warn("retrieve_succeeded")` rule.

3. **Unicode artifacts in criterion text.** Surrogate characters (`\udc9d`) and non-breaking spaces (`\xa0`) found in eligibility text — artifacts of the CTIS data entry system. Will corrupt regex-based exon number extraction at Silver. EU CTR-specific cleaning step required before NLP.

---

## EudraCT (legacy EU registry, pre-2023)

**File**: `eudract_access_note.md` | **Target**: none — pipeline not viable | **Date**: 2026-06-06

### Access investigation result

The informal REST endpoint (`/ctr-search/rest/search`) used by the clinical trials community is **decommissioned — HTTP 404 on all variants**. RSS feed and bulk download endpoints also return 404. Only the HTML search interface is alive.

**108 DMD trial records** visible in the web UI. Individual trial HTML pages contain eligibility criteria in sections E.3/E.4, but access requires HTML scraping — legally fragile on an EMA regulatory site and technically fragile as the source is being phased out.

### Why no pipeline was built

- REST API is dead; no replacement provided
- HTML scraping is not authorised by EudraCT ToS and is fragile (the interface already changed once)
- Source is frozen — no new trials since January 2023; count will not grow

### Recommended actions

1. **Overlap check first**: query `clinicaltrials_raw` to determine what fraction of the 108 EudraCT trials are already present via NCT cross-registration. If >75% overlap, deprioritise.
2. **One-time manual extraction** if gap is significant: 108 records is tractable via the 20-record-per-request plain-text download (6 requests). Store as `fixtures/eudract_dmd_trials.json`, not as an automated pipeline.
3. **EMA formal data request** if historical completeness is a hard requirement — the only route to complete structured data. Turnaround ~4–8 weeks.
4. For ongoing EU coverage post-2023, CTIS (`eu_ctr_first_look.py`) is the correct path.

---

## FDA Drug Approvals

**Notebook**: `fda_approvals_first_look.py` | **Target**: `clinical.bronze.fda_approvals_raw` | **Date**: 2026-06-06

### Endpoints

Two endpoints required in combination:

```
GET https://api.fda.gov/drug/label.json
    ?search=indications_and_usage:"Duchenne muscular dystrophy"
    &limit=100
→ Primary — INDICATIONS AND USAGE section; exon-skipping eligibility phrases live here
```

```
GET https://api.fda.gov/drug/drugsfda.json
    ?search=application_number:{NDA/BLA}
→ Secondary — full supplement history per application
```

Public. Unauthenticated: 40 req/min. API key (free registration): 240 req/min. Note: `openfda.indication` does not exist as a search field — use `indications_and_usage`.

### Record counts

- **24 label records** match "Duchenne muscular dystrophy": 4 AONs, ELEVIDYS, givinostat/DUVYZAT, deflazacort/EMFLAZA, vamorolone/AGAMREE, generic corticosteroids
- **6 drugsfda application records**, 1–35+ supplements each (eteplirsen: 35+)

### Approved DMD drugs reference

| Drug | Brand | Mechanism | Exon target | Application |
|------|-------|-----------|-------------|-------------|
| Eteplirsen | EXONDYS 51 | AON exon skipping | Exon 51 | NDA206488 |
| Golodirsen | VYONDYS 53 | AON exon skipping | Exon 53 | NDA211970 |
| Viltolarsen | VILTEPSO | AON exon skipping | Exon 53 | NDA212154 |
| Casimersen | AMONDYS 45 | AON exon skipping | Exon 45 | NDA213026 |
| Delandistrogene moxeparvovec | ELEVIDYS | Microdystrophin gene therapy | None (boys 4–5) | BLA125736 |
| Givinostat | DUVYZAT | Pan-HDAC inhibitor | None (all DMD ≥6 years) | NDA216954 |
| Deflazacort | EMFLAZA | Corticosteroid | None | NDA208684 |
| Vamorolone | AGAMREE | Dissociative corticosteroid | None | NDA216592 |

Ataluren (TRANSLARNA) — EMA approved only; not FDA approved. Ingested via EMA labels pathway.

### Data quality concerns

1. **`openfda` object empty on ~30% of label records.** When `openfda.application_number` is absent, no programmatic link exists to the application history. Silver needs a hand-curated `set_id → application_number` lookup table. Flag with `@dlt.expect` (warn, not quarantine) on `openfda_application_number`.

2. **Genetic eligibility parseable for AONs only.** The four AONs use the consistent phrase `"amenable to exon N skipping"` — one regex covers all. ELEVIDYS and givinostat carry no exon-level text. Silver NLP must handle each drug by name with explicit coverage tests; new approvals will silently produce null `target_exon` values if only pattern-matching is used.

3. **Only current label version accessible via openFDA.** EXONDYS 51 is on version 15 — each version may have altered the indication, patient population, or age window. Tracking label history requires the FDA bulk download files or DailyMed FHIR History API — a separate ingestion pathway not covered by this exploration.

---

## LOVD (Leiden Open Variation Database)

**Notebook**: `lovd_first_look.py` | **Target**: `discovery.bronze.lovd_variants_raw` | **Date**: 2026-06-06

### Endpoints

The LOVD3 REST API base is `https://databases.lovd.nl/shared/api/rest.php`. The API is documented in the
LOVDnl/LOVD3 GitHub repository (`src/api.php`). The website prohibits web scraping — the REST API is the
only authorised programmatic access method.

```
GET https://databases.lovd.nl/shared/api/rest.php/variants/DMD
    ?show_variant_effect=1
    &start={1-based offset}     # pagination
→ Atom XML (default) or JSON (Accept: application/json)
→ OpenSearch pagination: <os:totalResults>, <os:startIndex>, <os:itemsPerPage>
```

The gene metadata endpoint provides a connectivity check:

```
GET https://databases.lovd.nl/shared/api/rest.php/genes/DMD
→ Gene record: symbol, chromosome, transcript, curator, created/updated dates
```

The `/variants/DMD/unique` endpoint (deduplicated by `Variant/DNA` + `Variant/DBID`) was not selected
for Bronze because it collapses multi-lab submissions, losing per-submitter pathogenicity calls needed
for ADR-06 conflict detection.

Public, no authentication. No documented rate limit — polite 1 req/s enforced in notebook.
Default response is Atom XML; JSON requested via `Accept: application/json` header.

### Record counts

| Metric | Count |
|--------|-------|
| Total public variants (all submissions) | ~41,538 |
| Unique public DNA variants | ~10,136 |
| Hidden variants | ~1,413 |
| Individuals with public variants | ~61,781 |
| Reference transcript | NM_004006.2 (Dp427m) |
| Database version at exploration | DMD:260512 (May 2026) |

At 100 per page, full ingestion requires ~415 pages. At 1 req/s: ~7 minutes. Monthly full replacement
recommended; incremental delta via `edited_date` high-water mark is possible but adds operational
complexity for a dataset this size.

### Data quality concerns

1. **`exon_raw` is not returned by the shared `/variants/DMD` Atom endpoint.** The field is absent from
   all records — the shared endpoint only returns `position_mRNA` (e.g. `NM_004006.2:c.-1289195_9085-18771`),
   which contains cDNA coordinates but no discrete exon number. Exon numbers must be derived at Silver via
   Ensembl coordinate lookup: map the cDNA position range against the NM_004006.2 exon coordinate table to
   recover affected exon indices, then apply the reading frame rule. Records where `position_mRNA` is null
   or unparseable cannot contribute to reading frame computation and must be quarantined with
   `action_required = 'manual_review'`. Note: individual LOVD installations (non-shared) do expose `exon_raw`
   — if the shared endpoint proves insufficient, a direct query to the Leiden DMD database instance is the
   fallback.

2. **`Variant/DNA` notation is heterogeneous — three distinct styles present.** Canonical HGVS cDNA
   (`c.6439del`), legacy uncertain-boundary notation (`c.(?_432-1)_(6438+1_?)del`), and fully uncertain
   records (`c.?`) all appear in the same response. The `hgvs` Python library will fail strict parsing on
   the legacy style; Silver must implement a fallback chain: strict HGVS → lenient regex → `exon_raw` →
   quarantine. Records where both `Variant/DNA = "c.?"` and `exon_raw` is null cannot contribute to
   reading frame computation and must be quarantined with `action_required = 'manual_review'`.

3. **Pathogenicity encoding is dual-layer and LOVD-specific — not ACMG 5-tier.** LOVD encodes
   pathogenicity as `+` (pathogenic), `+?` (likely pathogenic), `-` (benign), `-?` (likely benign),
   `?` (VUS), `.` (not provided) in both `effect_reported` (submitter call) and `effect_concluded`
   (curator call). Silver must map both fields to ACMG 5-tier and then implement ADR-06: disagreement
   between `effect_concluded` and the ClinVar pathogenicity for the same `clinvar_id` sets
   `classification_conflict = true`. The `clinvar_id` field is expected to be null for a large fraction
   of records (~60-70% estimated), making cross-source conflict detection only partial. Additionally,
   `effect_reported` vs `effect_concluded` disagreement within LOVD itself is a secondary conflict
   signal that Silver should also surface.
