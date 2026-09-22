# Further split oversized LowStmt* helpers and drop dead setup locals.
import re

path = 'AstLower.abp'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    src = f.read()

# --- helpers text to insert before LowStmtDim ---

DIM_CTOR = r'''Function LowStmtDimCtor(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim vOff As Long
    Dim vTy As Long
    Dim vTypeIdx As Long
    Dim vByRef As Long
    Dim vGlob As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim lab As Long
    Dim tt As *TypeTable
    Dim ti As Long
    Dim fname(63) As Byte
    Dim args(15) As Long
    Dim argi As Long
    Dim argn As Long
    Dim nArgs As Long
    Dim stk As Long
    Dim j As Long
    Dim kCtor(7) As Byte
    Dim names As *Byte

    LowStmtDimCtor = 0
    ast = ctx->ast
    nodes = ast->nodes
    tt = ast->types
    AstCopyStr(ast, idx, VarPtr(name))
    If nodes[idx].num <> TY_UDT Then
        Exit Function
    End If
    ti = nodes[idx].extra
    If ti < 0 Then Exit Function
    If TyIsClass(tt, ti) = 0 Then Exit Function
    j = ti * 48
    lstrcpy(VarPtr(kCtor), "Ctor")
    names = tt->typeNames
    LowMangleClass(VarPtr(names[j]), VarPtr(kCtor), VarPtr(name))
    lab = LowFindFunc(ctx, VarPtr(name))
    If lab < 0 Then
        Print "error: missing ctor '" + MakeStr(VarPtr(name)) + "'"
        ctx->err = 1
        Exit Function
    End If
    nArgs = 1
    argn = nodes[idx].right
    While argn >= 0
        If nodes[argn].kind <> AST_ARG Then Exit While
        nArgs = nArgs + 1
        argn = nodes[argn].nxt
    Wend
    If nodes[idx].right >= 0 Then
        If nodes[nodes[idx].right].kind <> AST_ARG Then
            nArgs = -1
        End If
    End If
    If nArgs <= 0 Then Exit Function
    stk = LowCallStk(nArgs)
    If stk > 0 Then
        IrEmit(ctx->list, OP_SUB_RSP, stk, 0)
    End If
    argi = 1
    argn = nodes[idx].right
    While argn >= 0 And argi < 16
        If nodes[argn].kind <> AST_ARG Then Exit While
        args[argi] = argn
        argi = argi + 1
        argn = nodes[argn].nxt
    Wend
    argi = 1
    While argi < nArgs
        If LowExprArg(ctx, nodes[args[argi]].left) = 0 Then Exit Function
        IrEmit(ctx->list, OP_STORE_RSP_RAX, argi * TyPtrSize(), 0)
        argi = argi + 1
    Wend
    AstCopyStr(ast, idx, VarPtr(fname))
    If LowLookupVar(ctx, VarPtr(fname), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) = 0 Then
        ctx->err = 1
        Exit Function
    End If
    LowEmitLeaOff(ctx->list, vOff, vGlob)
    IrEmit(ctx->list, OP_STORE_RSP_RAX, 0, 0)
    LowEmitLoadRegArgs(ctx->list, nArgs)
    IrEmit(ctx->list, OP_CALL_LAB, lab, 0)
    LowEmitCallFinish(ctx->list, stk)
    LowStmtDimCtor = 1
End Function

'''

DIM_NEW = r'''Function LowStmtDim(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim vOff As Long
    Dim vTy As Long
    Dim vTypeIdx As Long
    Dim vByRef As Long
    Dim vGlob As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte

    LowStmtDim = 0
    ast = ctx->ast
    nodes = ast->nodes
    If LowStmtDimCtor(ctx, idx) <> 0 Then
        LowStmtDim = 1
        Exit Function
    End If
    If ctx->err <> 0 Then Exit Function
    If nodes[idx].right >= 0 Then
        If LowExpr(ctx, nodes[idx].right) = 0 Then Exit Function
        AstCopyStr(ast, idx, VarPtr(name))
        If LowLookupVar(ctx, VarPtr(name), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) = 0 Then
            ctx->err = 1
            Exit Function
        End If
        If vTy = TY_SINGLE Then
            LowEmitCvtToSingleIfNeeded(ctx, nodes[idx].right)
        ElseIf vTy = TY_DOUBLE Then
            LowEmitCvtToDoubleIfNeeded(ctx, nodes[idx].right)
        Else
            LowEmitCvtToLongIfNeeded(ctx, nodes[idx].right, vTy)
        End If
        LowEmitStoreOff(ctx->list, vOff, vGlob)
    End If
    LowStmtDim = 1
End Function

'''

