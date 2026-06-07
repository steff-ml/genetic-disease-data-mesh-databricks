# LinkedIn Post Sequencing

Positioning goal: scientific data engineer / architect working at the intersection
of genomics, clinical standards, and data platform engineering.

Tone: problem-first, technically honest, no hype. Each post teaches one concrete thing.

This is a living document. New posts are added as the project produces decisions and
results worth writing about. The doc-sync agent flags candidates after each session.

---

## What makes something post-worthy

A change or decision is worth a post if it meets at least two of the following:

- **Non-obvious**: the right answer wasn't immediately clear; there was a real tradeoff or a surprising constraint
- **Consequential**: the decision has downstream effects on the system or on patients
- **Transferable**: an engineer on a different project could apply the same thinking
- **Grounded**: it can be illustrated with a specific number, formula, error message, or concrete example — not just an abstract principle

Posts about "I chose X" are weak. Posts about "I had to choose between X and Y because of Z constraint, and here is what I learned" are strong.

---

## Narrative arc

The posts follow a story, not a topic list. Someone who reads all of them should
finish understanding both the human problem and the engineering response to it.

**Act 1 — Why this problem exists** (posts 01–02): the human stakes
**Act 2 — The data reality** (posts 03–04): what the sources actually look like
**Act 3 — Engineering decisions** (posts 05–07): what was built and why
**Act 4 — Hard constraints** (posts 08–10): the non-negotiable requirements
**Act 5 — Technology choices** (posts 11–13): specific platform decisions and tradeoffs
**Act 6 — Results and reflection** (posts 14–15): what the system reveals and what went wrong

---

## Publishing schedule

| # | Act | Title | Publish when | Prerequisite |
|---|-----|-------|-------------|--------------|
| 01 | 1 | *Why I built a data platform for a disease that affects 1 in 3,500 boys* | Now — June 2026 | None — the problem exists regardless of what is built |
| 02 | 1 | *One formula that determines whether a child qualifies for a drug* | Now — June 2026 | Reading frame calculator written |
| 03 | 2 | *The databases that should agree on DMD mutations — don't* | Now — June 2026 | LOVD + ClinVar exploration done |
| 04 | 2 | *What pulling from six genomic APIs actually looks like* | July 2026 | All Bronze exploration notebooks done |
| 05 | 3 | *When your sources disagree on whether a variant is pathogenic, what does your pipeline do?* | August 2026 | Silver conflict detection (ADR-06) built |
| 06 | 3 | *Why string matching two genomic databases is mostly wrong* | August 2026 | HGVS normalisation in Silver |
| 07 | 3 | *I wrote data contracts before the Silver layer existed — here is why* | September 2026 | First Gold contract live in CI |
| 08 | 4 | *The patient privacy requirement that has no clean answer* | September 2026 | ADR-24 implemented (PHI architecture live) |
| 09 | 4 | *Why row-level access control requires more than roles* | October 2026 | PHI access controls deployed and verified |
| 10 | 4 | *Three clinical data standards, three different jobs* | October 2026 | OMOP, FHIR, SDTM templates in use |
| 11 | 5 | *Why I chose Delta Live Tables over regular Spark jobs for this pipeline* | November 2026 | DLT Silver pipeline running in production |
| 12 | 5 | *Stable variant identifiers: what breaks when you use HGVS as a join key* | November 2026 | VRS IDs in Gold |
| 13 | 5 | *(reserved — filled by doc-sync as technology decisions are made)* | TBD | TBD |
| 14 | 6 | *The mutation gap: which DMD exons have no approved therapy and no recruiting trial* | December 2026 | Gold + dashboard live |
| 15 | 6 | *Six months building data infrastructure for a rare disease: what I would do differently* | January 2027 | Full platform operational |

---

## Technology decision candidates (Act 5 pool)

As architectural choices are made, doc-sync will flag them against this list.
Confirmed decisions move into the schedule above as post 13 or additional posts.

| Decision | Why it might be a post | Status |
|----------|----------------------|--------|
| DLT vs Spark Jobs | Declarative quality expectations + event log vs portability + testability. When does the DLT abstraction pay off? | Candidate |
| Serverless vs classic clusters | Startup time, library management, cost model. Why serverless for interactive; why classic for long-running pipelines | Candidate |
| Databricks Asset Bundles vs Terraform | DAB for Databricks-native resources; Terraform for multi-cloud. Where the boundary sits | Candidate |
| Unity Catalog column masks vs application-level masking | Why pushing PHI masking to the engine is safer than enforcing it in application code | Candidate |
| DLT expectations vs dbt tests | Different failure modes, different pipeline phases. When you are in the Databricks ecosystem, which should you use? | Candidate |
| Bitol ODCS contracts vs homegrown schema validation | What a standard contract format gives you that a hand-rolled JSON schema does not | Candidate |

---

## Posts you can publish right now (June 2026)

Posts 01, 02, and 03 require nothing beyond what is already built. They describe
the problem and early findings — which are credible now.

Post 04 becomes publishable once all six Bronze exploration notebooks are complete
and you have real null-rate numbers and API quirks to draw from.

Do not publish posts 05 onward before the prerequisite is true. Specificity is what
makes these posts valuable, and specificity requires real results.

---

## Format guidance

- **Opening line**: a problem statement, not an announcement. Never "I built..." or "Excited to share..."
- **Length**: 200–280 words. Long enough for depth, short enough to read on a phone.
- **Structure**: problem → why it's non-obvious → what the answer turned out to be → one takeaway
- **Concrete detail**: one specific number, formula, error message, or example per post. This is what makes people share.
- **Hashtags**: max 3, at the very end. Never in the body of the post.
- **Images**: a clean code snippet screenshot or a single-panel diagram outperforms a stock photo.
- **Cadence**: one post every 10–14 days. Consistency matters more than frequency.
