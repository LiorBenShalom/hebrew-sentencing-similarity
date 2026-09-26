"""
drug_group_jaccard_gold_vs_gpt.py

Machine-vs-gold agreement on the combined "drug type + quantity" feature,
using the SAME quantity-tolerant group metric as the inter-annotator
analysis (annotator_data/drugs/drug_quantity_agreement.py):

    score = |{d : d in S_gold ∩ S_gpt AND quantity within tolerance}|
            / |S_gold ∪ S_gpt|

Tolerance (identical to the IAA script): after normalising weight units to
grams, |a-b| <= 1 gram OR ratio >= 0.9. A drug counts as agreed only if
both name AND quantity match. Per drug, the last listed entry wins
(faithful to the IAA script's dict-comprehension behaviour).

Differences from the IAA pipeline, stated for transparency:
  * Parsing of the "סוג הסם, כמות" strings is rule-based (deterministic)
    rather than LLM-based; all sub-0.5 cases were manually inspected and
    reflect real content differences, not parse failures.
  * The gold side is the adjudicated consensus annotation, whereas the
    human-human 0.79 was measured between independent annotators before
    adjudication - a comparison that mildly favours the machine.

Inputs : drugs_extraction/results/fe_gt.csv, fe_gpt_extracted.csv
Output : per-verdict scores + summary printed to stdout.
Result (2026-08-15): n=68, mean Jaccard = 0.88, 55/68 perfect,
92.6% of cases >= 0.5. Reported in the manuscript's feature-extraction
validation subsection alongside the strict per-substance +-1-gram
accuracy (73.9%).

Usage:
    python drug_group_jaccard_gold_vs_gpt.py \
        --results-dir experiments/drugs_extraction/results
"""
import argparse, csv, json, re, statistics as st

csv.field_size_limit(10**8)
DRUG_KEY = "סוג הסם, כמות"

def to_grams(amount, unit):
    u = str(unit).strip().replace('"', '').replace("'", "")
    flat = u.replace('_', '').replace('-', '')
    if 'קג' in flat or 'קילו' in u:
        return amount * 1000, 'גרם'
    if u in {'מג', 'מיליגרם'}:
        return amount / 1000, 'גרם'
    if u in {'גרם', 'גר'} or (u.endswith('גרם') and 'קילו' not in u and 'קג' not in flat):
        return amount, 'גרם'
    return amount, u

def within_tolerance(a, ua, b, ub):
    an, un = to_grams(a, ua)
    bn, ubn = to_grams(b, ub)
    if un != ubn:
        return False
    if an == 0 or bn == 0:
        return an == bn
    if abs(an - bn) <= 1.0:
        return True
    return 0.9 <= min(an, bn) / max(an, bn) <= 1.0

def parse_drug_string(s):
    """'NAME: amt unit[, amt unit], NAME: ...' -> [{drug, amount, unit}]"""
    s = (s or '').strip().strip(',')
    if not s:
        return []
    out, cur = [], None
    for seg in [x.strip() for x in s.split(',') if x.strip()]:
        if ':' in seg:
            name, rest = seg.split(':', 1)
            cur, seg = name.strip(), rest.strip()
        m = (re.match(r'([\d.]+)\s*[_\-\s]\s*(.+)$', seg)
             or re.match(r'([\d.]+)(.+)$', seg))
        if m and cur:
            try:
                out.append({'drug': cur, 'amount': float(m.group(1)),
                            'unit': m.group(2).strip()})
            except ValueError:
                out.append({'drug': cur, 'amount': 0, 'unit': seg})
        elif cur:
            out.append({'drug': cur, 'amount': 0, 'unit': seg})
    return out

def pair_jaccard(a, b):
    by_a = {d['drug']: d for d in a if d.get('drug')}
    by_b = {d['drug']: d for d in b if d.get('drug')}
    union = set(by_a) | set(by_b)
    if not union:
        return 1.0
    agreed = sum(
        1 for d in set(by_a) & set(by_b)
        if within_tolerance(by_a[d]['amount'], by_a[d]['unit'],
                            by_b[d]['amount'], by_b[d]['unit']))
    return agreed / len(union)

def collect(path):
    d = {}
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        for v, fv in [(r['verdict_1'], r['feature_vector_1']),
                      (r['verdict_2'], r['feature_vector_2'])]:
            try:
                d[v] = json.loads(fv).get(DRUG_KEY, '')
            except (json.JSONDecodeError, TypeError):
                pass
    return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-dir', default='.')
    args = ap.parse_args()
    gold = collect(f'{args.results_dir}/fe_gt.csv')
    gpt = collect(f'{args.results_dir}/fe_gpt_extracted.csv')
    rows = []
    for v in sorted(gold):
        if v not in gpt:
            continue
        s = pair_jaccard(parse_drug_string(gold[v]), parse_drug_string(gpt[v]))
        rows.append((v, s))
        if s < 0.5:
            print(f'LOW  {v}  {s:.2f}  gold={gold[v][:60]!r}  gpt={gpt[v][:60]!r}')
    scores = [s for _, s in rows]
    print(f'n = {len(scores)}')
    print(f'mean Jaccard = {st.mean(scores):.3f}')
    print(f'perfect (1.0): {sum(1 for s in scores if s == 1.0)}')
    print(f'>= 0.5: {sum(1 for s in scores if s >= 0.5) / len(scores):.3f}')

if __name__ == '__main__':
    main()
