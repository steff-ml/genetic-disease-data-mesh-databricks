# ADR-05: Match Product Ownership

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Working Decision
**Depends on:** ADR-03 (domain boundaries determine who could own the match product)
**Blocks:** ADR-13 (interface type for the match product)

---

## Knowledge Required

The consumer question test: whoever is accountable for answering the business question owns the product that answers it
Understanding of cross-domain product patterns: consuming domain produces a Gold product from upstream published products
Dehghani on domain ownership accountability

Decision for this project: Clinical trials domain owns the match product. It consumes the genomic domain's published patient variant product. No separate matching domain at current scope.

---

## References

**Books**
- Dehghani, *Data Mesh* ch4, ch8: domain ownership accountability and cross-domain product patterns

**Databricks documentation**
None directly — this is an ownership decision, not a technical one.

---

## Decision

### Context

The primary output of this platform is `gold.patient_trial_eligibility` — the record of which patients are eligible for which trials. This product is produced by joining the Discovery domain's published mutation profile against the Clinical domain's trial eligibility catalogue and applying eligibility logic. The question is which domain owns this cross-domain product.

### Decision

The **Clinical domain** owns the match product (`clinical.gold.patient_trial_eligibility`) and all related Gold products in the patient-trial matching family.

The consumer question test (Dehghani): the domain accountable for answering the primary business question owns the product that answers it. The business question is "which trials is this patient eligible for?" This is a clinical and translational question. A clinician, clinical coordinator, or registry data manager asks it. The Clinical domain team is accountable for the answer.

The Clinical domain is a **consumer** of `discovery.gold.patient_mutation_profile`. It applies trial eligibility logic (Layer 2: approach-specific mutation criteria) and patient-level criteria (Layer 3) from `clinical.gold.trial_eligibility_catalogue` to the mutation profile, and publishes the result. The Clinical domain does not own or transform variant data.

**No separate Matching domain** is established at current scope. This is revisited in ADR-15.

### Alternatives considered

**Discovery domain owns the match product**: wrong. The matching business question is clinical. Placing the match product in the Discovery domain means a genomics team is accountable for clinical eligibility decisions — a misalignment of domain expertise and accountability. The Discovery domain does not have access to trial eligibility criteria; it has no basis for producing the match.

**Separate Matching domain**: premature at current scope. A Matching domain is warranted when matching logic is independently deployable — when it has its own versioning, validation, and monitoring lifecycle separate from both source domains. At current scope, matching is a rule engine applied inside the Clinical Gold pipeline, not an independent service. Adding a domain boundary here adds coordination overhead without adding analytical independence.

### Rationale

The consumer question test produces an unambiguous answer: the Clinical domain answers the question. Ownership follows accountability. The Clinical domain declares a consumer dependency on `discovery.gold.patient_mutation_profile` and is responsible for handling breaking changes in that upstream product contract.

### Consequences

- `clinical.gold` contains: `trial_eligibility_catalogue`, `patient_trial_eligibility`, `therapy_addressable_population`, `mutation_coverage_gaps`, `patient_trial_eligibility_delta`
- The Clinical domain's DLT pipeline service principal is granted read access to `discovery.gold.patient_mutation_profile` specifically — not to the full Discovery catalog
- The Discovery domain's `patient_mutation_profile` Bitol contract lists the Clinical domain as a named consumer; contract major version changes require consumer notification before deployment

### Compliance implications

None beyond the standard data product contract requirements from ADR-04. The match product is not patient-level data at current scope (it links mutation profiles to trials, not named individuals); patient identification is a later-stage concern.

### Assumptions

- Cross-domain Unity Catalog grants are service principal-level, not user-level: the Clinical domain's pipeline identity gets read access to `discovery.gold.patient_mutation_profile`, not to `discovery.*`

### Review trigger

If matching logic becomes a trained ML model requiring its own audit trail, versioning, and model validation lifecycle independent of the Clinical domain's pipeline lifecycle, revisit whether a separate Matching domain is warranted (ADR-15).
