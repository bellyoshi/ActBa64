# Split LowExpr into per-kind helpers.
path = r'c:\Users\bellm\source\repos\ActBa64\src\actba64\AstLower.abp'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

start = end = None
for i, l in enumerate(lines):
    if l.startswith('Function LowExpr('):
        start = i
    if start is not None and i > start and l.startswith("Function LowEmitStrCmp"):
        end = i
        break
if start is None or end is None:
    raise SystemExit('LowExpr bounds not found')

fn = lines[start:end]
# Keep preamble (comment before LowEmitStrCmp) out of fn - end points at LowEmitStrCmp

# Top-level only: exactly 4 spaces then If/ElseIf/Else/End If for k =
branches = []
close_i = None
for i, l in enumerate(fn):
    if not l.startswith('    '):
        continue
    if len(l) > 4 and l[4] == ' ':
        continue
    t = l.strip()
    if t.startswith('If k = AST_') or t.startswith('ElseIf k = AST_') or t == 'Else':
        branches.append((i, t))
    if t == 'End If' and branches:
        close_i = i

print('branches:')
for i, t in branches:
    print(i, t)
print('close', close_i)

def branch_body(name_pat):
    for bi, (i, t) in enumerate(branches):
        if name_pat in t:
            start_b = i + 1
            if bi + 1 < len(branches):
                end_b = branches[bi + 1][0]
            else:
                end_b = close_i
            return fn[start_b:end_b]
    raise SystemExit('branch not found: ' + name_pat)

def rename_ret(body_lines, new_name):
    return [l.replace('LowExpr =', new_name + ' =') for l in body_lines]

# Extract Dim lines from original function (between Function and first non-dim code)
dim_lines = []
for l in fn[1:]:
    t = l.strip()
    if t.startswith('Dim '):
        dim_lines.append(l)
        continue
    if not t:
        if dim_lines:
            break
        continue
    if t.startswith("'"):
        if dim_lines:
            break
        continue
    break

COMMON_DIM = ''.join(dim_lines)
if 'stackPad' not in COMMON_DIM:
    COMMON_DIM = '    Dim stackPad(2047) As Byte\n' + COMMON_DIM

SETUP = '''    {ret} = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    tt = ast->types
    offs = ctx->offs
    types = ctx->types
    typeIdxs = ctx->typeIdxs
    byRefs = ctx->byRefs

'''

def undent(body_lines):
    """Body was nested under If; keep as-is (already 8-space indent for statements)."""
    return body_lines

def make_fn(name, body_lines):
    body = rename_ret(list(body_lines), name)
    while body and body[-1].strip() == '':
        body.pop()
    # Dedent one level (8 spaces -> 4) for statements that were under If
    out_body = []
    for l in body:
        if l.startswith('        '):
            out_body.append(l[4:])
        elif l.startswith('\t'):
            out_body.append(l)
        else:
            out_body.append(l)
    parts = []
    parts.append('Function %s(ctx As *LowerCtx, idx As Long) As Long\n' % name)
    parts.append(COMMON_DIM)
    if not COMMON_DIM.endswith('\n\n') and not COMMON_DIM.endswith('\n'):
        parts.append('\n')
    parts.append('\n')
    parts.append(SETUP.format(ret=name))
    parts.extend(out_body)
    if not out_body[-1].endswith('\n'):
        parts.append('\n')
    parts.append('End Function\n\n')
    return ''.join(parts)

helpers = []
mapping = [
    ('AST_NUM', 'LowExprNum'),
    ('AST_STRING', 'LowExprString'),
    ('AST_VAR', 'LowExprVar'),
    ('AST_MEMBER', 'LowExprMember'),
    ('AST_INDEX', 'LowExprIndex'),
    ('AST_BUILTIN', 'LowExprBuiltin'),
    ('AST_CALL', 'LowExprCall'),
    ('AST_UNARY', 'LowExprUnary'),
    ('AST_BINOP', 'LowExprBinop'),
    ('AST_CAST', 'LowExprCast'),
]
for pat, name in mapping:
    body = branch_body(pat)
    helpers.append(make_fn(name, body))
    print('%s body lines %d' % (name, len(body)))

dispatcher = '''Function LowExpr(ctx As *LowerCtx, idx As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim k As Long
    Dim list As *IrList
    Dim v As Long
    Dim buf(255) As Byte

    LowExpr = 0
    If idx < 0 Then
        ctx->err = 1
        Exit Function
    End If
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes

    If LowConstInt(ast, idx, v) <> 0 Then
        IrEmit(list, OP_MOV_EAX_IMM, v, 0)
        LowExpr = 1
        Exit Function
    End If
    If LowConstStr(ast, idx, VarPtr(buf)) <> 0 Then
        IrEmitStr(list, OP_LEA_RAX_STR, 0, VarPtr(buf))
        LowExpr = 1
        Exit Function
    End If

    k = nodes[idx].kind
    If k = AST_NUM Then
        LowExpr = LowExprNum(ctx, idx)
        Exit Function
    End If
    If k = AST_STRING Then
        LowExpr = LowExprString(ctx, idx)
        Exit Function
    End If
    If k = AST_VAR Then
        LowExpr = LowExprVar(ctx, idx)
        Exit Function
    End If
    If k = AST_MEMBER Then
        LowExpr = LowExprMember(ctx, idx)
        Exit Function
    End If
    If k = AST_INDEX Then
        LowExpr = LowExprIndex(ctx, idx)
        Exit Function
    End If
    If k = AST_BUILTIN Then
        LowExpr = LowExprBuiltin(ctx, idx)
        Exit Function
    End If
    If k = AST_CALL Then
        LowExpr = LowExprCall(ctx, idx)
        Exit Function
    End If
    If k = AST_UNARY Then
        LowExpr = LowExprUnary(ctx, idx)
        Exit Function
    End If
    If k = AST_BINOP Then
        LowExpr = LowExprBinop(ctx, idx)
        Exit Function
    End If
    If k = AST_CAST Then
        LowExpr = LowExprCast(ctx, idx)
        Exit Function
    End If
    Print "error: unsupported expr kind " + Str$(k)
    ctx->err = 1
End Function

'''

new_block = ''.join(helpers) + dispatcher
# Preserve any blank lines / comments between LowExpr End and LowEmitStrCmp
after = lines[end:]
# Find original End Function of LowExpr within fn
# Replace lines[start:end] with new_block
out = lines[:start] + [new_block] + after
# new_block is one big string - need to split to lines for consistency
text = ''.join(lines[:start]) + new_block + ''.join(after)
with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
print('LowExpr split OK')