ASSIGN_INDEX = r'''Function LowStmtAssignIndex(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim vOff As Long
    Dim vTy As Long
    Dim vTypeIdx As Long
    Dim vByRef As Long
    Dim vGlob As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim leftK As Long
    Dim leftIdx As Long
    Dim tt As *TypeTable
    Dim foff As Long
    Dim fsz As Long
    Dim fcnt As Long
    Dim fieldTy As Long
    Dim ti As Long
    Dim fname(63) As Byte
    Dim base As Long
    Dim ix As Long

    LowStmtAssignIndex = 0
    ast = ctx->ast
    nodes = ast->nodes
    tt = ast->types
    leftIdx = nodes[idx].left
    leftK = nodes[leftIdx].kind
    If LowExpr(ctx, nodes[idx].right) = 0 Then Exit Function
    If leftK = AST_CALL Then
        AstCopyStr(ast, leftIdx, VarPtr(name))
        If LowLookupVar(ctx, VarPtr(name), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) <> 0 Then
            If vTy = TY_SINGLE_ARR Then
                LowEmitCvtToSingleIfNeeded(ctx, nodes[idx].right)
            ElseIf vTy = TY_DOUBLE_ARR Then
                LowEmitCvtToDoubleIfNeeded(ctx, nodes[idx].right)
            End If
        End If
    Else
        base = nodes[leftIdx].left
        If nodes[base].kind = AST_VAR Then
            AstCopyStr(ast, base, VarPtr(name))
            If LowLookupVar(ctx, VarPtr(name), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) <> 0 Then
                If vTy = TY_SINGLE_ARR Then
                    LowEmitCvtToSingleIfNeeded(ctx, nodes[idx].right)
                ElseIf vTy = TY_DOUBLE_ARR Then
                    LowEmitCvtToDoubleIfNeeded(ctx, nodes[idx].right)
                End If
            End If
        End If
    End If
    IrEmit(ctx->list, OP_PUSH_RAX, 0, 0)
    If LowAddr(ctx, nodes[idx].left) = 0 Then Exit Function
    IrEmit(ctx->list, OP_POP_RCX, 0, 0)
    If leftK = AST_CALL Then
        AstCopyStr(ast, leftIdx, VarPtr(name))
        If LowLookupVar(ctx, VarPtr(name), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) <> 0 Then
            If vTy = TY_STRING_ARR Or vTy = TY_DOUBLE_ARR Then
                IrEmit(ctx->list, OP_STORE_PTR, 0, 0)
            ElseIf vTy = TY_LONG_ARR Or vTy = TY_SINGLE_ARR Then
                LowStoreSized(ctx->list, 4)
            Else
                IrEmit(ctx->list, OP_STORE_BYTE_RAX_CL, 0, 0)
            End If
        Else
            IrEmit(ctx->list, OP_STORE_BYTE_RAX_CL, 0, 0)
        End If
    Else
        base = nodes[leftIdx].left
        If nodes[base].kind = AST_MEMBER Then
            AstCopyStr(ast, base, VarPtr(fname))
            ix = nodes[base].left
            If nodes[ix].kind = AST_INDEX Then
                AstCopyStr(ast, nodes[ix].left, VarPtr(name))
            ElseIf nodes[ix].kind = AST_VAR Then
                AstCopyStr(ast, ix, VarPtr(name))
            Else
                ctx->err = 1
                Exit Function
            End If
            If LowLookupVar(ctx, VarPtr(name), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) = 0 Then
                ctx->err = 1
                Exit Function
            End If
            ti = vTypeIdx
            If TyFindFieldEx(tt, ti, VarPtr(fname), foff, fsz, fcnt, fieldTy) = 0 Then
                ctx->err = 1
                Exit Function
            End If
            If fcnt > 1 Then
                LowStoreSized(ctx->list, fsz)
            ElseIf fsz = TyPtrSize() Then
                LowStoreSized(ctx->list, LowPtrFieldElemSize(fieldTy))
            Else
                ctx->err = 1
                Exit Function
            End If
        Else
            AstCopyStr(ast, base, VarPtr(name))
            If LowLookupVar(ctx, VarPtr(name), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) <> 0 Then
                If vTy = TY_STRING_ARR Or vTy = TY_DOUBLE_ARR Then
                    IrEmit(ctx->list, OP_STORE_PTR, 0, 0)
                ElseIf vTy = TY_LONG_ARR Or vTy = TY_SINGLE_ARR Then
                    LowStoreSized(ctx->list, 4)
                ElseIf vTy = TY_PTR_LONG Then
                    LowStoreSized(ctx->list, 4)
                Else
                    IrEmit(ctx->list, OP_STORE_BYTE_RAX_CL, 0, 0)
                End If
            Else
                IrEmit(ctx->list, OP_STORE_BYTE_RAX_CL, 0, 0)
            End If
        End If
    End If
    LowStmtAssignIndex = 1
End Function

'''

