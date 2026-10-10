# Validating LLM-Based Case Similarity for Sentencing-Range Determination in Hebrew Criminal Law

Code, data and results for the manuscript submitted to *Artificial Intelligence and Law*.
Everything the paper reports (Tables 1–22, Figures 1–7, Online Resource 1) is derived from the files in this repository. No API call is needed to recompute any table or figure; API calls are needed only to regenerate the LLM outputs themselves (feature extraction, pairwise similarity scores, explanations), which are all stored here.

The repository is anonymised for review: annotators appear as A1–A7, workspace paths are replaced by `<WORKSPACE>`, and no author information is included.

## Layout

```
data/
  annotation/            gold standard: 241 similarity pairs (100 drugs, 141 weapons) with per-annotator
                         labels, inter-annotator agreement, per-verdict manual feature annotation
                         (Google-Form exports, converted to the schema), agreement scripts
  representations/       the seven case representations for the annotated pairs, one CSV per
                         representation per domain (Manual, GPT-Schema, GPT-Free, GPT-Law,
                         Hybrid-Manual, Hybrid-Full, Raw Facts)
  extraction_validation/ manual ground truth and automatic extraction outputs used for Table 8
  citation_classifier/   573 labelled paragraphs (54 judgments), tokenizer, config, threshold
  range_corpus/          corpus_4432.csv (verdict, domain, indictment_facts, sentencing_range_low/high,
                         months); llm_pair_scores_452225.csv (the union of all GPT-4.1 pairwise scores
                         used by the prediction methods, Hybrid-Full representation; 452,225
                         unique pairs over six scoring batches); master_inventory.csv;
                         citation_network/ (edges, pair types, node metrics);
                         embeddings/ (5-fold supervised DictaBERT and SimCSE verdict embeddings)
results/
  similarity/            per-configuration metrics (cells_n13.csv: 7 reps x 13 LLMs x 2 domains),
                         summary_qwk_n13.csv (Table 10), contrasts48.csv (Table 11 / 47 of 48),
                         pairwise_21x8_fdr.csv (Online Resource 1), baselines/ (Table 14; text baselines + pair-level tests, Table B5),
                         confusion_3way/ (Figure 3), figures/ (CLDs, Figure 2),
                         llm_predictions/ (raw per-pair LLM outputs for all 182 configurations)
  explainability/        first_pass_claude_opus/ (Claude Opus 4.7 ratings), second_pass_blind/
                         (GPT-5 blind pass: prompt, rubric, inputs), final_labels/ (adjudicated
                         labels and changelogs; Table 15). See results/explainability/README.md
                         for which file and column is final.
  feature_analysis/      field-name inventories, schema mapping, beyond-schema mass (Tables 18–21)
  sentencing_range/      data/ (per-query errors for M1–M10, bootstrap CIs, paired tests, sweeps;
                         Table 16, Figures 1, 4–7), plots/, audit/, methodology notes,
                         DATA_PROVENANCE_4432.md
scripts/
  1_preprocessing/       DOCX -> CSV, indictment-facts isolation, citation extraction and classifier
                         training, sentencing-range extraction (few-shot GPT), unified file
  2_representations/     schema extraction (GPT-Schema), free / statute-grounded extraction
                         (GPT-Free, GPT-Law), hybrid enrichment and post-processing, extraction
                         evaluation against the manual ground truth (extraction_eval_*)
  3_similarity_scoring/  v6_score_multimodel_experiment.py: the pairwise LLM scorer used for all
                         182 configurations; model_config.py lists model identifiers
  4_similarity_analysis/ paper_results_qwk.py (QWK oracle / 10-fold CV, Spearman, C-index,
                         Wilcoxon + FDR, CLDs), random and embedding baselines, confusion analysis
  5_explainability/      explanation generation, Claude first-pass rating, blind-pass agreement
  6_feature_analysis/    inventory, direct schema mapping, beyond-schema classification
  7_sentencing_range/    embeddings/ (5-fold supervised and SimCSE training), candidate_filters/
                         (citation, supervised, SimCSE, BM25, TF-IDF; LLM re-ranking batches),
                         analysis/ (rigor_phase_a_v2.py -> per-query errors; rigor_phase_b.py ->
                         CIs and paired tests; thesis_story_part1.py -> Figure 4; sweeps and plots)
validation/              hand check of 100 randomly sampled corpus ranges against the source
                         judgments (Section 3.1.3)
provenance/MANIFEST.csv  source path, size and SHA-256 of every packaged file
tools/                   build_repo.py (assembles this folder from the working tree; run in the
                         order build_repo -> anonymize -> redact_names), verify_headline_numbers.py
```

