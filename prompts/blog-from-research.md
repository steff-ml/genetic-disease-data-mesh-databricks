# Prompt: Value-testing blog post from research

**Stage:** Candidate
**Quadrant:** Automate (structuring and drafting); hypothesis judgment stays Moat
**Uses logged:** 0
**Promotes to:** `blog-from-research` Skill (once stable)

---

## Difference from blog-from-adr

`blog-from-adr.md` explains a decision already made. This prompt is for *before* building starts — the goal is to expose a hypothesis to community feedback, not to document a conclusion. The structure, tone, and call to action are different.

---

## Prompt

I need a draft blog post whose purpose is to test whether a project idea is worth pursuing, by publishing early and inviting pushback from the community.

Context: I am a freelance data engineer specializing in hard scientific data integration. My audience is data engineers and technical leads, possibly with some domain scientists. They should feel invited to correct me, not impressed by me.

Here is the background:

**The problem I identified:**
[DESCRIBE THE PROBLEM IN ONE PARAGRAPH — the pain point, who has it, why it matters]

**My hypothesis / approach:**
[DESCRIBE YOUR PROPOSED APPROACH — what you plan to build or research, why you think it is the right direction]

**What I have learned so far:**
[SUMMARIZE KEY RESEARCH FINDINGS — relevant constraints, existing standards, what others have tried]

**What I am uncertain about:**
[LIST YOUR BIGGEST OPEN QUESTIONS — the things you genuinely do not know yet]

Write a draft post that:
- Opens with the problem in terms a reader would recognize from their own work, not from my framing
- States the hypothesis clearly and directly — what I am betting on and why
- Names the key research findings that led here, briefly — enough that a reader can assess whether my reasoning is sound
- Makes the uncertainty explicit — the open questions are an invitation, not a weakness to hide
- Ends with a specific ask: what kind of feedback would actually be useful (not "let me know what you think")
- Tone: honest and direct; sounds like someone thinking in public, not pitching

Length: 500–700 words. Use headers. Flag any sentence where you are extrapolating beyond what I provided.

---

## Notes on use

- Read the draft for accuracy before publishing — especially any claims that characterize the research findings
- The open questions section is the most important part; do not cut it for length
- If the draft sounds like it's defending the hypothesis, rewrite the framing — the goal is to attract correction, not endorsement
- Once used 3 times with consistently good output, promote to a Skill
