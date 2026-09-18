import os, re
from collections import Counter

root = os.path.dirname(os.path.abspath(__file__))
pat = re.compile(r'^(Function|Sub)\s+(\w+)', re.I)
end_pat = re.compile(r'^End\s+(Function|Sub)\b', re.I)

pj = os.path.join(root, 'actba64.pj')
compiler_files = set()
if os.path.isfile(pj):
    in_src = False
    with open(pj, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            t = line.strip()
            if t.upper() == '#SOURCE':
                in_src = True
                continue
            if in_src:
                if t.startswith('#'):
                    break
                if t and not t.startswith("'"):
                    compiler_files.add(t)

files = sorted(fn for fn in os.listdir(root) if fn.endswith('.abp') and os.path.isfile(os.path.join(root, fn)))
rows = []
for fn in files:
    path = os.path.join(root, fn)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        m = pat.match(lines[i].strip())
        if m:
            name = m.group(2)
            start = i
            i += 1
            phys = 0
            body = 0
            while i < len(lines):
                raw = lines[i].rstrip('\n')
                t = raw.strip()
                if end_pat.match(t):
                    break
                phys += 1
                if t and not t.startswith("'"):
                    body += 1
                i += 1
            total = i - start + 1
            rows.append((phys, body, total, fn, name, start + 1, fn in compiler_files))
        i += 1

print('=== compiler files, physical body > 100 ===')
over = [r for r in rows if r[0] > 100 and r[6]]
for r in sorted(over, reverse=True):
    print('  %5d phys  %5d code  %s:%d  %s' % (r[0], r[1], r[3], r[5], r[4]))
print('count:', len(over))
print()
print('=== all abp, physical body > 100, not in pj ===')
over2 = [r for r in rows if r[0] > 100 and not r[6]]
for r in sorted(over2, reverse=True):
    print('  %5d phys  %5d code  %s:%d  %s' % (r[0], r[1], r[3], r[5], r[4]))
print('count:', len(over2))