## Method identifiers

| Paper | Files |
|---|---|
| M1 global median | `global_median` |
| M2 offense-matched random | `offense_matched_random` |
| M3 TF-IDF + Ridge | `tfidf_ridge` |
| M4 BM25 | `bm25` |
| M5 Supervised alone | `sup_only` |
| M6 SimCSE alone | `simcse_only` |
| M7 Citation + LLM | `citation_llm` |
| M8 Supervised + LLM | `sup_llm` |
| M9 SimCSE + LLM | `simcse_llm` |
| M10 LLM-best | `llm_best` |
| (random pool + LLM, Online Resource 1) | `random_llm` |

Representation identifiers in file names: `fe` / `fe_manual_schema` = Manual, `fe_gpt_schema_v2` / `fe_gpt_schema` = GPT-Schema, `with_gpt_features` / `gpt_free` = GPT-Free, `with_gpt_law_features` / `gpt_law` = GPT-Law, `hybrid` / `hybrid_manual_gpt` = Hybrid-Manual, `hybrid_full_gpt` = Hybrid-Full, `with_indicment_facts` / `facts` = Raw Facts.

## Recomputing the paper's numbers without API calls

```sh
pip install -r requirements.txt
python tools/verify_headline_numbers.py      # Tables 10, 11, 15, 16 from packaged CSVs
```

The full analysis chain, from stored LLM outputs to the tables:

1. Similarity (RQ1–RQ2): `scripts/4_similarity_analysis/paper_results_qwk.py` reads
   `results/similarity/llm_predictions/` and writes the per-cell metrics, the 10-fold CV variant,
   Wilcoxon + Benjamini–Hochberg contrasts and the CLD figures.
2. Baselines (Section 4.7): `random_baseline.py`, `embedding_baseline.py`, `embedding_all_reps.py`,
   `significance_vs_*.py`.
3. Explanations (RQ3): `results/explainability/final_labels/` are the adjudicated labels;
   `scripts/5_explainability/agreement.py` recomputes agreement between passes.
4. Feature anatomy (Section 5.3): `scripts/6_feature_analysis/` over `data/representations/`.
5. Sentencing range (RQ4): `scripts/7_sentencing_range/analysis/rigor_phase_a_v2.py` recomputes
   per-query errors for all methods from `data/range_corpus/` (corpus, pair scores, embeddings,
   citation network); `rigor_phase_b.py` produces the CIs and paired tests in
   `results/sentencing_range/data/`. `_run_all_4432.sh` lists the order.

Scripts keep the relative paths of the original working tree (`experiments/...`); the mapping from
those paths to this repository is in `provenance/MANIFEST.csv` (source column).

## Regenerating LLM outputs

Requires provider keys in `.env` (see `.env.example`). Model identifiers and access dates are in
`scripts/3_similarity_scoring/model_config.py`. Scoring is
deterministic in intent (temperature 0; 0.1 for GPT-4.1-mini extraction and the corpus-scale
batches) but provider-side changes mean re-runs need not reproduce the stored outputs exactly.

## Data notes

- Judgments are public court records obtained from the Nevo database. The repository contains the
  isolated indictment-facts paragraphs and structured features, not full judgment texts;
  identifiers (`verdict`) are Nevo case numbers.
- `results/sentencing_range/data/rigor_raw_per_query_K.csv.gz` is gzipped (source 102 MB).
- Known corpus artefacts are left as used in the experiments and documented in
  `results/sentencing_range/audit/` and `validation/`.
