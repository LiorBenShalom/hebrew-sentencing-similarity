#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare a reviewer's labels against ours.

Mode A: reads output/*.json with {"labels":[...]} and computes agreement vs data_current/.
Mode B: reads output/*.json with {"flags":[...]} and just summarizes proposed changes.

Usage:  python3 scripts/agreement.py
"""
import json, glob, os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUR = os.path.join(ROOT, 'data_current')
OUT = os.path.join(ROOT, 'output')
DIMS = ['נאמנות_עובדתית', 'רלוונטיות_משפטית', 'שלמות']


def cohen_kappa(a, b):
    """Unweighted Cohen's kappa, no sklearn dependency."""
    cats = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return float('nan')
    obs = sum(1 for x, y in zip(a, b) if x == y) / n
    exp = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return float('nan') if exp == 1 else (obs - exp) / (1 - exp)


def main():
    files = sorted(glob.glob(os.path.join(OUT, '*.json')))
    if not files:
        sys.exit('No JSON files in output/ — run the reviewer first.')

    blind, flags, seen_files = {}, [], set()
    for f in files:
        d = json.load(open(f, encoding='utf-8'))
        name = d.get('file') or os.path.basename(f)
        seen_files.add(name)
        for lab in d.get('labels', []):
            blind[(name, int(lab['row_index']))] = lab
        for fl in d.get('flags', []):
            flags.append(dict(fl, file=name))

    if flags and not blind:
        print(f'MODE B — {len(flags)} proposed changes\n')
        df = pd.DataFrame(flags)
        print(df.groupby(['file', 'dimension']).size().to_string())
        df.to_csv(os.path.join(OUT, 'proposed_changes.csv'), index=False, encoding='utf-8-sig')
        print('\nwrote output/proposed_changes.csv')
        return

    print('MODE A — agreement vs data_current/\n')
    rows, missing = [], []
    for name in sorted(seen_files):
        p = os.path.join(CUR, name)
        if not os.path.exists(p):
            print(f'  !! no matching file in data_current/: {name}')
            continue
        cur = pd.read_csv(p)
        for i in range(len(cur)):
            lab = blind.get((name, i))
            if lab is None:
                missing.append((name, i))
                continue
            if int(lab['pair_id']) != int(cur.iloc[i]['pair_id']):
                print(f'  !! pair_id mismatch {name} row {i}')
            for d in DIMS:
                rows.append({'file': name, 'row_index': i, 'pair_id': int(cur.iloc[i]['pair_id']),
                             'dimension': d, 'ours': int(cur.iloc[i][d]), 'theirs': int(lab[d]),
                             'reason': lab.get('reason', '')})
    if missing:
        print(f'  !! {len(missing)} rows have no label from the reviewer (first 5: {missing[:5]})\n')

    D = pd.DataFrame(rows)
    if D.empty:
        sys.exit('No comparable labels found.')
    D['agree'] = D.ours == D.theirs

    print(f'{"dimension":22s} {"n":>5s} {"exact":>7s} {"±1":>7s} {"kappa":>7s}   ours→theirs mean')
    for d in DIMS:
        g = D[D.dimension == d]
        k = cohen_kappa(list(g.ours), list(g.theirs))
        within1 = ((g.ours - g.theirs).abs() <= 1).mean()
        print(f'{d:22s} {len(g):5d} {g.agree.mean():6.1%} {within1:6.1%} {k:7.3f}   '
              f'{g.ours.mean():.2f} → {g.theirs.mean():.2f}')

    print(f'\n{"OVERALL":22s} {len(D):5d} {D.agree.mean():6.1%}')

    print('\nper file (exact agreement):')
    print(D.groupby(['file', 'dimension']).agree.mean().unstack().to_string(float_format=lambda x: f'{x:.1%}'))

    dis = D[~D.agree].sort_values(['file', 'row_index'])
    dis.to_csv(os.path.join(OUT, 'disagreements.csv'), index=False, encoding='utf-8-sig')
    print(f'\n{len(dis)} disagreements → output/disagreements.csv')
    print('\ndirection of disagreement (theirs - ours):')
    print((dis.theirs - dis.ours).value_counts().sort_index().to_string())


if __name__ == '__main__':
    main()
