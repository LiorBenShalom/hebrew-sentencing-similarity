#!/usr/bin/env python3
"""Build the clean git folder `hebrew-sentencing-similarity` from the thesis workspace.

Copies only the final data, final results and the scripts that produced them.
Writes provenance/MANIFEST.csv (source path, destination, bytes, sha256).
Run from the workspace root (new_try). Idempotent: re-running overwrites.
"""
import csv, glob, gzip, hashlib, json, os, re, shutil, sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
OUT = os.path.join(ROOT, 'hebrew-sentencing-similarity')
E = 'experiments'
EXCL = re.compile(r'(\.bak|\.backup|\.DS_Store|__pycache__|\.pyc$|\.zip$|\.ipynb$|_bak_|\.log$)')
GZ_OVER = 95 * 1024 * 1024

# (source glob relative to ROOT, destination dir relative to OUT)
PLAN = [
    # ---------------- data ----------------
    (f'{E}/annotator_data/README.md', 'data/annotation'),
    (f'{E}/annotator_data/similarity/*', 'data/annotation/similarity'),
    (f'{E}/annotator_data/drugs/*', 'data/annotation/drugs'),
    (f'{E}/annotator_data/weapon/*', 'data/annotation/weapon'),
    (f'{E}/data/final/drugs/*.csv', 'data/representations/drugs'),
    (f'{E}/data/final/wep/*.csv', 'data/representations/weapon'),
    (f'{E}/drugs_extraction/data/*', 'data/extraction_validation/drugs'),
    (f'{E}/drugs_extraction/results/*.csv', 'data/extraction_validation/drugs'),
    (f'{E}/weapon_extraction/data/*', 'data/extraction_validation/weapon'),
    (f'{E}/weapon_extraction/results/*.csv', 'data/extraction_validation/weapon'),
    (f'{E}/results/0_preprocessing/citation_classifier/*', 'data/citation_classifier'),
    ('simcse_cuda_bundle/data/supervised_data.csv', 'data/range_corpus'),
    (f'{E}/data_per_domain/similarity_scores_combined.csv', 'data/range_corpus'),
    (f'{E}/data_per_domain/master_inventory.csv', 'data/range_corpus'),
    (f'{E}/data_per_domain/network_analysis/README.md', 'data/range_corpus/citation_network'),
    (f'{E}/data_per_domain/network_analysis/summary.json', 'data/range_corpus/citation_network'),
    (f'{E}/data_per_domain/network_analysis/citation_edges_all.csv', 'data/range_corpus/citation_network'),
    (f'{E}/data_per_domain/network_analysis/citation_edges_in_set.csv', 'data/range_corpus/citation_network'),
    (f'{E}/data_per_domain/network_analysis/citation_pair_types.csv', 'data/range_corpus/citation_network'),
    (f'{E}/data_per_domain/network_analysis/node_metrics.csv', 'data/range_corpus/citation_network'),
    ('simcse_cuda_bundle/outputs_supervised_filtered/verdict_embeddings_*_fold[1-5]_offenseFiltered.npy', 'data/range_corpus/embeddings/supervised_filtered'),
    ('simcse_cuda_bundle/outputs_supervised_filtered/verdict_index_*_fold[1-5]_offenseFiltered.csv', 'data/range_corpus/embeddings/supervised_filtered'),
    ('simcse_cuda_bundle/outputs_simcse_5fold/*', 'data/range_corpus/embeddings/simcse_5fold'),
    # ---------------- results ----------------
    (f'{E}/results/1_similarity/qwk/*.csv', 'results/similarity'),
    (f'{E}/results/1_similarity/qwk/*.png', 'results/similarity/figures'),
    ('online_resource_csv/*.csv', 'results/similarity'),
    (f'{E}/results/1_similarity/baselines/README.md', 'results/similarity/baselines'),
    (f'{E}/results/1_similarity/baselines/*.csv', 'results/similarity/baselines'),
    (f'{E}/results/1_similarity/baselines/*.png', 'results/similarity/baselines'),
    (f'{E}/results/1_similarity/v6_final_predictions/drugs/results_drugs/*_preds.csv', 'results/similarity/llm_predictions/drugs'),
    (f'{E}/results/1_similarity/v6_final_predictions/drugs/results_drugs/*_stats.json', 'results/similarity/llm_predictions/drugs'),
    (f'{E}/results/1_similarity/v6_final_predictions/weapon/results_weapon/*_preds.csv', 'results/similarity/llm_predictions/weapon'),
    (f'{E}/results/1_similarity/v6_final_predictions/weapon/results_weapon/*_stats.json', 'results/similarity/llm_predictions/weapon'),
    (f'{E}/old/results_1_similarity/explainability/hybrid_full/explainability_*.csv', 'results/explainability/first_pass_claude_opus'),
    (f'{E}/old/results_1_similarity/explainability/hybrid_full/mode_A_blind/*.md', 'results/explainability/second_pass_blind'),
    (f'{E}/old/results_1_similarity/explainability/hybrid_full/mode_A_blind/data_blind/*', 'results/explainability/second_pass_blind/data_blind'),
    (f'{E}/old/results_1_similarity/explainability/hybrid_full/mode_A_blind/data_current/*', 'results/explainability/second_pass_blind/data_current'),
    (f'{E}/old/results_1_similarity/explainability/hybrid_full/mode_A_blind/guides/*', 'results/explainability/second_pass_blind/guides'),
    (f'{E}/old/results_1_similarity/explainability/hybrid_full/final_labels/*', 'results/explainability/final_labels'),
    (f'{E}/analysis_representations/out/*', 'results/feature_analysis'),
    (f'{E}/analysis_representations/*.md', 'results/feature_analysis'),
    (f'{E}/results/2_sentencing_range/full_analysis_2026_05_13/data/*', 'results/sentencing_range/data'),
    (f'{E}/results/2_sentencing_range/full_analysis_2026_05_13/plots/*', 'results/sentencing_range/plots'),
    (f'{E}/results/2_sentencing_range/full_analysis_2026_05_13/*.md', 'results/sentencing_range'),
    (f'{E}/results/2_sentencing_range/audit/*', 'results/sentencing_range/audit'),
    (f'{E}/old/results_1_similarity/paper/confusion_3way/*.csv', 'results/similarity/confusion_3way'),
    (f'{E}/old/results_1_similarity/paper/confusion_3way/*.md', 'results/similarity/confusion_3way'),
    (f'{E}/old/results_1_similarity/paper/confusion_3way/*.png', 'results/similarity/confusion_3way'),
    # ---------------- scripts ----------------
    (f'{E}/scripts/pipeline/*.py', 'scripts/1_preprocessing'),
    (f'{E}/results/0_preprocessing/citation_classifier/train_classifier.py', 'scripts/1_preprocessing'),
    (f'{E}/src/extraction/*.py', 'scripts/2_representations'),
    (f'{E}/scripts/representations/*.py', 'scripts/2_representations'),
    (f'{E}/drugs_extraction/code/*.py', 'scripts/2_representations/extraction_eval_drugs'),
    (f'{E}/weapon_extraction/code/*.py', 'scripts/2_representations/extraction_eval_weapon'),
    (f'{E}/weapon_extraction/results/run_full_eval.sh', 'scripts/2_representations/extraction_eval_weapon'),
    (f'{E}/src/scoring/*.py', 'scripts/3_similarity_scoring'),
    (f'{E}/src/common/model_config.py', 'scripts/3_similarity_scoring'),
    (f'{E}/src/analysis/*', 'scripts/4_similarity_analysis'),
    (f'{E}/src/maintenance/*.py', 'scripts/4_similarity_analysis/maintenance'),
    (f'{E}/old/results_1_similarity/explainability/*.py', 'scripts/5_explainability'),
    (f'{E}/old/results_1_similarity/explainability/hybrid_full/mode_A_blind/scripts/*.py', 'scripts/5_explainability'),
    (f'{E}/analysis_representations/*.py', 'scripts/6_feature_analysis'),
    ('simcse_cuda_bundle/*.py', 'scripts/7_sentencing_range/embeddings'),
    ('simcse_cuda_bundle/*.sh', 'scripts/7_sentencing_range/embeddings'),
    ('simcse_cuda_bundle/requirements.txt', 'scripts/7_sentencing_range/embeddings'),
    (f'{E}/scripts/sentencing_baselines/*', 'scripts/7_sentencing_range/candidate_filters'),
    (f'{E}/results/2_sentencing_range/full_analysis_2026_05_13/scripts/*.py', 'scripts/7_sentencing_range/analysis'),
    (f'{E}/results/2_sentencing_range/full_analysis_2026_05_13/scripts/_run_all_4432.sh', 'scripts/7_sentencing_range/analysis'),
    # ---------------- validation ----------------
    ('article_repository/validation/range_sample_100/sentencing_range_validation_100_HE.csv', 'validation/range_sample_100'),
    ('article_repository/validation/range_sample_100/sample.csv', 'validation/range_sample_100'),
    # ---------------- misc ----------------
    (f'{E}/.env.example', '.'),
]

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def main():
    os.makedirs(OUT, exist_ok=True)
    rows, seen = [], set()
    for pat, dst in PLAN:
        srcs = sorted(glob.glob(os.path.join(ROOT, pat)))
        srcs = [s for s in srcs if os.path.isfile(s) and not EXCL.search(s.replace(ROOT, ''))]
        if not srcs:
            print('WARN no match:', pat); continue
        ddir = os.path.join(OUT, dst); os.makedirs(ddir, exist_ok=True)
        for s in srcs:
            name = os.path.basename(s)
            if name == 'supervised_data.csv': name = 'corpus_4432.csv'
            if name == 'similarity_scores_combined.csv': name = 'llm_pair_scores_254952.csv'
            d = os.path.join(ddir, name)
            rel = os.path.relpath(d, OUT)
            if rel in seen: continue
            seen.add(rel)
            size = os.path.getsize(s)
            if size > GZ_OVER and not d.endswith('.gz'):
                d += '.gz'; rel += '.gz'
                if not os.path.exists(d):
                    with open(s, 'rb') as fi, gzip.open(d, 'wb', compresslevel=6) as fo:
                        shutil.copyfileobj(fi, fo, 1 << 20)
                note = 'gzip (>95MB)'
            else:
                if not os.path.exists(d):  # never overwrite: anonymize/redact run after build
                    shutil.copyfile(s, d)
                note = 'copy'
            rows.append([os.path.relpath(s, ROOT), rel, size, sha256(s), note])
    os.makedirs(os.path.join(OUT, 'provenance'), exist_ok=True)
    with open(os.path.join(OUT, 'provenance', 'MANIFEST.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['source', 'destination', 'source_bytes', 'source_sha256', 'transformation']); w.writerows(rows)
    total = sum(r[2] for r in rows)
    print(f'{len(rows)} files, {total/1e6:.1f} MB source')

if __name__ == '__main__':
    main()
