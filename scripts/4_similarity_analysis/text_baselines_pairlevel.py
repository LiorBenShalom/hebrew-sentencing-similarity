"""No-LLM text baselines for the similarity grid (Appendix B.6, Table B5) and
pair-level significance of every LLM cell against the strongest embedder.

Run from the repository root:
    python scripts/4_similarity_analysis/text_baselines_pairlevel.py

Inputs
  data/representations/{drugs,weapon}/facts.csv            raw verdict-facts text + expert labels
  results/similarity/baselines/emb_preds/embedding_*_preds.csv
                                                          per-pair cosine scores of the five text
                                                          embedders (embedding_baseline.py and
                                                          embedding_openrouter.py)
  results/similarity/llm_predictions/{drugs,weapon}/*_preds.csv
                                                          per-pair LLM scores (7 reps x 13 LLMs)
  results/similarity/cells_n13.csv                         cell list (which files form the panel)

Outputs (results/similarity/baselines/)
  bm25_{drugs,weapon}_preds.csv          symmetric BM25 score per gold pair
  text_baselines_spearman.csv            Table B5: Spearman rho of BM25 + 5 embedders, with LLM means
  vs_best_embedding_cells.csv            one row per (domain, rep, LLM): rho_llm, rho_emb, delta,
                                         Steiger z/p (one-sided, LLM > embedder), pair-bootstrap CI,
                                         BH-FDR p within domain
  vs_best_embedding_summary.csv          per (domain, rep): how many of the 13 LLMs exceed / are
                                         significantly above the best embedder; panel-level tests

Statistics
  * BM25: Okapi BM25 (k1=1.5, b=0.75) on a simple Hebrew tokeniser, scored symmetrically
    (mean of BM25(q=a, d=b) and BM25(q=b, d=a)) over the corpus of unique verdicts in the gold set.
  * Steiger (1980) test for two dependent correlations sharing the gold labels, applied to
    Spearman correlations via the rank transform; one-sided H1: rho_LLM > rho_embedder.
  * Pair bootstrap: 5,000 resamples of the gold pairs, percentile CI of (rho_LLM - rho_embedder).
  * Panel-level: one-sample Wilcoxon of the 13 LLM rhos against the embedder's rho (what the
    earlier significance_vs_text_embedding.py did) and a one-sided binomial on the sign count.
"""
from __future__ import annotations
import glob, math, os, re
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results" / "similarity" / "baselines"
PREDS = BASE / "emb_preds"
LLM = ROOT / "results" / "similarity" / "llm_predictions"
FACTS = {"drugs": ROOT / "data" / "representations" / "drugs" / "facts.csv",
         "weapon": ROOT / "data" / "representations" / "weapon" / "facts.csv"}
EMBEDDERS = {"openai": "OpenAI text-embedding-3-large", "e5": "mE5-large-instruct", "bge": "BGE-M3",
             "qwen3-embedding-8b": "Qwen3-Embedding-8B", "gemini": "Gemini-embedding-001"}
REP = {"fe": "Manual", "fe_gpt_schema_v2": "GPT-Schema", "hybrid": "Hybrid-Manual",
       "hybrid_full_gpt": "Hybrid-Full", "with_gpt_features": "GPT-Free",
       "with_gpt_law_features": "GPT-Law", "with_indicment_facts": "Raw-Facts"}
REPS = ["Manual", "GPT-Schema", "Hybrid-Manual", "Hybrid-Full", "Raw-Facts", "GPT-Free", "GPT-Law"]
DOMS = ["drugs", "weapon"]
B = 5000
rng = np.random.default_rng(0)


# ---------------- BM25 ----------------
def tok(t: str) -> list[str]:
    return re.findall(r"[֐-׿]+|\d+", str(t))


def bm25_pairs(docs: dict[str, str], pairs, k1=1.5, b=0.75) -> np.ndarray:
    toks = {i: tok(t) for i, t in docs.items()}
    N = len(toks); avg = np.mean([len(v) for v in toks.values()])
    df = Counter()
    for v in toks.values():
        df.update(set(v))
    idf = {w: math.log(1 + (N - n + 0.5) / (n + 0.5)) for w, n in df.items()}
    tf = {i: Counter(v) for i, v in toks.items()}

    def s(q, d):
        td, L = tf[d], len(toks[d])
        return sum(idf[w] * td[w] * (k1 + 1) / (td[w] + k1 * (1 - b + b * L / avg)) for w in tf[q] if w in td)
    return np.array([0.5 * (s(a, c) + s(c, a)) for a, c in pairs])


# ---------------- helpers ----------------
def steiger_z(r12, r13, r23, n):
    """Steiger (1980) z for H0: rho(1,2) = rho(1,3), variable 1 shared."""
    z12, z13 = np.arctanh(r12), np.arctanh(r13)
    rm2 = (r12 ** 2 + r13 ** 2) / 2
    f = min((1 - r23) / (2 * (1 - rm2)), 1.0)
    h = (1 - f * rm2) / (1 - rm2)
    return (z12 - z13) * math.sqrt((n - 3) / (2 * (1 - r23) * h))


