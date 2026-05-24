# ADR-15: Separate Matching Domain

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Deferred
**Trigger:** Expansion beyond Duchenne to a second disease area with independent matching logic, or a second independent trial domain consumer, or matching logic becoming an ML model requiring its own versioning and validation lifecycle.
**Depends on:** ADR-03 (domain boundary principle)
**Blocks:** Domain topology

---

## Current position

Clinical domain owns the match product per ADR-05. No separate matching domain at current scope.

---

## Knowledge Required When Triggered

Dehghani on domain proliferation anti-patterns — when splitting domains adds coordination overhead rather than reducing it. A new domain is justified when the data, the team, and the consumer question are genuinely independent, not when it is organisationally convenient.

Understanding of the new disease area's matching logic — does it share enough with Duchenne (same reading frame rule, same AON mechanism) to stay in one domain, or is it a genuinely different computational problem? SMA copy number matching, for example, is structurally different from DMD exon deletion matching.

ML model lifecycle requirements — if matching logic becomes a trained model rather than a rule engine, it requires its own versioning, validation, and audit trail. This may justify a separate domain regardless of disease area.

---

## Decision (to be filled in when triggered)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed when the trigger condition is met.*