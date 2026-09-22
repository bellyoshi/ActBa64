# Split AstToIr into phase helpers.
path = r'c:\Users\bellm\source\repos\ActBa64\src\actba64\AstLower.abp'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    src = f.read()

start = src.find('Function AstToIr(ast As *Ast, list As *IrList, ByRef subsystemOut As Long) As Long')
if start < 0:
    raise SystemExit('AstToIr not found')
# end at last End Function of file for AstToIr - find matching
end = src.find('\nEnd Function\n', start)
# verify it's the AstToIr end by checking AstToIr = 1 before it
chunk = src[start:end+len('\nEnd Function\n')]
if 'AstToIr = 1' not in chunk:
    raise SystemExit('wrong End Function')

new = r'''Function AstToIrRegDecls(ctx As *LowerCtx, prog As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim stmt As Long
    Dim param As Long
    Dim nm(63) As Byte
    Dim apiBuf(63) As Byte
    Dim libBuf(63) As Byte
    Dim dllKind As Long
    Dim byRefBits As Long
    Dim bit As Long

    AstToIrRegDecls = 0
    ast = ctx->ast
    nodes = ast->nodes
    stmt = nodes[prog].left
    While stmt >= 0
        If nodes[stmt].kind = AST_DECLARE Then
            AstCopyStr(ast, stmt, VarPtr(nm))
            libBuf[0] = 0
            apiBuf[0] = 0
            If nodes[stmt].right >= 0 Then
                AstCopyStr(ast, nodes[stmt].right, VarPtr(libBuf))
            End If
            If nodes[stmt].extra >= 0 Then
                AstCopyStr(ast, nodes[stmt].extra, VarPtr(apiBuf))
            End If
            If apiBuf[0] = 0 Then
                AstCopyStr(ast, stmt, VarPtr(apiBuf))
            End If
            dllKind = LowDllKindFromLib(VarPtr(libBuf))
            If dllKind = 0 Then
                Print "error: unknown Declare Lib '" + MakeStr(VarPtr(libBuf)) + "' for '" + MakeStr(VarPtr(nm)) + "'"
                Exit Function
            End If
            byRefBits = 0
            bit = 1
            param = nodes[stmt].left
            While param >= 0
                If nodes[param].num <> 0 Then
                    byRefBits = byRefBits + bit
                End If
                bit = bit * 2
                param = nodes[param].nxt
            Wend
            If LowAddDecl(ctx, VarPtr(nm), VarPtr(apiBuf), dllKind, byRefBits) = 0 Then Exit Function
        End If
        stmt = nodes[stmt].nxt
    Wend
    AstToIrRegDecls = 1
End Function

Function AstToIrRegConsts(ctx As *LowerCtx, prog As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim stmt As Long
    Dim nm(63) As Byte
    Dim sConst(255) As Byte

    AstToIrRegConsts = 0
    ast = ctx->ast
    nodes = ast->nodes
    stmt = nodes[prog].left
    While stmt >= 0
        If nodes[stmt].kind = AST_CONST Then
            AstCopyStr(ast, stmt, VarPtr(nm))
            If nodes[stmt].extra <> 0 Then
                sConst[0] = 0
                If nodes[stmt].left >= 0 Then
                    AstCopyStr(ast, nodes[stmt].left, VarPtr(sConst))
                End If
                If LowAddStrConst(ctx, VarPtr(nm), VarPtr(sConst)) = 0 Then Exit Function
            Else
                If LowAddConst(ctx, VarPtr(nm), nodes[stmt].num) = 0 Then Exit Function
            End If
        End If
        stmt = nodes[stmt].nxt
    Wend
    AstToIrRegConsts = 1
End Function

Function AstToIrRegFuncs(ctx As *LowerCtx, prog As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim stmt As Long
    Dim param As Long
    Dim nm(63) As Byte
    Dim labFn As Long
    Dim byRefBits As Long
    Dim bit As Long

    AstToIrRegFuncs = 0
    ast = ctx->ast
    nodes = ast->nodes
    stmt = nodes[prog].left
    While stmt >= 0
        If nodes[stmt].kind = AST_FUNC Then
            labFn = LowNewLab(ctx)
            AstCopyStr(ast, stmt, VarPtr(nm))
            byRefBits = 0
            bit = 1
            param = nodes[stmt].left
            While param >= 0
                If nodes[param].num <> 0 Then
                    byRefBits = byRefBits + bit
                End If
                bit = bit * 2
                param = nodes[param].nxt
            Wend
            If LowAddFunc(ctx, VarPtr(nm), labFn, byRefBits) = 0 Then Exit Function
            ' extra は Parser が書いた戻り型のまま残す（lab は funcLabs）。
            ' extra を lab で上書きすると TY_STRING/TY_DOUBLE と衝突し、
            ' String 戻りが Double 変換されたり GC ルートから外れる。
        End If
        stmt = nodes[stmt].nxt
    Wend
    AstToIrRegFuncs = 1
End Function

Function AstToIrEmitFuncSetup(ctx As *LowerCtx, stmt As Long, retBuf As *Byte) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim param As Long
    Dim nm(63) As Byte
    Dim labFn As Long
    Dim frame As Long
    Dim pi As Long
    Dim j As Long
    Dim offs As *Long
    Dim ty As Long
    Dim nbytes As Long
    Dim ti As Long
    Dim nFlags As Long
    Dim isByRef As Long

    AstToIrEmitFuncSetup = -1
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    ctx->symCount = 0
    ctx->frameUsed = 0
    ctx->inFunc = 1
    g_doEndLab = -1
    g_whileEndLab = -1
    g_forEndLab = -1
    g_funcEndLab = -1
    LowResetFnPreciseRoots()
    nFlags = nodes[stmt].num
    If nFlags >= 256 Then
        retBuf[0] = 0
    Else
        AstCopyStr(ast, stmt, retBuf)
    End If
    param = nodes[stmt].left
    While param >= 0
        AstCopyStr(ast, param, VarPtr(nm))
        isByRef = nodes[param].num
        ty = nodes[param].extra
        If ty < 0 Then ty = TY_LONG
        ti = nodes[param].right
        nbytes = TyPtrSize()
        If LowAddSym(ctx, VarPtr(nm), ty, nbytes, ti, isByRef) < 0 Then Exit Function
        param = nodes[param].nxt
    Wend
    If retBuf[0] <> 0 Then
        ty = nodes[stmt].extra
        If ty <> TY_STRING Then
            If ty <> TY_DOUBLE Then
                ty = TY_LONG
            End If
        End If
        If LowAddSym(ctx, retBuf, ty, 8, -1, 0) < 0 Then Exit Function
    End If
    ' locals: all Dims in body including nested If/Select/loops
    If LowCollectDimsInList(ctx, nodes[stmt].right, 0) = 0 Then Exit Function
    frame = LowAlign16(ctx->frameUsed + &H28 + &H2000)
    If frame < &H28 Then frame = &H28
    g_funcEndLab = LowNewLab(ctx)
    AstCopyStr(ast, stmt, VarPtr(nm))
    labFn = LowFindFunc(ctx, VarPtr(nm))
    If labFn < 0 Then
        Print "error: missing function label '" + MakeStr(VarPtr(nm)) + "'"
        Exit Function
    End If
    IrEmit(list, OP_LABEL, labFn, 0)
    IrEmit(list, OP_ENTER, frame, 0)
    offs = ctx->offs
    pi = 0
    param = nodes[stmt].left
    While param >= 0
        If TyIs32() <> 0 Then
            offs[pi] = 8 + pi * 4
        ElseIf pi = 0 Then
            IrEmit(list, OP_STORE_LOCAL_ECX, offs[pi], 0)
        ElseIf pi = 1 Then
            IrEmit(list, OP_STORE_LOCAL_EDX, offs[pi], 0)
        ElseIf pi = 2 Then
            IrEmit(list, OP_STORE_LOCAL_R8, offs[pi], 0)
        ElseIf pi = 3 Then
            IrEmit(list, OP_STORE_LOCAL_R9, offs[pi], 0)
        Else
            ' stack arg already at [rbp+0x30+(pi-4)*8]
            ' LowAddSym が付けた precise root を実オフセットへ付け替える
            LowRetargetFnPreciseRoot(offs[pi], 48 + (pi - 4) * 8)
            offs[pi] = 48 + (pi - 4) * 8
        End If
        ' Long 引数をここで ZX してはいけない。BytePtr / HWND / VoidPtr
        ' は ParseEatLongAlias で TY_LONG になっており、ヒープの StrPtr
        ' を 32bit に切ると D3DCompile 等が AV する。添字は LowAddr 側で ZX。
        pi = pi + 1
        param = nodes[param].nxt
    Wend
    nFlags = pi
    ' 非引数ローカル（戻り値スロット含む）を 0 初期化。
    ' String を未初期化のまま StoreString→StrFree するとスタックゴミを
    ' HeapFree して AV するため必須。
    j = pi
    While j < ctx->symCount
        IrEmit(list, OP_MOV_EAX_IMM, 0, 0)
        IrEmit(list, OP_STORE_LOCAL, offs[j], 0)
        j = j + 1
    Wend
    AstToIrEmitFuncSetup = nFlags
End Function

Function AstToIrEmitFuncFinish(ctx As *LowerCtx, stmt As Long, retBuf As *Byte, nFlags As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim nm(63) As Byte
    Dim offs As *Long
    Dim pi As Long

    AstToIrEmitFuncFinish = 0
    ast = ctx->ast
    list = ctx->list
    nodes = ast->nodes
    offs = ctx->offs
    If LowStmtList(ctx, nodes[stmt].right) = 0 Or ctx->err <> 0 Then
        AstCopyStr(ast, stmt, VarPtr(nm))
        Print "error: codegen in function '" + MakeStr(VarPtr(nm)) + "'"
        Exit Function
    End If
    IrEmit(list, OP_LABEL, g_funcEndLab, 0)
    LowEmitLocalClassDtors(ctx)
    ' エピローグでは Collect しない。入れ子の Mid$ / Lower$ 終了時に
    ' 呼び出し元の String が conservative 漏れで解放されるのを防ぐ。
    If retBuf[0] <> 0 Then
        pi = LowFindSym(ctx, retBuf)
        If pi < 0 Then Exit Function
        IrEmit(list, OP_LOAD_LOCAL, offs[pi], 0)
    End If
    LowEmitLeaveN(list, nFlags)
    ctx->inFunc = 0
    g_funcEndLab = -1
    retBuf[0] = 0
    AstToIrEmitFuncFinish = 1
End Function

Function AstToIrEmitFuncs(ctx As *LowerCtx, prog As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim stmt As Long
    Dim retBuf(63) As Byte
    Dim nFlags As Long

    AstToIrEmitFuncs = 0
    ast = ctx->ast
    nodes = ast->nodes
    stmt = nodes[prog].left
    While stmt >= 0
        If nodes[stmt].kind = AST_FUNC Then
            nFlags = AstToIrEmitFuncSetup(ctx, stmt, VarPtr(retBuf))
            If nFlags < 0 Then Exit Function
            If AstToIrEmitFuncFinish(ctx, stmt, VarPtr(retBuf), nFlags) = 0 Then Exit Function
        End If
        stmt = nodes[stmt].nxt
    Wend
    AstToIrEmitFuncs = 1
End Function

Function AstToIrEmitMain(ctx As *LowerCtx, prog As Long, labMain As Long) As Long
    Dim nodes As *AstNode
    Dim ast As *Ast
    Dim list As *IrList
    Dim stmt As Long
    Dim frame As Long

    AstToIrEmitMain = 0
    list = ctx->list
    ast = ctx->ast
    nodes = ast->nodes
    ' main: module Dims are globals; frame only needs temps (16-byte aligned)
    ctx->symCount = 0
    ctx->frameUsed = 0
    frame = LowAlign16(&H28)

    IrEmit(list, OP_LABEL, labMain, 0)
    IrEmit(list, OP_ENTER, frame, 0)
    LowEmitGcPreciseRootsInit(ctx)

    stmt = nodes[prog].left
    While stmt >= 0
        If nodes[stmt].kind <> AST_FUNC And nodes[stmt].kind <> AST_CONST And nodes[stmt].kind <> AST_TYPE Then
            If LowStmt(ctx, stmt) = 0 Or ctx->err <> 0 Then
                Print "error: codegen in module stmt kind " + Str$(nodes[stmt].kind)
                Exit Function
            End If
        End If
        stmt = nodes[stmt].nxt
    Wend

    LowEmitGlobalClassDtors(ctx)
    LowEmitStrCollectSafepoint(ctx)
    LowEmitExitImm(ctx, 0)
    IrEmit(list, OP_LEAVE, 0, 0)
    AstToIrEmitMain = 1
End Function

Sub AstToIrEmitRt(ctx As *LowerCtx)
    LowEmitRtCatBody(ctx)
    LowEmitRtMidBody(ctx)
    LowEmitRtStrBody(ctx)
    LowEmitRtPrintBody(ctx)
    LowEmitRtInputBody(ctx)
    LowEmitRtValBody(ctx)
    LowEmitRtValMilliBody(ctx)
    LowEmitRtMilliToSingleBody(ctx)
    LowEmitRtMilliToDoubleBody(ctx)
    LowEmitRtMakeStrBody(ctx)
    LowEmitRtStrCmpBody(ctx)
    LowEmitRtStrFreeBody(ctx)
    LowEmitRtStrHeapAllocBody(ctx)
    LowEmitRtStrGcPreciseBody(ctx)
    LowEmitRtStrGcConsBody(ctx)
    LowEmitRtStrCollectBody(ctx)
End Sub

Function AstToIr(ast As *Ast, list As *IrList, ByRef subsystemOut As Long) As Long
    Dim ctx As LowerCtx
    Dim nodes As *AstNode
    Dim prog As Long
    Dim namesBuf As *Byte
    Dim offsBuf As *Long
    Dim typesBuf As *Long
    Dim typeIdxsBuf As *Long
    Dim byRefsBuf As *Long
    Dim gNamesBuf As *Byte
    Dim gOffsBuf As *Long
    Dim gTypesBuf As *Long
    Dim gTypeIdxsBuf As *Long
    Dim funcNamesBuf As *Byte
    Dim funcLabsBuf As *Long
    Dim funcByRefsBuf As *Long
    Dim constNamesBuf As *Byte
    Dim constValsBuf As *Long
    Dim constStrNamesBuf As *Byte
    Dim constStrValsBuf As *Byte
    Dim declNamesBuf As *Byte
    Dim declApiNamesBuf As *Byte
    Dim declDllsBuf As *Byte
    Dim declByRefsBuf As *Byte
    Dim labMain As Long
    Dim tt As *TypeTable

    AstToIr = 0
    subsystemOut = IMAGE_SUBSYSTEM_WINDOWS_CUI
    If ast->root < 0 Then Exit Function
    nodes = ast->nodes
    prog = ast->root
    If nodes[prog].kind <> AST_PROGRAM Then Exit Function
    tt = ast->types

    namesBuf = calloc(BytesN(DYN_INIT, SYM_NAME_LEN))
    offsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    typesBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    typeIdxsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    byRefsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    gNamesBuf = calloc(BytesN(DYN_INIT, SYM_NAME_LEN))
    gOffsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    gTypesBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    gTypeIdxsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    funcNamesBuf = calloc(BytesN(DYN_INIT, SYM_NAME_LEN))
    funcLabsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    funcByRefsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    constNamesBuf = calloc(BytesN(DYN_INIT, SYM_NAME_LEN))
    constValsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    constStrNamesBuf = calloc(BytesN(DYN_INIT, SYM_NAME_LEN))
    constStrValsBuf = calloc(BytesN(DYN_INIT, AST_STR_LEN))
    declNamesBuf = calloc(BytesN(DYN_INIT, SYM_NAME_LEN))
    declApiNamesBuf = calloc(BytesN(DYN_INIT, SYM_NAME_LEN))
    declDllsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    declByRefsBuf = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    g_preciseRoots = calloc(BytesN(GC_MAX_PRECISE, SizeOf(Long)))
    g_fnPreciseRoots = calloc(BytesN(GC_MAX_PRECISE, SizeOf(Long)))
    g_gNbytes = calloc(BytesN(DYN_INIT, SizeOf(Long)))
    g_fb0 = namesBuf
    g_fb1 = offsBuf
    g_fb2 = typesBuf
    g_fb3 = typeIdxsBuf
    g_fb4 = byRefsBuf
    g_fb5 = gNamesBuf
    g_fb6 = gOffsBuf
    g_fb7 = gTypesBuf
    g_fb8 = gTypeIdxsBuf
    g_fb9 = funcNamesBuf
    g_fb10 = funcLabsBuf
    g_fb11 = funcByRefsBuf
    g_fb12 = constNamesBuf
    g_fb13 = constValsBuf
    g_fb14 = constStrNamesBuf
    g_fb15 = constStrValsBuf
    g_fb16 = declNamesBuf
    g_fb17 = declApiNamesBuf
    g_fb18 = declDllsBuf
    g_fb19 = declByRefsBuf
    If namesBuf = NULL Or offsBuf = NULL Or typesBuf = NULL Or typeIdxsBuf = NULL Or byRefsBuf = NULL Or gNamesBuf = NULL Or gOffsBuf = NULL Or gTypesBuf = NULL Or gTypeIdxsBuf = NULL Or funcNamesBuf = NULL Or funcLabsBuf = NULL Or funcByRefsBuf = NULL Or constNamesBuf = NULL Or constValsBuf = NULL Or constStrNamesBuf = NULL Or constStrValsBuf = NULL Or declNamesBuf = NULL Or declApiNamesBuf = NULL Or declDllsBuf = NULL Or declByRefsBuf = NULL Then
        LowFreeAstBufs()
        Exit Function
    End If
    If g_preciseRoots = NULL Or g_fnPreciseRoots = NULL Or g_gNbytes = NULL Then
        LowFreeAstBufs()
        Exit Function
    End If

    g_symCap = DYN_INIT
    g_gCap = DYN_INIT
    g_funcCap = DYN_INIT
    g_constCap = DYN_INIT
    g_constStrCap = DYN_INIT
    g_declCap = DYN_INIT
    g_gNames = gNamesBuf
    g_gOffs = gOffsBuf
    g_gTypes = gTypesBuf
    g_gTypeIdxs = gTypeIdxsBuf
    g_gCount = 0
    g_gSize = 0

    ctx.list = list
    ctx.ast = ast
    ctx.symCount = 0
    ctx.nextLab = 0
    ctx.err = 0
    ctx.names = namesBuf
    ctx.offs = offsBuf
    ctx.types = typesBuf
    ctx.typeIdxs = typeIdxsBuf
    ctx.byRefs = byRefsBuf
    ctx.frameUsed = 0
    ctx.inFunc = 0
    ctx.funcNames = funcNamesBuf
    ctx.funcLabs = funcLabsBuf
    ctx.funcByRefs = funcByRefsBuf
    ctx.funcCount = 0
    ctx.constNames = constNamesBuf
    ctx.constVals = constValsBuf
    ctx.constCount = 0
    ctx.constStrNames = constStrNamesBuf
    ctx.constStrVals = constStrValsBuf
    ctx.constStrCount = 0
    ctx.declNames = declNamesBuf
    ctx.declApiNames = declApiNamesBuf
    ctx.declDlls = declDllsBuf
    ctx.declByRefs = declByRefsBuf
    ctx.declCount = 0
    g_doEndLab = -1
    g_whileEndLab = -1
    g_forEndLab = -1
    g_funcEndLab = -1
    g_rtCatLab = -1
    g_rtMidLab = -1
    g_rtStrLab = -1
    g_rtPrintLab = -1
    g_rtInputLab = -1
    g_rtValLab = -1
    g_rtValMilliLab = -1
    g_rtMilliToSingleLab = -1
    g_rtMilliToDoubleLab = -1
    g_rtMakeStrLab = -1
    g_rtStrCmpLab = -1
    g_rtStrFreeLab = -1
    g_rtStrHeapAllocLab = -1
    g_rtStrGcPreciseLab = -1
    g_rtStrGcConsLab = -1
    g_rtStrCollectLab = -1
    g_gcBaseOff = 0
    g_preciseRootCount = 0
    g_fnPreciseRootCount = 0
    list->globSize = 0

    ' #USEWINDOW による GUI サブシステム切り替えは CompileSource 側で行う
    If AstToIrRegDecls(VarPtr(ctx), prog) = 0 Then
        LowFreeAstBufs()
        Exit Function
    End If
    If AstToIrRegConsts(VarPtr(ctx), prog) = 0 Then
        LowFreeAstBufs()
        Exit Function
    End If
    If AstToIrRegFuncs(VarPtr(ctx), prog) = 0 Then
        LowFreeAstBufs()
        Exit Function
    End If

    ' module-level Dim -> globals (before any function emit; nested Dims in main too)
    If LowCollectDimsInList(VarPtr(ctx), nodes[prog].left, 1) = 0 Then
        LowFreeAstBufs()
        Exit Function
    End If
    LowCollectPreciseGlobRoots()
    g_gcBaseOff = g_gSize
    g_gSize = g_gSize + GC_REGION_SIZE
    list->globSize = g_gSize

    labMain = LowNewLab(VarPtr(ctx))
    IrEmit(list, OP_JMP, labMain, 0)

    If AstToIrEmitFuncs(VarPtr(ctx), prog) = 0 Then
        LowFreeAstBufs()
        Exit Function
    End If
    If AstToIrEmitMain(VarPtr(ctx), prog, labMain) = 0 Then
        LowFreeAstBufs()
        Exit Function
    End If
    AstToIrEmitRt(VarPtr(ctx))

    LowFreeAstBufs()
    g_gNames = NULL
    g_gOffs = NULL
    g_gTypes = NULL
    g_gTypeIdxs = NULL
    g_gCount = 0
    g_gSize = 0
    AstToIr = 1
End Function
'''

# AstToIr itself may still be >100 due to alloc init. Extract AstToIrAlloc if needed after.
with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(src[:start] + new + '\n')
print('AstToIr split written')
