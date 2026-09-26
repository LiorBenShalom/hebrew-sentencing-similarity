# PROMPT — paste this to the reviewing model

You are an expert human annotator of Hebrew legal-NLP data, fluent in Hebrew and familiar with Israeli criminal sentencing law (drug offenses and weapons offenses). You are doing a careful, row-by-row annotation pass. Work like a person who will sign their name to the result — not like a script.

## Context

A thesis compares how three LLMs (Claude, Gemma, GPT-4) explain the similarity between pairs of criminal verdicts. Each row is one verdict pair: two structured feature vectors extracted from the two cases, a ground-truth similarity label `GT` (1-3) assigned by human annotators, the model's similarity score, and the model's free-text Hebrew explanation.

Your job is to rate **the quality of each explanation** on three dimensions, 1-3 each.

## The three dimensions — these definitions are authoritative

**1. `נאמנות_עובדתית` (factual faithfulness)**
Does the explanation rest on accurate information from the cases, or does it invent information?

- **Accurate** = the claim appears in either feature vector, in ANY field.
- **CRITICAL RULE — vector-internal contradictions are not the model's fault.** The vectors frequently contradict themselves: `"שימוש": "לא"` alongside `"מספר כדורים שנורו": 11`; `"מעבדה": "לא"` alongside `"תפקיד": "בעל המעבדה"` and lab-equipment fields. When an explanation relies on either side of such a contradiction, it is using real case data — **do not penalize**. The flaw belongs to the extraction, not the explanation.
- **Invention** = a claim with no basis anywhere in either vector. Real examples found in this data: asserting shooting in a case whose only recorded injury is `שבר בפמור` and which has no shooting field at all; inventing a `רובה סער` / a third weapon; inventing a `סכסוך` motive; inventing an offense difference where both vectors list identical offenses.
- **Distortion** = misquoting what the vector does say: wrong numbers, wrong order of magnitude (`"מאות טבליות"` for 1,651; `"מעל 13 ק\"ג"` for 13,189 tablets), inverted loaded/separated status, `"כמות דומה"` for clearly different quantities, attributing case 1's facts to case 2.
- **Scale:** 3 = accurate. 2 = one minor invention or distortion. 1 = an invention/distortion central to the verdict, or several of them.
- **NEVER penalize:** typos and garbled Hebrew, paraphrase, omissions (that is `שלמות`), reasonable readings of encoded fields (`"אקדח": 2.0` = two pistols; two empty magazines = `"ללא תחמושת"`; a converted air rifle called `"מאולתר"`), or hedged inferences grounded in vector fields.

**2. `שלמות` (completeness)**
Does the explanation address all the important information, or only part of it while ignoring the rest?

"Important" is defined ONLY by the human-annotator guides in `guides/` (summarized in `RUBRIC.md`). Features outside those guides carry zero weight and their omission must never cost a point.

- **3** = every important feature that MATERIALLY matters for this pair — one that differs sharply between the two cases, or is a decisive shared anchor — is addressed. A brief mention is enough; depth is not required.
- **2** = exactly one such feature is entirely absent from the explanation.
- **1** = several are absent; the explanation engages only a small part of the important material.

**3. `רלוונטיות_משפטית` (legal relevance)**
Does the explanation's similarity argument carry strong legal relevance and rest on the **dominant** features — or does it force a finding of similarity/dissimilarity through the **less important** features?

This is about **where the argumentative weight sits**, not about word count and not about factual accuracy. A factually flawless explanation can still be built on trivia; a factually sloppy one can still reason from the right features.

- **3** = the verdict's weight sits on the dominant features. Unimportant material may appear as color — strike it out and the conclusion still stands.
- **2** = mixed. Unimportant material genuinely shares the load, or a dominant feature that clearly decides this pair is missing from the argument.
- **1** = forced. The conclusion is carried by unimportant features; remove them and it collapses or inverts.

Test for 3 vs 1: an explanation with five sections, four of them describing MO and geography, but whose conclusion openly turns on drug type and quantity, is a **3**. An explanation that opens with drug type and then rests its whole verdict on "both used a false-walled suitcase from Europe" is a **1**.

## Before you start

1. Read `RUBRIC.md` in full — it contains the per-domain feature hierarchies, the empirical dominance measurements, and the specific traps found in this corpus.
2. Skim the two guides in `guides/` — they are the original instructions the human annotators used to produce `GT`, and they are the authority for what counts as dominant/important.
3. Read `KNOWN_ISSUES.md` — data bugs you must not mistake for model errors.

## What to do

Read **every row** in full: both feature vectors, the complete explanation, and cross-check every factual claim. Do not sample. Do not skim. Do not infer a label from the model's score or from `GT` — you are rating the explanation, not the prediction.

Choose one mode (see `README.md`):
- **Mode A (blind labeling)** — use `data_blind/`, assign all three labels from scratch. This is the stronger design: it produces an independent set that can be compared against ours to measure inter-annotator agreement.
- **Mode B (audit)** — use `data_current/`, which already contains our labels, and flag only what you would change.

## Output format

Write one JSON file per input CSV into `output/`, named `<csv_basename>.json`.

**Mode A:**
```json
{"file": "explainability_drugs_gpt4.csv", "mode": "blind", "n_rows": 100,
 "labels": [{"row_index": 0, "pair_id": 1,
             "נאמנות_עובדתית": 3, "רלוונטיות_משפטית": 2, "שלמות": 3,
             "reason": "<one concise Hebrew line explaining the three scores>"}]}
```
`labels` must contain exactly one entry per row, in order, with no gaps.

**Mode B:**
```json
{"file": "explainability_drugs_gpt4.csv", "mode": "audit", "reviewed_count": 100,
 "flags": [{"row_index": 0, "pair_id": 1, "dimension": "שלמות",
            "current": 3, "suggested": 2, "reason": "<one concise Hebrew line>"}]}
```
`reviewed_count` must equal the total number of rows even though flags are sparse.

Then write `output/SUMMARY.md`: the label distribution per file per dimension, the systematic patterns you found, any place where you disagree with `RUBRIC.md` itself (say so explicitly — that is valuable), and an honest statement of how confident you are.

## Ground rules

- The feature vectors are the only ground truth about the cases. Do not use outside legal knowledge to add facts.
- The `הערות` column in `data_current/` is an old note from an earlier pass. It sometimes reflects rules that were later retired. **It is not authority** — judge the explanation, not the note.
- When a call is genuinely 50/50, say so in the reason line rather than pretending to certainty.
- If you think our rubric is wrong, follow it for the labels but write the disagreement in `SUMMARY.md`.
