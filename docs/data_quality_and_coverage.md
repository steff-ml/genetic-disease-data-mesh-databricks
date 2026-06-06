Back to [README.md](../../README.md)
# Data Quality & Coverage

This document gives an honest picture of what data this platform contains, how reliable it is, and where its limits are. It is written for a general audience — no technical background is required to read it.

---

## What Data Is Included

This platform brings together data on genetic diseases, including _(e.g. disease definitions, gene associations, variant classifications, patient cohorts — fill in as appropriate)_.

The goal is to provide a unified, trustworthy source that researchers, clinicians, and analysts can rely on without needing to manually reconcile data from multiple sources.

---

## Coverage

| Dimension | Status | Notes |
|-----------|--------|-------|
| Diseases covered | _(e.g. ~6,000)_ | _(e.g. based on OMIM/Orphanet)_ |
| Genes covered | _(to be filled)_ | — |
| Variants covered | _(to be filled)_ | — |
| Geographic coverage | _(to be filled)_ | _(e.g. global, or specific cohorts)_ |
| Time period | _(to be filled)_ | _(earliest and latest records)_ |

### Known Gaps

Some areas are intentionally or temporarily not covered:

- _(e.g. Somatic variants are out of scope — this platform focuses on germline genetics)_
- _(e.g. Diseases with fewer than N documented cases may have limited or no data)_
- _(e.g. Data from certain source databases is pending integration)_

---

## Data Freshness

| Source | Update Frequency | Last Updated |
|--------|-----------------|--------------|
| _(Source A)_ | _(e.g. Monthly)_ | _(date)_ |
| _(Source B)_ | _(e.g. Quarterly)_ | _(date)_ |

Data is refreshed automatically on the schedule above. If you are using this data for time-sensitive work, check the "Last Updated" column before drawing conclusions.

---

## Data Quality

### What "Quality" Means Here

We use three main dimensions to assess quality:

- **Completeness** — Are all expected fields filled in? A record with many missing values is less useful than one that is fully populated.
- **Consistency** — Do values agree across sources? For example, does a gene symbol match between two databases that both list it?
- **Accuracy** — Is the information correct? Where possible, we cross-reference against authoritative sources, but some fields rely on curator judgement or published literature that may later be revised.

### Quality Indicators

| Metric | Current Status |
|--------|---------------|
| Completeness (key fields) | _(e.g. 94%)_ |
| Cross-source consistency | _(e.g. 88%)_ |
| Records flagged for review | _(e.g. 212)_ |

These numbers are updated each time the data is refreshed.

---

## Known Issues

| Issue | Affected Area | Severity | Status |
|-------|--------------|----------|--------|
| _(e.g. Synonym mismatches between source A and B)_ | _(e.g. Disease names)_ | Low | Under investigation |
| _(add more as discovered)_ | — | — | — |

Severity levels: **Low** (cosmetic or edge case), **Medium** (may affect some analyses), **High** (do not use this data for decisions until resolved).

---

## What the Platform Validates — and What It Does Not

**The platform checks that:**
- Records conform to expected formats (e.g. gene symbols follow HGNC conventions)
- Required fields are present
- Values fall within defined reference lists where applicable

**The platform does not guarantee:**
- That the underlying scientific claims are correct — it reflects the state of published and curated knowledge, which evolves
- That every edge case or rare variant has been captured
- Clinical validity or suitability for diagnostic use

---

## Questions or Concerns

If you notice something that looks wrong, or if you have questions about a specific data point, please _(e.g. open a GitHub issue / contact the data team at [email] / use the feedback form)_.
