# Prompt: One-pager from research completeness check

**Stage:** Candidate
**Quadrant:** Automate (first draft only — accuracy and citation verification stay Moat)
**Uses logged:** 0
**Promotes to:** `one-pager-from-research` Skill (once stable)

---

## Difference from other writing prompts

`blog-from-research.md` produces a hypothesis-testing post intended to attract community pushback before building starts. This prompt is for *after* the research is substantially complete — the goal is to communicate a project and its rationale to a professional audience who may be considering hiring you or collaborating. The output is a one-pager, not a blog post: tighter structure, concrete numbers foregrounded, the "so what" made explicit.

---

## When to use

After running `research-completeness-check.md` and receiving feedback on known unknowns, blind spots, and gaps — use this prompt to turn that feedback and the underlying research into a revised or new one-pager that addresses those gaps. The research completeness check output is the primary input, not the one-pager draft.

---

## Prompt

I need a one-pager (500–800 words) describing a technical project for a professional audience of data engineers, technical leads, and hiring managers in life sciences and data-intensive industries.

**My positioning goal:**
[STATE THE ROLE YOU ARE TARGETING — e.g. "scientific data engineer / architect in rare disease or biotech"]

**The research completeness check identified these gaps in my existing draft:**

*Known unknowns not yet addressed:*
[PASTE THE KNOWN UNKNOWNS LIST FROM THE COMPLETENESS CHECK]

*Blind spots identified:*
[PASTE THE BLIND SPOTS LIST FROM THE COMPLETENESS CHECK]

**The underlying research I am drawing from:**
[PASTE OR SUMMARISE THE KEY RESEARCH FINDINGS — statistics, citations, mechanisms, quantified impacts. Do not paste the draft — paste the research. The prompt will construct a new draft from research, not polish an existing one.]

**The project in one sentence:**
[DESCRIBE WHAT YOU ARE BUILDING AND WHO IT IS FOR]

**The specific decisions or choices that distinguish this project:**
[LIST 2–4 NON-OBVIOUS DECISIONS: architectural, technical, or methodological. E.g. "chose DLT over regular Spark jobs because...", "used OMOP rather than SDTM because..."]

---

Write a one-pager that:

1. **Opens with a concrete, patient-specific or domain-specific problem** — not a general statement about data silos or industry trends. Lead with the most striking specific number or mechanism from the research. The first sentence should be falsifiable.

2. **States the general problem class and why it compounds** — one short paragraph contextualising the opening in the broader landscape, with references where the research provides them.

3. **Quantifies the specific gap** — the most important statistic that makes the problem undeniable. One paragraph, one number, cited.

4. **Explains the mechanism** — if the problem involves a formula, rule, or biological principle that governs eligibility or outcomes, state it explicitly. Readers who understand it will trust the rest; readers who do not will learn something. Do not hide it.

5. **Names the closest existing analogy and its limitation** — if a comparable platform exists in an adjacent domain, say what it does and why the current domain is structurally different. This establishes that the author knows the landscape.

6. **Describes the project** — what it is, who uses the output, what the architecture enables. Use "reference implementation" or "governed platform", not "learning project" or "side project". One paragraph.

7. **Explains the technology choices in terms of the problem** — not "Platform X supports Y" but "the problem requires Z because of constraint W, and Platform X addresses that by doing V." One paragraph.

8. **Closes with the scope of impact** — what this enables beyond the immediate use case: generalisability, downstream AI applications, or the specific failure mode it prevents.

**Tone**: technically honest, not boastful. Sounds like someone who has looked closely at a real problem and built something specific in response — not someone pitching a product. The reader should feel they are learning something, not being marketed to.

**Citations**: include inline citations (Author et al., year) for every statistical claim and every mechanism that comes from a published source. Flag any sentence where you are extrapolating beyond the provided research with *(verify)*.

---

## Notes on use

- **Verify every citation before publishing.** The model will construct plausible-looking references from the research you provide; some details (volume, page numbers, exact titles) will need checking against the original source.
- **The opening sentence is the most important thing to get right.** If it sounds like a general data industry observation, rewrite it. It should name a disease, a number, or a mechanism that only someone who has done the research would know.
- **Do not cut the mechanism section for length.** The formula, rule, or biological principle is what distinguishes this from every other data platform post. It is the reason a technical reader pauses.
- **The technology section must speak to a specific constraint**, not generic platform capabilities. If it reads like a vendor's feature list, rewrite it.
- Once used 3 times with consistently accurate first drafts, promote to a Skill.
