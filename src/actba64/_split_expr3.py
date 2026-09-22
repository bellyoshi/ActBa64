# Final size cuts for remaining LowExpr* helpers.
import re

path = 'AstLower.abp'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    src = f.read()


def extract_func(src, name):
    pat = re.compile(
        r'^Function\s+' + re.escape(name) + r'\(.*?\nEnd Function\n',
        re.M | re.S,
    )
    m = pat.search(src)
    if not m:
        raise SystemExit('missing ' + name)
    return m.start(), m.end(), m.group(0)


# --- BuiltinStr: extract RIGHT ---
s, e, fn = extract_func(src, 'LowExprBuiltinStr')
# Find ElseIf BI_RIGHT ... until ElseIf BIK_RGB
m = re.search(
    r'(    ElseIf nodes\[idx\]\.num = BI_RIGHT Then\n)'
    r'(.*?)\n'
    r'(    ElseIf nodes\[idx\]\.num = BIK_RGB Then\n)',
    fn, re.S,
)
if not m:
    raise SystemExit('RIGHT block not found')
right_body = m.group(2)
# undent one level from body (was under ElseIf)
right_lines = []
for l in right_body.splitlines(True):
    if l.startswith('        '):
        right_lines.append(l[4:])
    else:
        right_lines.append(l)
right_fn = '''Function LowExprBuiltinRight(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim lab As Long
    Dim labZ As Long
    Dim labA As Long
    Dim labB As Long

    LowExprBuiltinRight = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
''' + ''.join(right_lines).replace('LowExprBuiltinStr =', 'LowExprBuiltinRight =') + '''
    LowExprBuiltinRight = 1
End Function

'''
# The original body already sets LowExprBuiltinStr = 1 at end - when extracting, that becomes Right = 1, then we add another = 1. Fix: don't double.
right_text = ''.join(right_lines).replace('LowExprBuiltinStr =', 'LowExprBuiltinRight =')
# if already ends with LowExprBuiltinRight = 1, don't add again
if 'LowExprBuiltinRight = 1' not in right_text:
    right_text += '    LowExprBuiltinRight = 1\n'
right_fn = '''Function LowExprBuiltinRight(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim lab As Long
    Dim labZ As Long
    Dim labA As Long
    Dim labB As Long

    LowExprBuiltinRight = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
''' + right_text + '''End Function

'''
new_str = fn[:m.start()] + '    ElseIf nodes[idx].num = BI_RIGHT Then\n        LowExprBuiltinStr = LowExprBuiltinRight(ctx, idx)\n' + fn[m.start(3):]
# Update dispatcher to route RIGHT to Right helper via Str still - Str calls Right. Also can route from Builtin dispatcher.
src = src[:s] + right_fn + new_str + src[e:]

# --- BuiltinCore: extract MEMCPY/FILLMEMORY/ASC ---
s, e, fn = extract_func(src, 'LowExprBuiltinCore')
m = re.search(
    r'(    ElseIf nodes\[idx\]\.num = BI_FILLMEMORY Then\n)'
    r'(.*?)\n'
    r'(    ElseIf nodes\[idx\]\.num = BI_STRPTR Then\n)',
    fn, re.S,
)
if not m:
    raise SystemExit('FILLMEMORY..STRPTR not found')
# Includes FILLMEMORY, ASC - stop before STRPTR. Wait ASC is between FILL and STRPTR.
# Actually pattern stops at STRPTR, so body is FILLMEMORY + ASC. Also need MEMCPY which is after MAKESTR.
# Better: extract from BI_FILLMEMORY through BI_MEMCPY (inclusive), leave STR/MAKESTR/STRPTR in core.

m2 = re.search(
    r'(    ElseIf nodes\[idx\]\.num = BI_FILLMEMORY Then\n)'
    r'(.*?)'
    r'(    ElseIf nodes\[idx\]\.num = BI_STRPTR Then\n)'
    r'(.*?)'
    r'(    ElseIf nodes\[idx\]\.num = BI_MEMCPY Then\n)'
    r'(.*?)'
    r'(    Else\n)',
    fn, re.S,
)
if not m2:
    raise SystemExit('mem block markers')
# Reorder: keep STRPTR/STR/MAKESTR in core; move FILL, ASC, MEMCPY to Mem helper.
# Simpler approach: extract only BI_MEMCPY and BI_FILLMEMORY and BI_ASC as three early exits in a new function called from dispatcher.

# Extract FILLMEMORY+ASC as one block before STRPTR, and MEMCPY before Else
fill_asc = m2.group(1) + m2.group(2)  # FILLMEMORY Then ... (ends before STRPTR)
memcpy_block = m2.group(5) + m2.group(6)  # MEMCPY Then ... (ends before Else)

mem_chain = fill_asc + memcpy_block
# convert first ElseIf to If, rename
mem_lines = mem_chain.splitlines(True)
if mem_lines[0].strip().startswith('ElseIf'):
    mem_lines[0] = mem_lines[0].replace('ElseIf ', 'If ', 1)