def boot_delta(g, s, e):
    idx = rng.integers(0, len(g), (B, len(g)))
    def sp(X, Y):
        rx = np.apply_along_axis(stats.rankdata, 1, X); ry = np.apply_along_axis(stats.rankdata, 1, Y)
        rx -= rx.mean(1, keepdims=True); ry -= ry.mean(1, keepdims=True)
        return (rx * ry).sum(1) / np.sqrt((rx ** 2).sum(1) * (ry ** 2).sum(1))
    d = sp(s[idx], g[idx]) - sp(e[idx], g[idx])
    return np.percentile(d, 2.5), np.percentile(d, 97.5), float((d <= 0).mean())


def load_llm(dom, cells):
    out = {}
    for f in sorted(glob.glob(str(LLM / dom / "*_preds.csv"))):
        m = re.match(r"similarity_database_(.+)_v6score_(.+)_binary_0_preds\.csv", os.path.basename(f))
        if not m or m.group(1) not in REP:
            continue
        rep, model = REP[m.group(1)], m.group(2)
        if not ((cells.domain == dom) & (cells.rep == rep) & (cells.model == model)).any():
            continue
        df = pd.read_csv(f, encoding="utf-8-sig")
        df.columns = [c.replace("﻿", "").strip('"') for c in df.columns]
        if "status" in df:
            df = df[df.status == "ok"]
        out[(rep, model)] = df[["verdict_1", "verdict_2", "similarity_scale", "score"]].dropna()
    return out


def main():
    cells = pd.read_csv(ROOT / "results" / "similarity" / "cells_n13.csv")
    table, cell_rows, summ = [], [], []
    for dom in DOMS:
        facts = pd.read_csv(FACTS[dom])
        gold = facts[["verdict_1", "verdict_2", "similarity_scale"]].copy()
        # BM25
        docs = {}
        for _, r in facts.iterrows():
            docs.setdefault(r.verdict_1, r.indicment_facts_1); docs.setdefault(r.verdict_2, r.indicment_facts_2)
        bm = gold.copy(); bm["score"] = bm25_pairs(docs, list(zip(facts.verdict_1, facts.verdict_2)))
        bm.to_csv(BASE / f"bm25_{dom}_preds.csv", index=False)
        table.append(dict(domain=dom, score="BM25", spearman=stats.spearmanr(bm.score, bm.similarity_scale).correlation))
        # embedders
        emb = {}
        for key, name in EMBEDDERS.items():
            e = pd.read_csv(PREDS / f"embedding_{key}_{dom}_preds.csv")
            emb[key] = e
            table.append(dict(domain=dom, score=name, spearman=stats.spearmanr(e.score, e.similarity_scale).correlation))
        best_key = max(EMBEDDERS, key=lambda k: stats.spearmanr(emb[k].score, emb[k].similarity_scale).correlation)
        best = emb[best_key].set_index(["verdict_1", "verdict_2"])["score"].rename("emb")
        # LLM cells vs best embedder, pair level
        llm = load_llm(dom, cells)
        for rep in ["Raw-Facts", "Manual"]:
            table.append(dict(domain=dom, score=f"LLM on {rep} (mean of 13)",
                              spearman=np.mean([stats.spearmanr(d.score, d.similarity_scale).correlation
                                                for (r, _), d in llm.items() if r == rep])))
        rows = []
        for (rep, model), d in llm.items():
            j = d.set_index(["verdict_1", "verdict_2"]).join(best, how="inner")
            g, s, e = j.similarity_scale.values.astype(float), j.score.values.astype(float), j.emb.values.astype(float)
            r_l = stats.spearmanr(s, g).correlation; r_e = stats.spearmanr(e, g).correlation
            z = steiger_z(r_l, r_e, stats.spearmanr(s, e).correlation, len(j))
            lo, hi, pb = boot_delta(g, s, e)
            rows.append(dict(domain=dom, rep=rep, model=model, n=len(j), best_embedder=EMBEDDERS[best_key],
                             rho_llm=r_l, rho_emb=r_e, delta=r_l - r_e, steiger_z=z,
                             p_steiger=1 - stats.norm.cdf(z), boot_lo=lo, boot_hi=hi, p_boot=pb))
        pc = pd.DataFrame(rows)
        pc["p_steiger_fdr"] = multipletests(pc.p_steiger, method="fdr_bh")[1]
        cell_rows.append(pc)
        for rep in REPS:
            x = pc[pc.rep == rep]
            k = int((x.delta > 0).sum())
            summ.append(dict(domain=dom, rep=rep, n_llms=len(x), llm_mean=x.rho_llm.mean(), rho_emb=x.rho_emb.iloc[0],
                             delta_mean=x.delta.mean(), delta_min=x.delta.min(), delta_max=x.delta.max(),
                             llms_above=k, p_binomial=stats.binomtest(k, len(x), 0.5, alternative="greater").pvalue,
                             p_wilcoxon_vs_const=stats.wilcoxon(x.delta, alternative="greater").pvalue,
                             llms_sig_steiger_fdr=int((x.p_steiger_fdr < 0.05).sum()),
                             llms_boot_ci_excl0=int((x.boot_lo > 0).sum())))
        print(f"{dom}: best embedder = {EMBEDDERS[best_key]}")
    t = pd.DataFrame(table).pivot(index="score", columns="domain", values="spearman").round(3)
    t.to_csv(BASE / "text_baselines_spearman.csv")
    pd.concat(cell_rows).to_csv(BASE / "vs_best_embedding_cells.csv", index=False)
    s = pd.DataFrame(summ); s.to_csv(BASE / "vs_best_embedding_summary.csv", index=False)
    pd.set_option("display.width", 200)
    print(t.to_string()); print(s.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
