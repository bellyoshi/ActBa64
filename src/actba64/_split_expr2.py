# Split oversized LowExprBuiltin / LowExprCall / LowExprBinop further.
import re

path = 'AstLower.abp'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    src = f.read()


def extract_func(src, name):
    pat = re.compile(
        r'^Function\s+' + re.escape(name) + r'\b.*?\nEnd Function\n',
        re.M | re.S,
    )
    m = pat.search(src)
    if not m:
        raise SystemExit('missing ' + name)
    return m.start(), m.end(), m.group(0)


def split_binop(fn_text):
    # Extract comparison ElseIf block into LowExprBinopCmp
    # Extract IDIV..POW into LowExprBinopDiv
    lines = fn_text.splitlines(True)
    # Find top-level ElseIf op = BOP_IDIV and ElseIf op = BOP_EQ and Else / End If
    # Body uses 4-space base (already undented)
    idiv_i = eq_i = else_i = endif_i = None
    for i, l in enumerate(lines):
        t = l.strip()
        if not l.startswith('    '):
            continue
        if len(l) > 4 and l[4] == ' ':
            continue
        if t.startswith('ElseIf op = BOP_IDIV'):
            idiv_i = i
        if t.startswith('ElseIf op = BOP_EQ'):
            eq_i = i
        if t == 'Else' and eq_i is not None and else_i is None:
            else_i = i
        if t == 'End If' and eq_i is not None:
            endif_i = i
    if idiv_i is None or eq_i is None or else_i is None or endif_i is None:
        raise SystemExit('binop markers: %s %s %s %s' % (idiv_i, eq_i, else_i, endif_i))

    # Find start of first big If op = BOP_ADD Or op = BOP_MUL...
    arith_if = None
    for i, l in enumerate(lines):
        t = l.strip()
        if t.startswith('If op = BOP_ADD Or op = BOP_MUL'):
            arith_if = i
            break
    if arith_if is None:
        raise SystemExit('arith if not found')

    # CAT early exit block stays in Binop
    # Build helpers

    dim_cmp = '''Function LowExprBinopCmp(ctx As *LowerCtx, idx As Long, op As Long, fty As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim labB As Long

    LowExprBinopCmp = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
'''
    # body of cmp was under ElseIf - content from eq_i+1 to else_i
    cmp_body = lines[eq_i + 1:else_i]
    # undent one level
    cmp_body2 = []
    for l in cmp_body:
        if l.startswith('        '):
            cmp_body2.append(l[4:])
        else:
            cmp_body2.append(l)
    # rename ret
    cmp_body2 = [l.replace('LowExprBinop =', 'LowExprBinopCmp =') for l in cmp_body2]
    dim_cmp += ''.join(cmp_body2)
    dim_cmp += 'End Function\n\n'

    dim_div = '''Function LowExprBinopDiv(ctx As *LowerCtx, idx As Long, op As Long, fty As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim lab As Long
    Dim labB As Long

    LowExprBinopDiv = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
'''
    # Convert ElseIf chain starting at IDIV into If chain for standalone function
    div_lines = lines[idiv_i:eq_i]
    # First line ElseIf -> If; keep rest ElseIf; no trailing Else from cmp
    out_div = []
    first = True
    for l in div_lines:
        t = l.strip()
        if first and t.startswith('ElseIf '):
            out_div.append(l.replace('ElseIf ', 'If ', 1))
            first = False
            continue
        out_div.append(l)
    out_div = [l.replace('LowExprBinop =', 'LowExprBinopDiv =') for l in out_div]
    dim_div += ''.join(out_div)
    dim_div += 'End Function\n\n'

    # Rebuild LowExprBinop: keep preamble through CAT block and arith If..End If, then dispatch
    # Remove from idiv_i through endif_i, replace with calls
    head = lines[:idiv_i]
    # head ends before IDIV ElseIf - but still has open If from arith_if that needs End If
    # Structure was:
    #   If ADD/MUL... Then
    #     ...
    #   ElseIf IDIV...
    #   ElseIf EQ...
    #   Else
    #   End If
    # After extracting, head should close the arith If with End If, then call Div/Cmp

    # Find matching: arith_if's Then body ends at idiv_i (ElseIf)
    # So change: keep lines[:idiv_i], append End If, then dispatch for div/cmp/else

    new_binop = ''.join(head)
    new_binop += '    End If\n'
    new_binop += '    If op = BOP_IDIV Or op = BOP_DIV Or op = BOP_MOD Or op = BOP_SHL Or op = BOP_SHR Or op = BOP_POW Then\n'
    new_binop += '        LowExprBinop = LowExprBinopDiv(ctx, idx, op, fty)\n'
    new_binop += '        Exit Function\n'
    new_binop += '    End If\n'
    new_binop += '    If op = BOP_EQ Or op = BOP_NE Or op = BOP_LT Or op = BOP_LE Or op = BOP_GT Or op = BOP_GE Then\n'
    new_binop += '        LowExprBinop = LowExprBinopCmp(ctx, idx, op, fty)\n'
    new_binop += '        Exit Function\n'
    new_binop += '    End If\n'
    new_binop += '    Print "error: unsupported binop " + Str$(op)\n'
    new_binop += '    ctx->err = 1\n'
    new_binop += 'End Function\n\n'

    return dim_div + dim_cmp + new_binop