mem_body = ''.join(mem_lines).replace('LowExprBuiltinCore =', 'LowExprBuiltinMem =')
mem_fn = '''Function LowExprBuiltinMem(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim labZ As Long
    Dim labE As Long
    Dim sLen(15) As Byte

    LowExprBuiltinMem = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
''' + mem_body + '''    Else
        LowExprBuiltinMem = -1
    End If
End Function

'''
# Remove FILL/ASC and MEMCPY from core; keep STRPTR/STR/MAKESTR
core_new = fn[:m2.start()] + m2.group(3) + m2.group(4) + m2.group(7) + '        LowExprBuiltinCore = -1\n    End If\nEnd Function\n'
# Wait m2.group(7) is `    Else\n` - then we need the -1 body. Original was Else / = -1 / End If
# fn ends with Else / = -1 / End If / End Function
# After removing MEMCPY, structure: ... MAKESTR ... ElseIf STRPTR ... STR ... MAKESTR wait

# Let me redo more carefully by line surgery
lines = fn.splitlines(True)
# Find indices
def find_elif(name):
    for i, l in enumerate(lines):
        if l.strip().startswith('ElseIf nodes[idx].num = ' + name):
            return i
    return None
i_fill = find_elif('BI_FILLMEMORY')
i_asc = find_elif('BI_ASC')
i_strptr = find_elif('BI_STRPTR')
i_memcpy = find_elif('BI_MEMCPY')
i_else = None
for i, l in enumerate(lines):
    if l.strip() == 'Else' and i > i_memcpy:
        i_else = i
        break
# Mem function gets fill..asc-1? No: fill through asc (until strptr), plus memcpy until else
block1 = lines[i_fill:i_strptr]
block2 = lines[i_memcpy:i_else]
mem_lines = block1 + block2
mem_lines[0] = mem_lines[0].replace('ElseIf ', 'If ', 1)
mem_body = ''.join(l.replace('LowExprBuiltinCore =', 'LowExprBuiltinMem =') for l in mem_lines)
mem_fn = '''Function LowExprBuiltinMem(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim labZ As Long
    Dim labE As Long
    Dim sLen(15) As Byte

    LowExprBuiltinMem = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
''' + mem_body + '''    Else
        LowExprBuiltinMem = -1
    End If
End Function

'''
core_lines = lines[:i_fill] + lines[i_strptr:i_memcpy] + lines[i_else:]
core_fn = ''.join(core_lines)
src = src[:s] + mem_fn + core_fn + src[e:]

# Update LowExprBuiltin dispatcher
s, e, fn = extract_func(src, 'LowExprBuiltin')
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
    If n = BI_FILLMEMORY Or n = BI_ASC Or n = BI_MEMCPY Then
        LowExprBuiltin = LowExprBuiltinMem(ctx, idx)
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
src = src[:s] + disp + src[e:]

# --- CallIntrin: extract memcpy/fillmemory ---
s, e, fn = extract_func(src, 'LowExprCallIntrin')
lines = fn.splitlines(True)
i_memcpy = next(i for i, l in enumerate(lines) if 'lstrcpy(VarPtr(buf), "memcpy")' in l)
mem_part = lines[i_memcpy:]
# remove End Function from mem_part
mem_part = [l for l in mem_part if not l.startswith('End Function')]
memop = '''Function LowExprCallMemOp(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim buf(255) As Byte
    Dim list As *IrList
    Dim sLen(15) As Byte
    Dim args(15) As Long
    Dim argi As Long
    Dim argn As Long
    Dim stk As Long

    LowExprCallMemOp = -1
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    AstCopyStr(ast, idx, VarPtr(name))
''' + ''.join(l.replace('LowExprCallIntrin =', 'LowExprCallMemOp =') for l in mem_part) + '''End Function

'''
intrin_new = ''.join(lines[:i_memcpy]) + 'End Function\n'
# Wire Intrin to try MemOp at end - actually Call dispatcher should try MemOp. Simpler: at end of Intrin before End Function:
intrin_new = ''.join(lines[:i_memcpy])
intrin_new += '''    LowExprCallMemOp = LowExprCallMemOp(ctx, idx)
    If LowExprCallMemOp > 0 Then
        LowExprCallIntrin = LowExprCallMemOp
        Exit Function
    End If
    If ctx->err <> 0 Then Exit Function
End Function
'''
# BUG: can't use LowExprCallMemOp as both name and temp. Fix:
intrin_new = ''.join(lines[:i_memcpy])
# Need a Dim r - Intrin doesn't have r. Use inline:
intrin_new = '''Function LowExprCallIntrin(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim buf(255) As Byte
    Dim list As *IrList
    Dim argn As Long
    Dim r As Long

    LowExprCallIntrin = -1
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    AstCopyStr(ast, idx, VarPtr(name))
''' + ''.join(lines[lines.index('    lstrcpy(VarPtr(buf), "free")\n'):i_memcpy]).replace('LowExprCallIntrin = 0', 'LowExprCallIntrin = -1') + '''    r = LowExprCallMemOp(ctx, idx)
    If ctx->err <> 0 Then Exit Function
    If r > 0 Then
        LowExprCallIntrin = r
    End If
End Function

'''
# Get free/malloc/calloc only from original
free_start = next(i for i, l in enumerate(lines) if 'lstrcpy(VarPtr(buf), "free")' in l)
intrin_body = ''.join(lines[free_start:i_memcpy])
intrin_new = '''Function LowExprCallIntrin(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim buf(255) As Byte
    Dim list As *IrList
    Dim argn As Long
    Dim r As Long

    LowExprCallIntrin = -1
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    AstCopyStr(ast, idx, VarPtr(name))
''' + intrin_body + '''    r = LowExprCallMemOp(ctx, idx)
    If ctx->err <> 0 Then Exit Function
    If r > 0 Then
        LowExprCallIntrin = r
    End If
End Function

'''
src = src[:s] + memop + intrin_new + src[e:]