ASSIGN_MEMBER = r'''Function LowStmtAssignMember(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim vOff As Long
    Dim vTy As Long
    Dim vTypeIdx As Long
    Dim vByRef As Long
    Dim vGlob As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim leftIdx As Long
    Dim fsz As Long
    Dim base As Long

    LowStmtAssignMember = 0
    ast = ctx->ast
    nodes = ast->nodes
    leftIdx = nodes[idx].left
    If LowExpr(ctx, nodes[idx].right) = 0 Then Exit Function
    IrEmit(ctx->list, OP_PUSH_RAX, 0, 0)
    If LowAddr(ctx, nodes[idx].left) = 0 Then Exit Function
    IrEmit(ctx->list, OP_POP_RCX, 0, 0)
    fsz = LowMemberFieldSize(ctx, leftIdx)
    If fsz <= 0 Then
        AstCopyStr(ast, leftIdx, VarPtr(name))
        base = nodes[leftIdx].left
        If nodes[base].kind = AST_VAR Then
            AstCopyStr(ast, base, VarPtr(name))
            If LowLookupVar(ctx, VarPtr(name), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) <> 0 Then
                fsz = LowTyNbytes(vTy)
            End If
        End If
    End If
    If fsz <= 0 Then
        AstCopyStr(ast, leftIdx, VarPtr(name))
        Print "error: bad member field '" + MakeStr(VarPtr(name)) + "'"
        ctx->err = 1
        Exit Function
    End If
    LowStoreSized(ctx->list, fsz)
    LowStmtAssignMember = 1
End Function

'''

ASSIGN_VAR = r'''Function LowStmtAssignVar(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim vOff As Long
    Dim vTy As Long
    Dim vTypeIdx As Long
    Dim vByRef As Long
    Dim vGlob As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte

    LowStmtAssignVar = 0
    ast = ctx->ast
    nodes = ast->nodes
    If LowExpr(ctx, nodes[idx].right) = 0 Then Exit Function
    AstCopyStr(ast, nodes[idx].left, VarPtr(name))
    If LowLookupVar(ctx, VarPtr(name), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) = 0 Then
        Print "error: assign to undefined '" + MakeStr(VarPtr(name)) + "'"
        ctx->err = 1
        Exit Function
    End If
    If vTy = TY_SINGLE Then
        LowEmitCvtToSingleIfNeeded(ctx, nodes[idx].right)
    ElseIf vTy = TY_DOUBLE Then
        LowEmitCvtToDoubleIfNeeded(ctx, nodes[idx].right)
    Else
        LowEmitCvtToLongIfNeeded(ctx, nodes[idx].right, vTy)
    End If
    If vByRef <> 0 Then
        IrEmit(ctx->list, OP_PUSH_RAX, 0, 0)
        LowEmitLoadOff(ctx->list, vOff, vGlob)
        IrEmit(ctx->list, OP_POP_RCX, 0, 0)
        IrEmit(ctx->list, OP_STORE_PTR, 0, 0)
    ElseIf vTy = TY_STRING Then
        LowEmitStoreString(ctx, vOff, vGlob)
    Else
        LowEmitStoreOff(ctx->list, vOff, vGlob)
    End If
    LowStmtAssignVar = 1
End Function

'''

ASSIGN_NEW = r'''Function LowStmtAssign(ctx As *LowerCtx, idx As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim leftK As Long
    Dim leftIdx As Long

    LowStmtAssign = 0
    ast = ctx->ast
    nodes = ast->nodes
    leftIdx = nodes[idx].left
    leftK = nodes[leftIdx].kind
    If leftK = AST_INDEX Or leftK = AST_CALL Then
        LowStmtAssign = LowStmtAssignIndex(ctx, idx)
    ElseIf leftK = AST_MEMBER Then
        LowStmtAssign = LowStmtAssignMember(ctx, idx)
    ElseIf leftK = AST_VAR Then
        LowStmtAssign = LowStmtAssignVar(ctx, idx)
    Else
        ctx->err = 1
    End If
End Function

'''