def split_builtin(fn_text):
    lines = fn_text.splitlines(True)
    # Find ElseIf BI_LEFT at top level (4 spaces)
    left_i = None
    endif_i = None
    for i, l in enumerate(lines):
        t = l.strip()
        if not l.startswith('    '):
            continue
        if len(l) > 4 and l[4] == ' ':
            continue
        if t.startswith('ElseIf nodes[idx].num = BI_LEFT'):
            left_i = i
        if t == 'End If' and left_i is not None:
            endif_i = i
    if left_i is None or endif_i is None:
        raise SystemExit('builtin LEFT markers missing')

    # Find first If nodes[idx].num = BI_SIZEOF
    first_if = None
    for i, l in enumerate(lines):
        if l.strip().startswith('If nodes[idx].num = BI_SIZEOF'):
            first_if = i
            break

    # Core: from first_if to left_i (convert last to close), Str: from left_i to endif

    # Build Core: take lines[first_if:left_i] + Else unsupported + End If
    core_chain = lines[first_if:left_i]
    # Ensure ends with proper Else? Original continues with ElseIf LEFT - so core_chain last is previous branch body without Else.
    # Add Else unsupported
    core_body = ''.join(core_chain)
    core_body = core_body.replace('LowExprBuiltin =', 'LowExprBuiltinCore =')
    core_fn = '''Function LowExprBuiltinCore(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim vOff As Long
    Dim vTy As Long
    Dim vTypeIdx As Long
    Dim vByRef As Long
    Dim vGlob As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim list As *IrList
    Dim lab As Long
    Dim tt As *TypeTable
    Dim ti As Long
    Dim sz As Long
    Dim tsizes As *Long

    LowExprBuiltinCore = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    tt = ast->types

''' + core_body + '''    Else
        LowExprBuiltinCore = -1
    End If
End Function

'''

    # Str helper: ElseIf LEFT -> If LEFT
    str_chain = lines[left_i:endif_i]
    out_str = []
    first = True
    for l in str_chain:
        t = l.strip()
        if first and t.startswith('ElseIf '):
            out_str.append(l.replace('ElseIf ', 'If ', 1))
            first = False
            continue
        out_str.append(l)
    str_body = ''.join(out_str).replace('LowExprBuiltin =', 'LowExprBuiltinStr =')
    str_fn = '''Function LowExprBuiltinStr(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim lab As Long
    Dim labZ As Long
    Dim labA As Long
    Dim labB As Long

    LowExprBuiltinStr = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes

''' + str_body + '''End If
End Function

'''

    disp = '''Function LowExprBuiltin(ctx As *LowerCtx, idx As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim n As Long
    Dim r As Long

    LowExprBuiltin = 0
    ast = ctx->ast
    nodes = ast->nodes
    n = nodes[idx].num
    If n = BI_LEFT Or n = BI_MID Or n = BI_CHR Or n = BI_RIGHT Or n = BIK_RGB Or n = BI_LOWORD Then
        LowExprBuiltin = LowExprBuiltinStr(ctx, idx)
        Exit Function
    End If
    r = LowExprBuiltinCore(ctx, idx)
    If r < 0 Then
        Print "error: unsupported builtin " + Str$(n)
        ctx->err = 1
        Exit Function
    End If
    LowExprBuiltin = r
End Function

'''
    return core_fn + str_fn + disp


