# Explanation-quality ratings (Section 4.8, Table 15)

Three dimensions, 1–3 scale: `נאמנות_עובדתית` (factual faithfulness), `רלוונטיות_משפטית` (legal relevance), `שלמות` (completeness). Rows: 100 drug pairs + 141 weapon pairs, for each of three explaining models (Claude Sonnet 4.6, Gemma-4-31B, GPT-4.1), all on the Hybrid-Full representation.

| Folder / file | Stage |
|---|---|
| `first_pass_claude_opus/explainability_*.csv` | Stage 1: first-pass ratings (Claude Opus 4.7, `scripts/5_explainability/claude_annotate.py`), April 2026. The weapon files for Claude and Gemma were later superseded by the re-run on the corrected feature base (see `final_labels/RESULTS_SUMMARY.md` §6.1). |
| `final_labels/changelog.csv`, `final_labels/relevance_rationale.csv`, `final_labels/final_qa_changelog.csv` | Stages 2–4: full review against the feature vectors, redefinition of legal relevance per the annotation guides, QA. |
| `second_pass_blind/` | Stage 5: second, blind pass (GPT-5) — prompt (`PROMPT.md`), rubric (`RUBRIC.md`), guides, and the inputs handed to the blind rater (`data_blind/`, model identity and first-pass labels removed; `data_current/` = first-pass labels at that time). |
| `final_labels/changelog_adjudication.csv`, `changelog_rulings_1_2.csv`, `changelog_ruling_5.csv` | Stage 6: adjudication of the 522 disagreements and the five policy rulings. |
| **`final_labels/explainability_drugs_*_ADJUDICATED.csv`** | **Final drug labels (Table 15, drugs rows).** Exported from `explainability_final_labels_adjudicated_2026-08-16.xlsx`. |
| **`final_labels/explainability_weapon_claude_sonnet_4_6_RERUN.csv`, `..._gemma4_31b_or_RERUN.csv`, `..._gpt4_BLIND.csv`, columns `*_blind`** | **Final weapon labels (Table 15, weapon rows)**, after the re-run of Claude and Gemma on the corrected weapon feature base (19 Aug 2026). The unsuffixed columns in the same files are the original-rubric labels (RESULTS_SUMMARY §4.1). |
| `final_labels/explainability_weapon_*.csv` (no suffix), `explainability_final_labels.xlsx` | Superseded intermediate weapon state (old feature base); kept for the audit trail. |
| `final_labels/RESULTS_SUMMARY.md`, `RESULTS_TABLES.xlsx` | Narrative and tables of the whole process, including the per-stage counts (327 of 2,169 labels changed). |

`tools/verify_headline_numbers.py` recomputes Table 15 from the two bold rows above.
