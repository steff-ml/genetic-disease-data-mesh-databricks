# Data Products

Each section below describes one data product available on this platform. A data product is a curated, validated dataset with a clear purpose, known quality level, and defined access rules.

---

## Index

| # | Product | Description | Update Frequency | License |
|---|---------|-------------|-----------------|---------|
| 1 | [_(Name)_](#product-1--name) | _(Short description)_ | _(e.g. Monthly)_ | Academic / Commercial |

---

## Product 1 — _(Name)_

_(One or two sentences describing what this data product contains and who it is for.)_

### Schema

A summary of the key fields in this dataset. For the full technical specification, see the data contract.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| _(field_name)_ | _(e.g. string)_ | _(what it represents)_ | _(example value)_ |

### Update Frequency

This dataset is updated _(e.g. monthly / upon each source release / manually by curators)_. Changes between versions are documented in the [Changelog](changelog.md).

### Validation Method

Before each release, this dataset is checked for:

- _(e.g. Completeness — all required fields must be populated)_
- _(e.g. Consistency — gene symbols are validated against the HGNC reference list)_
- _(e.g. Referential integrity — all disease IDs must exist in the disease reference table)_

Validation results are logged and any failures block the release until resolved.

### Access Method

| Environment | Access Path |
|-------------|-------------|
| Databricks (Unity Catalog) | `_(catalog.schema.table)_` |
| _(e.g. REST API)_ | _(endpoint or instructions)_ |
| _(e.g. File download)_ | _(URL or process)_ |

### License Tiers

| Tier | Who Qualifies | What Is Allowed |
|------|--------------|-----------------|
| Academic / Non-commercial | Researchers at accredited institutions | Use for research and publication, with attribution |
| Commercial | Companies and for-profit entities | See commercial access below |

### Intended Use, Citation Format & Human Considerations

**Intended use:** _(Describe the research or analytical questions this product is designed to answer. Also note any uses it is explicitly not intended for, e.g. "not validated for clinical diagnostic use".)_

**Citation format:**
```
_(Author/Organisation), (Year). _(Product Name)_ [dataset]. Retrieved from _(platform URL)_, version _(X.Y)_.
```

**Human considerations:** This dataset describes genetic characteristics associated with disease. Users should be aware that:
- _(e.g. Data should not be used to make inferences about individuals without appropriate consent frameworks)_
- _(e.g. Variant classifications may change as scientific understanding evolves)_
- _(e.g. Population frequencies may not be representative of all ethnic groups)_

### How to Request Commercial Access

To request a commercial license, please _(e.g. contact us at [email] / fill in the request form at [URL])_ with the following information:

1. Organisation name and intended use case
2. Expected data volume and usage frequency
3. Contact details for your legal or compliance team

We aim to respond within _(e.g. 10 business days)_.

### How to Report Errors

If you believe you have found an error in this dataset, please _(e.g. open a GitHub issue / email [address])_ and include:

- The specific record(s) affected (e.g. a disease ID or gene symbol)
- What you believe is incorrect and why
- A reference or source supporting the correction

Reported errors are triaged within _(e.g. two weeks)_ and tracked in the [Changelog](changelog.md) once resolved.

---

_Add additional data products below by copying the template above._
