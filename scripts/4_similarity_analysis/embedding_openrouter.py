"""Text-embedding baseline via OpenRouter (same pipeline as embedding_baseline.py).

  1. Load pair facts (indicment_facts_1/2) from data/{drugs,wep}/facts.csv
  2. Encode each unique verdict text once (cached under results/.../emb_cache)
  3. Pair score = cosine(emb_1, emb_2) mapped to [0, 100]
  4. Save per-pair scores + print Spearman rho vs the expert 1/2/3 labels

Key: OPENROUTER_API_KEY from new_try/experiments/.env (the one the LLM runs used).

Usage (from new_try/experiments):
  python3 src/analysis/embedding_openrouter.py --models qwen/qwen3-embedding-8b
"""
from __future__ import annotations
import argparse, os, re, time
from pathlib import Path
import numpy as np, pandas as pd, requests
from scipy.stats import spearmanr

EXP = Path(__file__).resolve().parents[2]            # new_try/experiments
OUT = EXP / "results" / "1_similarity" / "baselines"
PREDS = OUT / "emb_preds"; CACHE = OUT / "emb_cache"
PREDS.mkdir(parents=True, exist_ok=True); CACHE.mkdir(parents=True, exist_ok=True)
DOMAINS = {"drugs": EXP / "data" / "drugs" / "facts.csv",
           "weapon": EXP / "data" / "wep" / "facts.csv"}
URL = "https://openrouter.ai/api/v1/embeddings"


def load_key() -> str:
    for line in (EXP / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*OPENROUTER_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line, re.I)
        if m:
            return m.group(1)
    raise SystemExit("OPENROUTER_API_KEY not found in experiments/.env")


def embed(texts: list[str], model: str, key: str, batch: int = 16) -> np.ndarray:
    hdr = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
           "HTTP-Referer": "https://github.com/LiorBenShalom/hebrew-sentencing-similarity",
           "X-Title": "hebrew-sentencing-similarity embedding baseline"}
    vecs = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        for attempt in range(6):
            r = requests.post(URL, headers=hdr, json={"model": model, "input": chunk,
                                                       "encoding_format": "float"}, timeout=120)
            if r.status_code == 200:
                data = sorted(r.json()["data"], key=lambda d: d["index"])
                vecs.extend(np.asarray(d["embedding"], dtype=np.float32) for d in data)
                break
            wait = 2 ** attempt
            print(f"    HTTP {r.status_code}: {r.text[:200]} -> retry in {wait}s")
            time.sleep(wait)
        else:
            raise SystemExit("OpenRouter kept failing")
        print(f"    {min(i + batch, len(texts))}/{len(texts)} encoded", flush=True)
    arr = np.vstack(vecs)
    return arr / np.clip(np.linalg.norm(arr, axis=1, keepdims=True), 1e-9, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen/qwen3-embedding-8b"])
    args = ap.parse_args()
    key = load_key()
    rows = []
    for model in args.models:
        tag = model.split("/")[-1]
        print(f"\n=== {model} ===")
        for dom, path in DOMAINS.items():
            df = pd.read_csv(path)
            id2txt: dict[str, str] = {}
            for _, r in df.iterrows():
                id2txt.setdefault(r["verdict_1"], str(r["indicment_facts_1"]))
                id2txt.setdefault(r["verdict_2"], str(r["indicment_facts_2"]))
            embs: dict[str, np.ndarray] = {}
            todo = []
            for vid, txt in id2txt.items():
                cp = CACHE / f"{tag}_{vid}.npy"
                if cp.exists():
                    embs[vid] = np.load(cp)
                else:
                    todo.append((vid, txt))
            print(f"  {dom}: {len(df)} pairs, {len(id2txt)} verdicts ({len(todo)} to encode)")
            if todo:
                vecs = embed([t for _, t in todo], model, key)
                for (vid, _), v in zip(todo, vecs):
                    np.save(CACHE / f"{tag}_{vid}.npy", v); embs[vid] = v
            cos = np.array([float(embs[a] @ embs[b]) for a, b in zip(df.verdict_1, df.verdict_2)])
            score = (cos.clip(-1, 1) + 1) * 50
            out = df[["verdict_1", "verdict_2", "similarity_scale", "similarity_binary_0",
                      "similarity_binary_1"]].copy()
            out["score"] = score
            out.to_csv(PREDS / f"embedding_{tag}_{dom}_preds.csv", index=False)
            rho = spearmanr(score, df.similarity_scale).correlation
            print(f"  {dom}: Spearman rho = {rho:.3f}   (cosine range {cos.min():.3f}-{cos.max():.3f})")
            rows.append(dict(domain=dom, model=model, n=len(df), spearman=rho))
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "emb_openrouter_spearman.csv", index=False)
    print("\n" + res.to_string(index=False))


if __name__ == "__main__":
    main()
