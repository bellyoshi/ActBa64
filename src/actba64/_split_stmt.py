# Split LowStmtHeavy into per-statement helpers.
path = r'c:\Users\bellm\source\repos\ActBa64\src\actba64\AstLower.abp'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

start = end = None
for i, l in enumerate(lines):
    if l.startswith('Function LowStmtHeavy'):
        start = i
    if start is not None and l.startswith('Function LowStmtList'):
        end = i
        break

fn = lines[start:end]

# Top-level only: exactly 4 spaces then If/ElseIf/Else/End If
branches = []
close_i = None
for i, l in enumerate(fn):
    if not l.startswith('    '):
        continue
    if len(l) > 4 and l[4] == ' ':
        continue  # nested
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
    return [l.replace('LowStmtHeavy =', new_name + ' =') for l in body_lines]

COMMON_DIM = '''    Dim stackPad(2047) As Byte
    Dim vOff As Long
    Dim vTy As Long
    Dim vTypeIdx As Long
    Dim vByRef As Long
    Dim vGlob As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim si As Long
    Dim offs As *Long
    Dim labElse As Long
    Dim labEnd As Long
    Dim labTop As Long
    Dim lab As Long
    Dim labStr As Long
    Dim jcc As Long
    Dim body As Long
    Dim leftK As Long
    Dim leftIdx As Long
    Dim tt As *TypeTable
    Dim typeIdxs As *Long
    Dim foff As Long
    Dim fsz As Long
    Dim fcnt As Long
    Dim fieldTy As Long
    Dim ti As Long
    Dim fname(63) As Byte
    Dim base As Long
    Dim ix As Long
    Dim saveDo As Long
    Dim saveWhile As Long
    Dim saveFor As Long
    Dim doMode As Long
    Dim cond As Long
    Dim stepIdx As Long
    Dim labStepNeg As Long
    Dim labStepCont As Long
    Dim useInc As Long
    Dim byRefs As *Long
    Dim types As *Long
    Dim list As *IrList
    Dim args(15) As Long
    Dim argi As Long
    Dim argn As Long
    Dim nArgs As Long
    Dim stk As Long
    Dim labSub As Long
    Dim labDone As Long
    Dim sApi(31) As Byte
    Dim j As Long
    Dim kCtor(7) As Byte
    Dim names As *Byte

'''

SETUP = '''    {ret} = 0
    ast = ctx->ast
    nodes = ast->nodes
    tt = ast->types
    typeIdxs = ctx->typeIdxs
    list = ctx->list
    offs = ctx->offs
    types = ctx->types
    byRefs = ctx->byRefs

'''

def make_fn(name, body_lines):
    body = rename_ret(body_lines, name)
    while body and body[-1].strip() == '':
        body.pop()
    parts = []
    parts.append('Function %s(ctx As *LowerCtx, idx As Long) As Long\n' % name)
    parts.append(COMMON_DIM)
    parts.append(SETUP.format(ret=name))
    parts.extend(body)
    parts.append('End Function\n')
    return parts

new_fns = []
for name, pat in [
    ('LowStmtDim', 'AST_DIM'),
    ('LowStmtAssign', 'AST_ASSIGN'),
    ('LowStmtInsMenu', 'AST_INSMENU'),
    ('LowStmtPrint', 'AST_PRINT'),
    ('LowStmtInput', 'AST_INPUT'),
    ('LowStmtDo', 'AST_DO'),
    ('LowStmtWhile', 'AST_WHILE'),
    ('LowStmtFor', 'AST_FOR'),
    ('LowStmtWith', 'AST_WITH'),
]:
    new_fns.extend(make_fn(name, branch_body(pat)))
    new_fns.append('\n')
    print(name, 'body lines', len(branch_body(pat)))

dispatch = '''Function LowStmtHeavy(ctx As *LowerCtx, idx As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim k As Long

    LowStmtHeavy = 0
    If idx < 0 Then
        LowStmtHeavy = 1
        Exit Function
    End If
    ast = ctx->ast
    nodes = ast->nodes
    k = nodes[idx].kind

    If k = AST_DIM Then
        LowStmtHeavy = LowStmtDim(ctx, idx)
        Exit Function
    End If
    If k = AST_CONST Or k = AST_TYPE Or k = AST_FUNC Or k = AST_DECLARE Then
        LowStmtHeavy = 1
        Exit Function
    End If
    If k = AST_ASSIGN Then
        LowStmtHeavy = LowStmtAssign(ctx, idx)
        Exit Function
    End If
    If k = AST_INSMENU Then
        LowStmtHeavy = LowStmtInsMenu(ctx, idx)
        Exit Function
    End If
    If k = AST_CALL Then
        LowStmtHeavy = LowExpr(ctx, idx)
        Exit Function
    End If
    If k = AST_EXIT Then
        If LowExpr(ctx, nodes[idx].left) = 0 Then Exit Function
        LowEmitExitEax(ctx)
        LowStmtHeavy = 1
        Exit Function
    End If
    If k = AST_EXITDO Then
        If g_doEndLab < 0 Then
            ctx->err = 1
            Exit Function
        End If
        IrEmit(ctx->list, OP_JMP, g_doEndLab, 0)
        LowStmtHeavy = 1
        Exit Function
    End If
    If k = AST_EXITWHILE Then
        If g_whileEndLab < 0 Then
            ctx->err = 1
            Exit Function
        End If
        IrEmit(ctx->list, OP_JMP, g_whileEndLab, 0)
        LowStmtHeavy = 1
        Exit Function
    End If
    If k = AST_EXITFOR Then
        If g_forEndLab < 0 Then
            ctx->err = 1
            Exit Function
        End If
        IrEmit(ctx->list, OP_JMP, g_forEndLab, 0)
        LowStmtHeavy = 1
        Exit Function
    End If
    If k = AST_EXITFUNC Then
        If g_funcEndLab < 0 Then
            ctx->err = 1
            Exit Function
        End If
        IrEmit(ctx->list, OP_JMP, g_funcEndLab, 0)
        LowStmtHeavy = 1
        Exit Function
    End If
    If k = AST_END Then
        LowEmitExitImm(ctx, 0)
        LowStmtHeavy = 1
        Exit Function
    End If
    If k = AST_PRINT Then
        LowStmtHeavy = LowStmtPrint(ctx, idx)
        Exit Function
    End If
    If k = AST_INPUT Then
        LowStmtHeavy = LowStmtInput(ctx, idx)
        Exit Function
    End If
    If k = AST_IF Then
        LowStmtHeavy = LowStmtIf(ctx, idx)
        Exit Function
    End If
    If k = AST_DO Then
        LowStmtHeavy = LowStmtDo(ctx, idx)
        Exit Function
    End If
    If k = AST_WHILE Then
        LowStmtHeavy = LowStmtWhile(ctx, idx)
        Exit Function
    End If
    If k = AST_FOR Then
        LowStmtHeavy = LowStmtFor(ctx, idx)
        Exit Function
    End If
    If k = AST_WITH Then
        LowStmtHeavy = LowStmtWith(ctx, idx)
        Exit Function
    End If
    Print "error: unsupported statement kind " + Str$(k)
    ctx->err = 1
End Function
'''

out = lines[:start] + new_fns + [dispatch, '\n'] + lines[end:]
with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(out)
print('LowStmtHeavy split OK')
