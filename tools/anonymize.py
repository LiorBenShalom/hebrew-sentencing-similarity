#!/usr/bin/env python3
"""Replace annotator first names with anonymous codes and strip local user paths.
Runs in place on the built repository folder. Idempotent."""
import os, re, sys

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
NAMES = {  # Hebrew and Latin spellings -> code
    'ליאור': 'A1', 'Lior': 'A1',
    'איתי': 'A2', 'Itay': 'A2',
    'גיא': 'A3', 'Guy': 'A3',
    'מור': 'A4', 'Mor': 'A4',
    'טל': 'A5', 'Tal': 'A5',
    'חן': 'A6', 'Chen': 'A6',
    'רותם': 'A7', 'Rotem': 'A7',
}
TEXT_EXT = ('.csv', '.json', '.py', '.md', '.txt', '.sh')
SCOPE = ['data/annotation', 'scripts', 'results', 'data/range_corpus/master_inventory.csv', 'docs']
PATH_RE = re.compile(r'/Users/[A-Za-z0-9_.-]+(/Library/CloudStorage/OneDrive-[^/\s"\',]+)?(/Thesis!!!)?')

# Hebrew names: match only as whole tokens (surrounded by non-letters). Latin: word boundary.
HEB = {k: v for k, v in NAMES.items() if re.search(r'[֐-׿]', k)}
LAT = {k: v for k, v in NAMES.items() if k not in HEB}
heb_re = re.compile(r'(?<![֐-׿])(' + '|'.join(map(re.escape, HEB)) + r')(?![֐-׿])')
lat_re = re.compile(r'\b(' + '|'.join(map(re.escape, LAT)) + r')\b')

def fix(text, names=True):
    t = PATH_RE.sub('<WORKSPACE>', text)
    if names:
        t = heb_re.sub(lambda m: HEB[m.group(1)], t)
        t = lat_re.sub(lambda m: LAT[m.group(1)], t)
    return t

changed = 0
for scope in SCOPE:
    p = os.path.join(REPO, scope)
    files = [p] if os.path.isfile(p) else [os.path.join(r, f) for r, _, fs in os.walk(p) for f in fs]
    for f in files:
        if not f.endswith(TEXT_EXT): continue
        try:
            s = open(f, encoding='utf-8').read()
        except UnicodeDecodeError:
            continue
        # names only inside annotation data and its scripts; paths everywhere
        names = scope.startswith('data/annotation') or '/annotation' in f
        t = fix(s, names)
        if t != s:
            open(f, 'w', encoding='utf-8').write(t); changed += 1
print('files changed:', changed)