FOR_STEP = r'''Function LowStmtForStep(ctx As *LowerCtx, idx As Long, vOff As Long, vGlob As Long, stepIdx As Long, useInc As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast

    LowStmtForStep = 0
    ast = ctx->ast
    nodes = ast->nodes
    If useInc <> 0 And vGlob = 0 Then
        IrEmit(ctx->list, OP_INC_LOCAL, vOff, 0)
    ElseIf useInc <> 0 Then
        LowEmitLoadOff(ctx->list, vOff, vGlob)
        IrEmit(ctx->list, OP_MOV_ECX, 1, 0)
        IrEmit(ctx->list, OP_ADD_EAX_ECX, 0, 0)
        LowEmitStoreOff(ctx->list, vOff, vGlob)
    ElseIf stepIdx >= 0 Then
        LowEmitLoadOff(ctx->list, vOff, vGlob)
        IrEmit(ctx->list, OP_PUSH_RAX, 0, 0)
        If LowExpr(ctx, stepIdx) = 0 Then Exit Function
        IrEmit(ctx->list, OP_POP_RCX, 0, 0)
        IrEmit(ctx->list, OP_ADD_EAX_ECX, 0, 0)
        LowEmitStoreOff(ctx->list, vOff, vGlob)
    Else
        If vGlob <> 0 Then
            LowEmitLoadOff(ctx->list, vOff, vGlob)
            IrEmit(ctx->list, OP_MOV_ECX, 1, 0)
            IrEmit(ctx->list, OP_ADD_EAX_ECX, 0, 0)
            LowEmitStoreOff(ctx->list, vOff, vGlob)
        Else
            IrEmit(ctx->list, OP_INC_LOCAL, vOff, 0)
        End If
    End If
    LowStmtForStep = 1
End Function

'''

FOR_NEW = r'''Function LowStmtFor(ctx As *LowerCtx, idx As Long) As Long
    Dim stackPad(2047) As Byte
    Dim vOff As Long
    Dim vTy As Long
    Dim vTypeIdx As Long
    Dim vByRef As Long
    Dim vGlob As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim name(63) As Byte
    Dim labEnd As Long
    Dim labTop As Long
    Dim body As Long
    Dim saveFor As Long
    Dim stepIdx As Long
    Dim labStepNeg As Long
    Dim labStepCont As Long
    Dim useInc As Long

    LowStmtFor = 0
    ast = ctx->ast
    nodes = ast->nodes
    If LowExpr(ctx, nodes[idx].right) = 0 Then Exit Function
    AstCopyStr(ast, nodes[idx].left, VarPtr(name))
    If LowLookupVar(ctx, VarPtr(name), VarPtr(vOff), VarPtr(vTy), VarPtr(vTypeIdx), VarPtr(vByRef), VarPtr(vGlob)) = 0 Then
        ctx->err = 1
        Exit Function
    End If
    LowEmitStoreOff(ctx->list, vOff, vGlob)
    labTop = LowNewLab(ctx)
    labEnd = LowNewLab(ctx)
    labStepNeg = LowNewLab(ctx)
    labStepCont = LowNewLab(ctx)
    saveFor = g_forEndLab
    g_forEndLab = labEnd
    stepIdx = nodes[idx].strId
    useInc = 0
    If stepIdx >= 0 Then
        If nodes[stepIdx].kind = AST_NUM Then
            If nodes[stepIdx].num = 1 Then
                useInc = 1
            End If
        End If
    End If
    IrEmit(ctx->list, OP_LABEL, labTop, 0)
    LowMaybeLoopStrCollect(ctx, nodes[idx].extra, nodes[idx].num, stepIdx)
    LowEmitLoadOff(ctx->list, vOff, vGlob)
    IrEmit(ctx->list, OP_PUSH_RAX, 0, 0)
    If LowExpr(ctx, nodes[idx].extra) = 0 Then Exit Function
    IrEmit(ctx->list, OP_MOV_EDX_EAX, 0, 0)
    IrEmit(ctx->list, OP_POP_RCX, 0, 0)
    If stepIdx >= 0 Then
        If LowExpr(ctx, stepIdx) = 0 Then Exit Function
        IrEmit(ctx->list, OP_TEST_EAX, 0, 0)
        IrEmit(ctx->list, OP_JL, labStepNeg, 0)
        IrEmit(ctx->list, OP_MOV_EAX_EDX, 0, 0)
        IrEmit(ctx->list, OP_CMP_ECX_EAX, 0, 0)
        IrEmit(ctx->list, OP_JG, labEnd, 0)
        IrEmit(ctx->list, OP_JMP, labStepCont, 0)
        IrEmit(ctx->list, OP_LABEL, labStepNeg, 0)
        IrEmit(ctx->list, OP_MOV_EAX_EDX, 0, 0)
        IrEmit(ctx->list, OP_CMP_ECX_EAX, 0, 0)
        IrEmit(ctx->list, OP_JL, labEnd, 0)
        IrEmit(ctx->list, OP_LABEL, labStepCont, 0)
    Else
        IrEmit(ctx->list, OP_MOV_EAX_EDX, 0, 0)
        IrEmit(ctx->list, OP_CMP_ECX_EAX, 0, 0)
        IrEmit(ctx->list, OP_JG, labEnd, 0)
    End If
    body = nodes[idx].num
    If LowStmtList(ctx, body) = 0 Then Exit Function
    If LowStmtForStep(ctx, idx, vOff, vGlob, stepIdx, useInc) = 0 Then Exit Function
    IrEmit(ctx->list, OP_JMP, labTop, 0)
    IrEmit(ctx->list, OP_LABEL, labEnd, 0)
    g_forEndLab = saveFor
    LowStmtFor = 1
End Function

'''