def split_call(fn_text):
    lines = fn_text.splitlines(True)
    # Find method block: If nodes[idx].extra = -3 Then ... Exit Function / End If
    method_start = method_end = None
    for i, l in enumerate(lines):
        t = l.strip()
        if t.startswith('If nodes[idx].extra = -3'):
            method_start = i
        if method_start is not None and method_end is None and t == 'End If':
            # first top-level End If after method start - need depth
            pass
    # Use depth counting from method_start
    depth = 0
    method_end = None
    for i in range(method_start, len(lines)):
        t = lines[i].strip()
        # only count at indent of method_start (4 spaces)
        ind = len(lines[i]) - len(lines[i].lstrip(' '))
        base_ind = len(lines[method_start]) - len(lines[method_start].lstrip(' '))
        if ind != base_ind:
            continue
        if t.startswith('If ') or t.startswith('ElseIf '):
            depth += 1
        if t.startswith('ElseIf ') and depth > 0:
            # ElseIf doesn't increase beyond If
            pass
        if t == 'End If':
            depth -= 1
            if depth == 0:
                method_end = i
                break
    # Fix depth: If increases, End If decreases; ElseIf doesn't change
    depth = 0
    method_end = None
    for i in range(method_start, len(lines)):
        t = lines[i].strip()
        ind = len(lines[i]) - len(lines[i].lstrip(' '))
        base_ind = len(lines[method_start]) - len(lines[method_start].lstrip(' '))
        if ind != base_ind:
            continue
        if t.startswith('If '):
            depth += 1
        elif t == 'End If':
            depth -= 1
            if depth == 0:
                method_end = i
                break
    if method_start is None or method_end is None:
        raise SystemExit('method block not found %s %s' % (method_start, method_end))

    # Intrinsics: from after method End If until If LowLookupVar
    lookup_i = None
    for i in range(method_end + 1, len(lines)):
        if lines[i].strip().startswith('If LowLookupVar(ctx, VarPtr(name)'):
            lookup_i = i
            break
    if lookup_i is None:
        raise SystemExit('lookup not found')

    # Method helper
    method_body = lines[method_start + 1:method_end]
    method_body = [l[4:] if l.startswith('        ') else l for l in method_body]
    method_body = [l.replace('LowExprCall =', 'LowExprCallMethod =') for l in method_body]
    method_fn = '''Function LowExprCallMethod(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim buf(255) As Byte
    Dim list As *IrList
    Dim lab As Long
    Dim nArgs As Long
    Dim vals As *Long
    Dim tt As *TypeTable
    Dim ti As Long
    Dim args(15) As Long
    Dim argi As Long
    Dim argn As Long
    Dim stk As Long
    Dim j As Long
    Dim useAddr As Long
    Dim names As *Byte

    LowExprCallMethod = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    tt = ast->types
    AstCopyStr(ast, idx, VarPtr(name))
''' + ''.join(method_body) + '''End Function

'''

    # Intrin: free/malloc/... block
    intrin_lines = lines[method_end + 1:lookup_i]
    intrin_lines = [l.replace('LowExprCall =', 'LowExprCallIntrin =') for l in intrin_lines]
    intrin_fn = '''Function LowExprCallIntrin(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim buf(255) As Byte
    Dim list As *IrList
    Dim nArgs As Long
    Dim sLen(15) As Byte
    Dim args(15) As Long
    Dim argi As Long
    Dim argn As Long
    Dim stk As Long

    LowExprCallIntrin = -1
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    AstCopyStr(ast, idx, VarPtr(name))
''' + ''.join(intrin_lines) + '''End Function

'''

    # Arr + Api rest becomes LowExprCallNormal
    # Find End Function
    rest = lines[lookup_i:]
    # rest starts with If LowLookupVar ... through End Function
    # Need preamble Dim + setup before lookup
    # Change: LowExprCall = LowExprCallNormal
    rest2 = []
    for l in rest:
        if l.startswith('End Function'):
            break
        rest2.append(l.replace('LowExprCall =', 'LowExprCallNormal ='))
    normal_fn = '''Function LowExprCallNormal(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim vOff As Long
    Dim vTy As Long
    Dim vTypeIdx As Long
    Dim vByRef As Long
    Dim vGlob As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim list As *IrList
    Dim lab As Long
    Dim nArgs As Long
    Dim tt As *TypeTable
    Dim byBits As Long
    Dim args(15) As Long
    Dim argi As Long
    Dim argn As Long
    Dim stk As Long
    Dim j As Long
    Dim bbit As Long
    Dim apiName(63) As Byte
    Dim isApi As Long
    Dim di As Long
    Dim dllKind As Long
    Dim dlls As *Long
    Dim bys As *Long
    Dim useAddr As Long

    LowExprCallNormal = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    tt = ast->types
    AstCopyStr(ast, idx, VarPtr(name))
''' + ''.join(rest2) + '''End Function

'''

    disp = '''Function LowExprCall(ctx As *LowerCtx, idx As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim r As Long

    LowExprCall = 0
    ast = ctx->ast
    nodes = ast->nodes
    If nodes[idx].extra = -3 Then
        LowExprCall = LowExprCallMethod(ctx, idx)
        Exit Function
    End If
    r = LowExprCallIntrin(ctx, idx)
    If ctx->err <> 0 Then Exit Function
    If r > 0 Then
        LowExprCall = r
        Exit Function
    End If
    LowExprCall = LowExprCallNormal(ctx, idx)
End Function

'''
    return method_fn + intrin_fn + normal_fn + disp


# Apply
s, e, fn = extract_func(src, 'LowExprBinop')
src = src[:s] + split_binop(fn) + src[e:]

s, e, fn = extract_func(src, 'LowExprBuiltin')
src = src[:s] + split_builtin(fn) + src[e:]

s, e, fn = extract_func(src, 'LowExprCall')
src = src[:s] + split_call(fn) + src[e:]

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(src)
print('expr2 split OK')