# --- CallNormal: extract array index ---
s, e, fn = extract_func(src, 'LowExprCallNormal')
m = re.search(
    r'(    If LowLookupVar\(ctx, VarPtr\(name\).*?\n)'
    r'(.*?)\n'
    r'(    lab = LowFindFunc\(ctx, VarPtr\(name\)\))',
    fn, re.S,
)
if not m:
    raise SystemExit('array block not found')
arr_body = m.group(1) + m.group(2)
arr_fn = '''Function LowExprCallArr(ctx As *LowerCtx, idx As Long) As Long
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

    LowExprCallArr = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    AstCopyStr(ast, idx, VarPtr(name))
''' + arr_body.replace('LowExprCallNormal =', 'LowExprCallArr =') + '''
End Function

'''
# Fix: arr_body starts with If LowLookupVar - good. But has Exit Function with = 1.
# New Normal:
norm = '''Function LowExprCallNormal(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
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
    If LowExprCallArr(ctx, idx) <> 0 Then
        LowExprCallNormal = 1
        Exit Function
    End If
    If ctx->err <> 0 Then Exit Function
''' + fn[m.start(3):]
# fn[m.start(3):] starts with lab = LowFindFunc... through End Function
src = src[:s] + arr_fn + norm + src[e:]

# --- CallMethod: extract invoke tail ---
s, e, fn = extract_func(src, 'LowExprCallMethod')
m = re.search(
    r'(    lab = -1\n)'
    r'(.*?)\n'
    r'(    LowEmitCallFinish\(list, stk\)\n)'
    r'(    LowExprCallMethod = 1\n)'
    r'(    Exit Function\n)'
    r'(End Function\n)',
    fn, re.S,
)
if not m:
    raise SystemExit('method invoke not found')
invoke_body = m.group(1) + m.group(2) + m.group(3)
invoke_fn = '''Function LowExprCallMethodInvoke(ctx As *LowerCtx, idx As Long, ti As Long, nArgs As Long, stk As Long) As Long
    Dim name(63) As Byte
    Dim buf(255) As Byte
    Dim list As *IrList
    Dim lab As Long
    Dim vals As *Long
    Dim tt As *TypeTable
    Dim j As Long
    Dim names As *Byte
    Dim ast As *Ast

    LowExprCallMethodInvoke = 0
    ast = ctx->ast
    list = ctx->list
    tt = ast->types
    AstCopyStr(ast, idx, VarPtr(name))
    j = ti * 48
    names = tt->typeNames
''' + invoke_body.replace('LowExprCallMethod =', 'LowExprCallMethodInvoke =') + '''
    LowExprCallMethodInvoke = 1
End Function

'''
# Fix double assignment
invoke_text = invoke_body  # has lab=-1 ... LowEmitCallFinish, no =1
invoke_fn = '''Function LowExprCallMethodInvoke(ctx As *LowerCtx, idx As Long, ti As Long, nArgs As Long, stk As Long) As Long
    Dim name(63) As Byte
    Dim buf(255) As Byte
    Dim list As *IrList
    Dim lab As Long
    Dim vals As *Long
    Dim tt As *TypeTable
    Dim j As Long
    Dim names As *Byte
    Dim ast As *Ast

    LowExprCallMethodInvoke = 0
    ast = ctx->ast
    list = ctx->list
    tt = ast->types
    AstCopyStr(ast, idx, VarPtr(name))
    j = ti * 48
    names = tt->typeNames
''' + invoke_text + '''
    LowExprCallMethodInvoke = 1
End Function

'''
method_new = fn[:m.start()] + '    If LowExprCallMethodInvoke(ctx, idx, ti, nArgs, stk) = 0 Then Exit Function\n    LowExprCallMethod = 1\nEnd Function\n'
src = src[:s] + invoke_fn + method_new + src[e:]

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(src)
print('expr3 OK')
