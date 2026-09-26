#!/usr/bin/env python3
"""Redact person names copied by the LLM extractors into free-text fields of the
LLM-enriched representations (GPT-Free, GPT-Law, Hybrid-Manual, Hybrid-Full).
Any JSON key that is the word 'שם' (name) or starts with it ('שם הנאשם', 'שם_השוטר', ...)
gets the value '[REDACTED]'. Nested dicts/lists are walked. Writes provenance/redaction_log.csv.
Run from the repository root; idempotent."""
import csv, glob, json, os, re, sys

R = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
KEY = re.compile(r'(^|[\s_])שם($|[\s_])')
FILES = [f for d in ('drugs', 'weapon') for f in glob.glob(f'{R}/data/representations/{d}/*.csv')
         if not os.path.basename(f).startswith(('facts', 'fe_'))]
FILES += glob.glob(f'{R}/results/explainability/**/*.csv', recursive=True)
FILES += [f for f in glob.glob(f'{R}/results/similarity/llm_predictions/*/*_preds.csv')
          if re.search(r'(with_gpt_features|with_gpt_law_features|hybrid)', os.path.basename(f))]
JSON_COLS = ('feature_vector_1', 'feature_vector_2', 'features', 'feature_vector')

def walk(o, hits):
    if isinstance(o, dict):
        for k, v in list(o.items()):
            if isinstance(k, str) and KEY.search(k) and isinstance(v, (str, int, float)) and v not in ('', None, '[REDACTED]'):
                o[k] = '[REDACTED]'; hits[0] += 1
            else:
                walk(v, hits)
    elif isinstance(o, list):
        for v in o: walk(v, hits)

log = []
for f in FILES:
    with open(f, encoding='utf-8', newline='') as fh:
        rows = list(csv.DictReader(fh)); cols = list(rows[0].keys()) if rows else []
    hits = [0]
    for r in rows:
        for c in cols:
            if c in JSON_COLS or (c.startswith('feature') and r[c].startswith('{')):
                try: o = json.loads(r[c])
                except Exception: continue
                walk(o, hits)
                r[c] = json.dumps(o, ensure_ascii=False)
    with open(f, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    log.append([os.path.relpath(f, R), hits[0]])
    print(f'{os.path.relpath(f, R)}: {hits[0]} values redacted')
os.makedirs(f'{R}/provenance', exist_ok=True)
with open(f'{R}/provenance/redaction_log.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['file', 'values_redacted']); w.writerows(log)
