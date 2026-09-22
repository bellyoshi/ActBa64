# Trim unused Dim locals from LowStmt* helpers in AstLower.abp
import re

path = 'AstLower.abp'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()
lines = text.splitlines(True)

TARGETS = {
    'LowStmtDim', 'LowStmtAssign', 'LowStmtInsMenu', 'LowStmtPrint',
    'LowStmtInput', 'LowStmtDo', 'LowStmtWhile', 'LowStmtFor', 'LowStmtWith',
    'LowExprNum', 'LowExprString', 'LowExprVar', 'LowExprMember', 'LowExprIndex',
    'LowExprBuiltin', 'LowExprCall', 'LowExprUnary', 'LowExprBinop', 'LowExprCast',
}

fn_re = re.compile(r'^(Function|Sub)\s+(\w+)', re.I)
end_re = re.compile(r'^End\s+(Function|Sub)\b', re.I)
dim_re = re.compile(r'^\s*Dim\s+(\w+)', re.I)

# Always keep stackPad even if only declared
KEEP_ALWAYS = {'stackPad'}


def process_func(start, end):
    """Return new lines for function body region [start+1:end] (exclusive of End)."""
    body = lines[start + 1:end]
    # Split Dim block vs rest
    dim_idxs = []
    first_non_dim = 0
    for i, ln in enumerate(body):
        t = ln.strip()
        if not t:
            if dim_idxs and first_non_dim == 0:
                first_non_dim = i  # blank after dims candidate
            continue
        if t.startswith("'"):
            continue
        m = dim_re.match(ln)
        if m:
            dim_idxs.append((i, m.group(1), ln))
            continue
        first_non_dim = i
        break
    else:
        first_non_dim = len(body)

    # Find end of contiguous Dim block (allow blanks/comments within)
    last_dim = dim_idxs[-1][0] if dim_idxs else -1
    code_start = last_dim + 1
    while code_start < len(body) and (not body[code_start].strip() or body[code_start].strip().startswith("'")):
        # keep one blank after dims; stop at first real code
        if body[code_start].strip().startswith("'") and code_start > last_dim + 1:
            break
        if not body[code_start].strip():
            code_start += 1
            continue
        break
    # Actually: code starts at first non-dim non-blank non-comment after dims
    code_start = last_dim + 1
    while code_start < len(body):
        t = body[code_start].strip()
        if not t or t.startswith("'"):
            code_start += 1
            continue
        if dim_re.match(body[code_start]):
            code_start += 1
            continue
        break

    code = ''.join(body[code_start:])
    used = set()
    for _, name, _ in dim_idxs:
        # word boundary match in code
        if re.search(r'\b' + re.escape(name) + r'\b', code):
            used.add(name)
    used |= KEEP_ALWAYS

    new_dims = []
    for _, name, ln in dim_idxs:
        if name in used:
            new_dims.append(ln)

    # Drop unused setup assigns like `tt = ast->types` when tt unused
    setup_drop = set()
    for name in [n for _, n, _ in dim_idxs if n not in used]:
        setup_drop.add(name)

    new_code_lines = []
    for ln in body[code_start:]:
        t = ln.strip()
        # drop `name = ...` where name is unused dim
        m = re.match(r'^(\w+)\s*=', t)
        if m and m.group(1) in setup_drop:
            continue
        new_code_lines.append(ln)

    out = []
    out.extend(new_dims)
    if new_dims and (not new_code_lines or new_code_lines[0].strip()):
        out.append('\n')
    out.extend(new_code_lines)
    return out


i = 0
out_lines = []
changed = []
while i < len(lines):
    m = fn_re.match(lines[i].strip())
    if m and m.group(2) in TARGETS:
        name = m.group(2)
        start = i
        j = i + 1
        while j < len(lines) and not end_re.match(lines[j].strip()):
            j += 1
        if j >= len(lines):
            out_lines.append(lines[i])
            i += 1
            continue
        new_body = process_func(start, j)
        old_phys = j - start - 1
        new_phys = len(new_body)
        changed.append((name, old_phys, new_phys))
        out_lines.append(lines[start])
        out_lines.extend(new_body)
        out_lines.append(lines[j])  # End Function
        i = j + 1
        continue
    out_lines.append(lines[i])
    i += 1

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(out_lines)

for name, o, n in changed:
    print('%s: %d -> %d phys body' % (name, o, n))
