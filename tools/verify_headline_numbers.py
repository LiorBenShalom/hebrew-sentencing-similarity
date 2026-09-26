#!/usr/bin/env python3
"""Recompute the paper's headline tables from the packaged CSVs (no API calls).
Table 10: mean over 13 LLMs per representation and domain (QWK_CV, QWK oracle, Spearman, C-index).
Table 11: Manual vs. each alternative on QWK (delta, d_z, FDR p).
Table 16: MAE (months) per method with bootstrap CI.
Run from the repository root."""
import pandas as pd, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cells = pd.read_csv(f'{R}/results/similarity/cells_n13.csv')
t10 = cells.groupby(['domain', 'rep'])[['qwk_cv', 'qwk', 'spearman', 'cindex']].mean().round(3)
print('Table 10 (mean over models)\n', t10.unstack('domain').to_string(), '\n')
c48 = pd.read_csv(f'{R}/results/similarity/contrasts48.csv')
print('Table 11 (Manual minus alternative, QWK)\n', c48[c48.metric == 'qwk'].round(3).to_string(index=False), '\n')
print('Significant contrasts (FDR p<0.05):', int((c48.pfdr < 0.05).sum()), 'of', len(c48), '\n')
mae = pd.read_csv(f'{R}/results/sentencing_range/data/rigor_mae_with_ci.csv')
order = ['global_median', 'offense_matched_random', 'tfidf_ridge', 'bm25', 'sup_only', 'simcse_only',
         'citation_llm', 'sup_llm', 'simcse_llm', 'llm_best']
mae = mae[mae.method.isin(order)].copy()
mae['M'] = mae.method.map({m: f'M{i+1}' for i, m in enumerate(order)})
print('Table 16 (MAE lower / upper bound, months)\n',
      mae.pivot(index='M', columns='domain', values=['mae_lo', 'mae_hi']).round(2).loc[[f'M{i}' for i in range(1, 11)]].to_string())

# Table 15: explanation quality (final labels)
D = ['נאמנות_עובדתית', 'רלוונטיות_משפטית', 'שלמות']
def fmt(d, cols): return '  '.join(f"{d[c].mean():.2f} ({(d[c]==3).mean()*100:.0f}%)" for c in cols)
print('\nTable 15 (faithfulness / relevance / completeness)')
FL = f'{R}/results/explainability/final_labels'
for m in ['claude_sonnet_4_6', 'gemma4_31b_or', 'gpt4']:
    print('drugs ', m.ljust(18), fmt(pd.read_csv(f'{FL}/explainability_drugs_{m}_ADJUDICATED.csv'), D))
for m, suf in [('claude_sonnet_4_6', 'RERUN'), ('gemma4_31b_or', 'RERUN'), ('gpt4', 'BLIND')]:
    print('weapon', m.ljust(18), fmt(pd.read_csv(f'{FL}/explainability_weapon_{m}_{suf}.csv'), [c + '_blind' for c in D]))
