# -*- coding: utf-8 -*-
import re, os
from collections import defaultdict

root = r'C:\Users\bellm\source\repos\bellyoshi\ActBa64\src\actba64'
num_re = re.compile(r'(?<![A-Za-z0-9_])(?:&H[0-9A-Fa-f]+|(?<!\.)\d+(?!\.\d))(?![A-Za-z0-9_])')

results = defaultdict(list)
file_counts = defaultdict(int)
const_defs = []
# ASCII-ish values of interest
ascii_vals = {9,10,13,32,34,35,36,38,39,40,41,42,43,44,45,46,47,48,57,58,59,60,61,62,64,65,90,91,92,93,94,95,97,122,126}
ascii_hits = []
size_vals = {63,64,255,256,259,260,511,512,1023,1024,4095,4096,32767,32768}
size_hits = defaultdict(list)
abi_vals = {8,16,24,32,40,48,56,64,72,80}
abi_hits = defaultdict(list)

def strip_comment_and_strings(raw):
    in_str = False
    out = []
    j = 0
    while j < len(raw):
        c = raw[j]
        if c == '"':
            in_str = not in_str
            out.append(' ')
        elif in_str:
            out.append(' ')
        elif c == "'" and not in_str:
            break
        else:
            out.append(c)
        j += 1
    return ''.join(out)

for dirpath, dirnames, filenames in os.walk(root):
    parts = dirpath.split(os.sep)
    if 'test' in parts or 'samples' in parts:
        continue
    for fn in filenames:
        if not fn.endswith('.abp'):
            continue
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, root)
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            raw = line.rstrip('\n')
            code2 = strip_comment_and_strings(raw)
            is_const = bool(re.match(r'\s*Const\s+', code2, re.I))
            for m in num_re.finditer(code2):
                tok = m.group(0)
                if tok.upper().startswith('&H'):
                    try:
                        val = int(tok[2:], 16)
                    except Exception:
                        continue
                    key = tok.upper()
                else:
                    val = int(tok)
                    key = str(val)
                if val in (0, 1, 2):
                    continue
                if is_const:
                    const_defs.append((rel, i, raw.strip()[:120], key, val))
                    continue
                results[key].append((rel, i, raw.strip()[:140], val))
                file_counts[rel] += 1
                if val in ascii_vals or -val in ascii_vals:
                    ascii_hits.append((rel, i, val, raw.strip()[:120]))
                if abs(val) in size_vals:
                    size_hits[abs(val)].append((rel, i, raw.strip()[:120]))
                if abs(val) in abi_vals:
                    # filter somewhat: stack/offset patterns
                    low = raw.lower()
                    if any(x in low for x in ['rsp', 'rbp', 'store_rsp', 'load_rsp', 'load_local',
                                              'store_local', 'lea_local', 'enter', 'sub_rsp',
                                              'add_rsp', 'shadow', 'callbytes', 'align',
                                              'offs[', 'off =', '* 8', '*8', '+ 8', '+8',
                                              'pi *', 'pi*', 'nbytes', 'frame']):
                        abi_hits[abs(val)].append((rel, i, raw.strip()[:120]))

print('=== TOP VALUES BY OCCURRENCE (excl Const defs, excl 0/1/2) ===')
by_freq = sorted(results.items(), key=lambda x: -len(x[1]))
for key, hits in by_freq[:80]:
    print(f'{key}: {len(hits)} hits')

print()
print('=== FILES WITH MOST MAGIC NUMBERS ===')
for f, c in sorted(file_counts.items(), key=lambda x: -x[1])[:50]:
    print(f'{c:4d}  {f}')

print()
print('=== ASCII-LIKE LITERALS (raw digits matching CH_* values) ===')
# group by value
by_a = defaultdict(list)
for h in ascii_hits:
    by_a[h[2]].append(h)
for v in sorted(by_a.keys(), key=lambda x: (abs(x), x)):
    hits = by_a[v]
    print(f'--- {v} ({len(hits)} hits) ---')
    for rel, i, val, txt in hits[:12]:
        print(f'  {rel}:{i}: {txt}')
    if len(hits) > 12:
        print(f'  ... +{len(hits)-12} more')

print()
print('=== SIZE CONST CANDIDATES ===')
for v in sorted(size_hits.keys()):
    hits = size_hits[v]
    print(f'--- {v} ({len(hits)} hits) ---')
    for rel, i, txt in hits[:15]:
        print(f'  {rel}:{i}: {txt}')
    if len(hits) > 15:
        print(f'  ... +{len(hits)-15} more')

print()
print('=== ABI-ISH OFFSET HITS ===')
for v in sorted(abi_hits.keys()):
    hits = abi_hits[v]
    print(f'--- {v} ({len(hits)} hits) ---')
    for rel, i, txt in hits[:20]:
        print(f'  {rel}:{i}: {txt}')
    if len(hits) > 20:
        print(f'  ... +{len(hits)-20} more')

print()
print('=== ALL CONST DEFS (non-test) ===')
for rel, i, txt, key, val in const_defs:
    print(f'{rel}:{i}: {txt}')

print()
print('TOTAL magic hits:', sum(len(v) for v in results.values()))
print('TOTAL const defs:', len(const_defs))
