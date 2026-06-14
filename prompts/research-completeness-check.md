# Prompt: Research completeness check

**Stage:** Candidate
**Quadrant:** Moat (sparring only — AI surfaces gaps, you close them)
**Uses logged:** 0
**Promotes to:** not a Skill candidate — judgment stays manual; the prompt is the asset

---

## When to use

When you feel like research is "probably done" but can't tell if you're stopping because it's actually complete or because you're tired of looking. Run this before moving from Research the problem → Architecting.

---

## Prompt

I am researching [TOPIC — e.g. "regulatory constraints on linking patient genomic data to clinical trial registries"]. My goal is to know enough to make defensible architecture decisions, not to know everything.

Here is what I have found so far:

[PASTE RESEARCH NOTES / SUMMARY]

The specific decisions this research needs to support are:

[LIST THE ARCHITECTURE OR DESIGN DECISIONS THAT DEPEND ON THIS RESEARCH — e.g. "which identifiers to use for patient records", "what consent model to encode in the data product"]

Please do three things:

**1. Known unknowns**
Based on what I've shared, what questions remain unanswered that are likely to matter for the decisions listed? List them as concrete questions, not vague areas.

**2. Likely blind spots**
What is a researcher in this area commonly wrong about, or what do people typically underestimate? Name specific failure modes — regulatory edge cases, ontology conflicts, version discontinuities, or adoption gaps in the community.

**3. Stop / continue call**
Given the decisions I need to make: is the research I have plausibly sufficient to proceed, or are there gaps that would predictably cause problems during architecture or build? Give me a direct recommendation with one sentence of reasoning.

Important: you are not answering the research questions — you are helping me see what I have not yet looked for. Flag anything you are uncertain about. I will verify open items before proceeding.

---

## Notes on use

- The model's "known unknowns" list is a lead, not a verdict — some items will be irrelevant to your specific context
- If item count on the list is low (under 4), either research is genuinely solid or the model lacks domain coverage; cross-check with a domain source
- A "continue" recommendation from the model does not mean stop — it means the gaps found are manageable; your judgment still governs
- This is not a Skill candidate: the judgment about whether to proceed is always yours and context-dependent
