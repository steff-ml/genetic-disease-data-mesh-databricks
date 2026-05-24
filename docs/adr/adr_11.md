# ADR-11: Computability Classification Schema

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-06 (eligibility representation standard), ADR-10 (GenAI extraction scope)
**Blocks:** Gold matching logic design

---

## Knowledge Required

20-30 DMD trial eligibility texts from ClinicalTrials.gov — the empirical basis for knowing which criterion types are actually computable. The schema should reflect the criterion types that appear in real trials, not hypothetical ones.

Understanding of the matching logic to be built downstream: a criterion type is only worth classifying as deterministic if the matching rule for it can actually be implemented. Classification without implementable matching logic is premature.

HPO (Human Phenotype Ontology) coverage for neuromuscular disease — some phenotypic criteria (ambulatory status, functional scales) are only classifiable as deterministic if HPO has a term for them and a standardised value set exists. HPO gaps constrain what can be called deterministic.

Understanding of LLM confidence calibration — required to define what the confidence score field means and what threshold distinguishes probabilistic from non-computable.

---

## Partial Decision

Three classes: deterministic (matching rule implementable without LLM), probabilistic (LLM extraction with confidence score), non-computable (requires clinical input not representable as data). Plus a confidence score for probabilistic extractions, plus an extracted_by field recording model version and prompt version for auditability.

---

## References

**Books**
No direct book coverage — this is a domain-specific design decision.

**Databricks documentation**
- [Delta Lake data types](https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html) — specifically the STRUCT type for representing the classification fields (class, confidence score, extracted_by) in the Silver schema

**Primary sources**
- HPO (Human Phenotype Ontology) documentation — coverage of neuromuscular phenotypes determines what is classifiable as deterministic
- 20–30 DMD trial eligibility texts from ClinicalTrials.gov — the empirical basis; the schema must reflect criterion types that actually appear in real trials

---

## Decision (to be filled in)

*Context, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before Silver layer build.*