#!/usr/bin/env python3
"""Recompute every cell of results/similarity/cells_n13.csv (7 representations x 13 LLMs x 2 domains)
from the raw per-pair LLM outputs in results/similarity/llm_predictions/, using the same definitions as
scripts/4_similarity_analysis/paper_results_qwk.py: QWK with oracle thresholds (midpoints between
unique scores), QWK with 10-fold stratified CV thresholds (seed 42), Spearman rho, ordinal C-index.
Prints per-cell differences and a summary. Run from the repository root; takes a few minutes."""
import glob, os, re, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.model_selection import StratifiedKFold

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = np.array([[((i - j) ** 2) / 4 for j in range(3)] for i in range(3)])

def qwk(t, p):
    O = np.bincount((t - 1) * 3 + (p - 1), minlength=9).reshape(3, 3).astype(float)
    E = np.outer(np.bincount(t - 1, minlength=3), np.bincount(p - 1, minlength=3)) / len(t)
    d = (W * E).sum()
    return 1 - (W * O).sum() / d if d > 0 else 0.0

def best_thresholds(sc, gt):
    u = np.unique(sc)
    if len(u) < 3: return 0.0, 0.0, 50.0
    mids = (u[:-1] + u[1:]) / 2
    best = (-1.0, mids[0], mids[-1])
    for i, t1 in enumerate(mids):
        for t2 in mids[i + 1:]:
            p = np.where(sc < t1, 1, np.where(sc < t2, 2, 3))
            if len(np.unique(p)) < 2: continue
            q = qwk(gt, p)
            if q > best[0]: best = (q, t1, t2)
    return best

def cv_qwk(sc, gt, k=10, seed=42):
    if len(np.unique(gt)) < 2 or min(np.bincount(gt - 1)) < k: return np.nan
    preds = np.zeros(len(gt), int)
    for tr, te in StratifiedKFold(k, shuffle=True, random_state=seed).split(sc, gt):
        _, t1, t2 = best_thresholds(sc[tr], gt[tr])
        preds[te] = np.where(sc[te] < t1, 1, np.where(sc[te] < t2, 2, 3))
    return qwk(gt, preds)

def c_index(gt, sc):
    g1, g2 = np.meshgrid(gt, gt, indexing='ij'); s1, s2 = np.meshgrid(sc, sc, indexing='ij')
    m = np.triu(np.ones_like(g1, bool), 1) & (g1 != g2)
    hi_s = np.where(g1 > g2, s1, s2); lo_s = np.where(g1 > g2, s2, s1)
    c = ((hi_s > lo_s) & m).sum(); d = ((hi_s < lo_s) & m).sum(); t = ((hi_s == lo_s) & m).sum()
    return (c + 0.5 * t) / (c + d + t)

REP = {'fe': 'Manual', 'fe_gpt_schema_v2': 'GPT-Schema', 'hybrid': 'Hybrid-Manual', 'hybrid_full_gpt': 'Hybrid-Full',
       'with_gpt_features': 'GPT-Free', 'with_gpt_law_features': 'GPT-Law', 'with_indicment_facts': 'Raw-Facts'}
cells = pd.read_csv(f'{R}/results/similarity/cells_n13.csv').set_index(['domain', 'rep', 'model'])
rows = []
for dom in ['drugs', 'weapon']:
    for f in sorted(glob.glob(f'{R}/results/similarity/llm_predictions/{dom}/*_preds.csv')):
        m = re.match(r'similarity_database_(.+)_v6score_(.+)_binary_0_preds\.csv', os.path.basename(f))
        if not m or m.group(1) not in REP: continue
        rep, model = REP[m.group(1)], m.group(2)
        if (dom, rep, model) not in cells.index: continue
        df = pd.read_csv(f)
        if 'status' in df: df = df[df.status == 'ok']
        gt = df.similarity_scale.astype(int).values; sc = df.score.astype(float).values
        k = ~np.isnan(sc); gt, sc = gt[k], sc[k]
        q, _, _ = best_thresholds(sc, gt)
        rows.append(dict(domain=dom, rep=rep, model=model, n=len(sc), qwk=q, qwk_cv=cv_qwk(sc, gt),
                         spearman=spearmanr(sc, gt).correlation, cindex=c_index(gt, sc)))
        print(f'{dom:6} {rep:14} {model:18} n={len(sc):3} qwk={q:.3f}', flush=True)
new = pd.DataFrame(rows).set_index(['domain', 'rep', 'model'])
print(f'\nrecomputed {len(new)} cells; cells_n13 has {len(cells)}')
for col in ['qwk', 'qwk_cv', 'spearman', 'cindex']:
    d = (new[col] - cells.loc[new.index, col]).abs()
    print(f'{col:9} max |diff| = {d.max():.4f}   cells with |diff| > 0.005: {(d > 0.005).sum()}')
    for idx in d[d > 0.005].index: print('   ', idx, round(new.loc[idx, col], 4), 'vs', round(cells.loc[idx, col], 4))
