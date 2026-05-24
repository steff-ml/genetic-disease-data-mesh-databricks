# ADR-23: Test Strategy

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-21 (pipeline framework — the framework determines what is testable and at what granularity)
**Blocks:** CI/CD pipeline design

---

## The Problem

Pipelines that are not tested are not maintained — they are replaced. A test strategy for this project must cover: transformation logic correctness, schema contract compliance, data quality expectation coverage, and regression detection when upstream schemas change. The strategy must also be honest about what is feasible: DLT pipelines, if chosen, have different testability characteristics than plain Spark jobs.

---

## Knowledge Required

**Unit testing transformation logic**: Pure transformation functions — the reading frame rule, exon deletion parsing, HGVS normalisation — can and should be tested in isolation with pytest and a small set of known-good/known-bad inputs. These functions should be extracted from pipeline definitions into a testable module. This is independent of the pipeline framework choice.

**Integration testing**: Running a pipeline end-to-end against a realistic test dataset and asserting on the output schema, row counts, and specific known outputs. For DLT, this requires a Databricks environment (cannot run locally without the DLT runtime). For Spark jobs, a local Spark session is sufficient for small datasets. The integration test dataset for this project should include: a sample of real ClinicalTrials.gov records, at least one record that fails each quality expectation, and at least one record for each eligibility criterion computability class.

**Schema regression testing**: When an upstream table schema changes (e.g., ClinicalTrials.gov adds or renames a field), downstream Silver transformations must not silently degrade. Delta schema enforcement catches write-time structural breaks, but semantic breaks (a field is renamed and the old name now reads as null) require explicit assertions. A schema regression test runs the pipeline against a fixed input snapshot and asserts that the Silver output matches an expected schema exactly.

**Data contract testing**: Each Gold product has a published schema contract. A contract test runs after a pipeline execution and asserts that the actual Gold table conforms to the declared contract schema — column names, types, nullability, and any declared constraints. This is the test that would catch a breaking change before a consumer does.

**Test data strategy**: Real ClinicalTrials.gov records are publicly available and suitable for integration tests. Synthetic data generation is needed for edge cases (e.g., a trial with no eligibility criteria, a trial with 50 nested criteria) that may not exist in the real dataset. Patient-level data, when introduced, requires anonymisation or fully synthetic generation — real patient data must never appear in test fixtures.

**CI/CD integration**: Tests must run automatically on every pull request. Unit tests run locally and in CI without Databricks access. Integration tests require a Databricks environment — this should be a dedicated test environment, not production. The CI/CD pipeline should block merges on unit test failure; integration test failures should be reported but may require manual review for data-dependent failures.

---

## Decision (to be filled in before Bronze build)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the first pipeline is built.*