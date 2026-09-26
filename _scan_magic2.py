# -*- coding: utf-8 -*-
import re, os
from collections import defaultdict

root = r'C:\Users\bellm\source\repos\bellyoshi\ActBa64\src\actba64'
num_re = re.compile(r'(?<![A-Za-z0-9_])(?:&H[0-9A-Fa-f]+|-?\d+)(?![A-Za-z0-9_.])')

results = defaultdict(list)
file_counts = defaultdict(int)
const_defs = []
ascii_vals = {9,10,13,32,34,35,36,38,39,40,41,42,43,44,45,46,47,48,57,58,59,60,61,62,64,
              65,90,91,92,93,94,95,97,122,126}
# Also common letter ranges used for IsAlpha checks
ascii_extra = {65,90,97,122}  # A Z a z already in ascii_vals
size_vals = {63,64,255,256,259,260,511,512,1023,1024,2047,2048,4095,4096}
dim_re = re.compile(r'Dim\s+\w+\((\d+)\)', re.I)

def strip_code(raw):
    in_str = False
    out = []
    for c in raw:
        if c == '"':
            in_str = not in_str
            out.append(' ')
        elif in_str:
            out.append(' ')
        elif c == "'" and not in_str:
            break
        else:
            out.append(c)
    return ''.join(out)

skip_dirs = {'test', 'samples', 'bin'}

for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in skip_dirs]
    parts = set(dirpath.split(os.sep))
    if parts & skip_dirs:
        continue
    for fn in filenames:
        if not fn.endswith('.abp'):
            continue
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, root).replace('\\', '/')
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            raw = line.rstrip('\n')
            code2 = strip_code(raw)
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
                if val in (0, 1, 2, -1):  # -1 often sentinel; still track but exclude common
                    continue
                if is_const:
                    const_defs.append((rel, i, raw.strip()[:120], key, val))
                    continue
                results[key].append((rel, i, raw.strip()[:140], val))
                file_counts[rel] += 1

# Focused reports
print('=== TOP VALUES (source only, excl test/samples/bin, excl Const, excl 0/1/2/-1) ===')
by_freq = sorted(results.items(), key=lambda x: -len(x[1]))
for key, hits in by_freq[:50]:
    print(f'{key}: {len(hits)}')

print()
print('=== FILES WITH MOST ===')
for f, c in sorted(file_counts.items(), key=lambda x: -x[1])[:40]:
    print(f'{c:4d}  {f}')

# ASCII: only when used as char comparison / assignment looking like char
print()
print('=== ASCII CANDIDATES (char-like context) ===')
char_ctx = re.compile(
    r'(=\s*%d\b|<>\s*%d\b|Or\s+\w+\s*=\s*%d\b|And\s+\w+\s*=\s*%d\b|'
    r'\[\d+\]\s*=\s*%d\b|MOV_EAX_IMM,\s*%d|MOV_ECX,\s*%d|'
    r'ADD_RAX_IMM,\s*-?%d|c\s*=\s*%d|c\s*<>\s*%d)',
    re.I
)
# simpler: look at lines with common patterns
for v in sorted(ascii_vals):
    hits = []
    for key in (str(v), str(-v)):
        for rel, i, txt, val in results.get(key, []):
            t = txt.lower()
            # skip opcode enums / pe offsets / emitbyte hex that happens to equal
            if 'emitbyte' in t or 'emitword' in t or 'putdword' in t or 'putword' in t:
                continue
            if 'op_' in t and 'mov_eax_imm' not in t and 'mov_ecx' not in t and 'add_rax_imm' not in t:
                continue
            if 'const ' in t:
                continue
            # keep if looks like char
            charish = (
                f'= {v}' in txt or f'= {v} ' in txt + ' ' or f'<> {v}' in txt or
                f', {v},' in txt or f', -{v},' in txt or f',{v},' in txt or
                f'[{v}]' in txt or  # unlikely
                f' = {v}' in txt or
                f'Or c = {v}' in txt or f'And c = {v}' in txt or
                f'= {v} Or' in txt or f'= {v} And' in txt or
                f'= {v} Then' in txt or f'<> {v} Then' in txt or
                f'= {v} And' in txt or
                re.search(rf'(^|[^0-9]){v}([^0-9.]|$)', txt) and any(
                    k in t for k in ['ch_', 'char', 'byte', 'src[', 'line[', 'rawcmd', 'crlf',
                                     'name[', 'buf[', 'p[', 'c =', 'c <>', 'mov_eax_imm',
                                     'add_rax_imm', 'isdigit', 'isalpha', 'tolower']
                )
            )
            # broader for known ascii files
            if not charish:
                if any(x in rel for x in ['Lexer', 'Preproc', 'Utils', 'Parser', 'Char', 'Byte',
                                          'AstLowerRt', 'AstLowerStr', 'AstLowerApi']):
                    # still filter noise
                    if abs(val) == v and any(x in t for x in [
                        f'= {v}', f'<> {v}', f', {v},', f', -{v}', f'[{v}]',
                        f' ={v}', f'={v} ', f'or {v}', f'and {v}'
                    ]):
                        charish = True
            if charish or (abs(val) == v and (
                f'= {v}' in txt or f'<> {v}' in txt or f', {v}, 0)' in txt or f', -{v}, 0)' in txt
                or f'[{0}] = {v}' in txt.replace(' ', '')  # rough
            )):
                hits.append((rel, i, txt))
    # dedupe
    seen = set()
    uniq = []
    for h in hits:
        k = (h[0], h[1])
        if k not in seen:
            seen.add(k)
            uniq.append(h)
    if uniq:
        print(f'--- {v} ({len(uniq)}) ---')
        for rel, i, txt in uniq[:25]:
            print(f'  {rel}:{i}: {txt}')
        if len(uniq) > 25:
            print(f'  ... +{len(uniq)-25}')

print()
print('=== Dim x(N) where N not 0/1/2 ===')
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in skip_dirs]
    if set(dirpath.split(os.sep)) & skip_dirs:
        continue
    for fn in filenames:
        if not fn.endswith('.abp'): continue
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, root).replace('\\', '/')
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f, 1):
                code = strip_code(line)
                for m in dim_re.finditer(code):
                    n = int(m.group(1))
                    if n not in (0, 1, 2):
                        print(f'  {rel}:{i}: Dim ...({n})  | {line.strip()[:100]}')

print()
print('=== SIZE LITERALS (63/64/255/256/259/260/511/512/1023/1024/2047/2048/4095/4096) ===')
for v in size_vals:
    hits = results.get(str(v), []) + results.get(str(-v), [])
    if not hits:
        continue
    print(f'--- {v} ({len(hits)}) ---')
    for rel, i, txt, val in hits[:20]:
        print(f'  {rel}:{i}: {txt}')
    if len(hits) > 20:
        print(f'  ... +{len(hits)-20}')

print()
print('=== AstLowerApi.abp all non-0/1/2/-1 ===')
for rel, i, txt, val in results.get('8', []) + []:
    pass
for key, hits in sorted(results.items(), key=lambda x: abs(int(x[0].replace('&H','0x') if False else (0)))):
    pass
api_hits = []
for key, hits in results.items():
    for rel, i, txt, val in hits:
        if rel == 'AstLowerApi.abp':
            api_hits.append((i, val, txt))
api_hits.sort()
for i, val, txt in api_hits:
    print(f'  L{i}: {val} | {txt}')

print()
print('TOTAL source magic:', sum(len(v) for v in results.values()))