EXIT_HELPER = r'''Function LowStmtExit(ctx As *LowerCtx, idx As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim k As Long

    LowStmtExit = 0
    ast = ctx->ast
    nodes = ast->nodes
    k = nodes[idx].kind
    If k = AST_EXIT Then
        If LowExpr(ctx, nodes[idx].left) = 0 Then Exit Function
        LowEmitExitEax(ctx)
        LowStmtExit = 1
        Exit Function
    End If
    If k = AST_EXITDO Then
        If g_doEndLab < 0 Then
            ctx->err = 1
            Exit Function
        End If
        IrEmit(ctx->list, OP_JMP, g_doEndLab, 0)
        LowStmtExit = 1
        Exit Function
    End If
    If k = AST_EXITWHILE Then
        If g_whileEndLab < 0 Then
            ctx->err = 1
            Exit Function
        End If
        IrEmit(ctx->list, OP_JMP, g_whileEndLab, 0)
        LowStmtExit = 1
        Exit Function
    End If
    If k = AST_EXITFOR Then
        If g_forEndLab < 0 Then
            ctx->err = 1
            Exit Function
        End If
        IrEmit(ctx->list, OP_JMP, g_forEndLab, 0)
        LowStmtExit = 1
        Exit Function
    End If
    If k = AST_EXITFUNC Then
        If g_funcEndLab < 0 Then
            ctx->err = 1
            Exit Function
        End If
        IrEmit(ctx->list, OP_JMP, g_funcEndLab, 0)
        LowStmtExit = 1
        Exit Function
    End If
    If k = AST_END Then
        LowEmitExitImm(ctx, 0)
        LowStmtExit = 1
    End If
End Function

'''

HEAVY_NEW = r'''Function LowStmtHeavy(ctx As *LowerCtx, idx As Long) As Long
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
    If k = AST_EXIT Or k = AST_EXITDO Or k = AST_EXITWHILE Or k = AST_EXITFOR Or k = AST_EXITFUNC Or k = AST_END Then
        LowStmtHeavy = LowStmtExit(ctx, idx)
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


def replace_func(src, name, new_text):
    pat = re.compile(
        r'^Function\s+' + re.escape(name) + r'\b.*?\nEnd Function\n',
        re.M | re.S,
    )
    m = pat.search(src)
    if not m:
        raise SystemExit('missing function: ' + name)
    return src[:m.start()] + new_text + src[m.end():]


# Replace in order: Dim, Assign, For, Heavy; insert helpers before Dim
src = replace_func(src, 'LowStmtDim', DIM_CTOR + DIM_NEW)
src = replace_func(src, 'LowStmtAssign', ASSIGN_INDEX + ASSIGN_MEMBER + ASSIGN_VAR + ASSIGN_NEW)
src = replace_func(src, 'LowStmtFor', FOR_STEP + FOR_NEW)
src = replace_func(src, 'LowStmtHeavy', EXIT_HELPER + HEAVY_NEW)

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(src)

print('split2 OK')
