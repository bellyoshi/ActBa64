# ビルド手順

ActBa64 は **1 本のコンパイラ** `actba64.exe` です。Lexer → Parser → AST → IR まで共通で、機械語と PE だけ分岐します。既定は PE32+ / AMD64、`-actba32` で PE32 / i386 を出します（中間 `.asm` / `.obj` は出さない）。

ブートストラップ:

1. **stage0** — 人が ActiveBasic 4.20 で `actba64.pj` をビルド（32bit **ホスト**。`#PLATFORM=32` は AB4.20 用で、出力ターゲットではない）
2. **stage1 / stage2** — そのコンパイラが自分自身を 64bit ホストとしてビルド（`-actba32` なし）

前提 OS: Windows（PowerShell）

リポジトリ根の `.\release_build.ps1` が上記に加えて ProjectEditor を組み、`release\` へ配布一式をコピーする。標準ヘッダは [`src/Include`](../src/Include) の 1 本。

---

## 1. stage0（手動・AB4.20）

作業ディレクトリ: `src\actba64`

ActiveBasic 4.20 で `actba64.pj` をビルドし、`bin\stage0\actba64.exe` に置く（`.pj` の `#OUTPUT_RELEASE` も同じパス）。`bin\stage0` フォルダは先に作ること。

`#PLATFORM=32` は **AB4.20 が 32bit exe を出すため** だけ。コンパイル対象の切替には使わない（対象は CLI の `-actba32`）。

**注意:** AB4.20 は式の加算・乗算を 16bit 化することがある。古い stage0 では次が壊れる。

- `SizeOfImage` が小さくなり、OS が `%1 is not a valid Win32 application` で拒否する
- DLL のエクスポート RVA が切れる（例: `0x1000 + 0x11811` → `0x2811`）。呼び出しは終了コード `0xC000001D`（不正命令）になる
- `-actba32` の絶対アドレス（ラベル、グローバル、文字列、IAT）が連鎖加算のままだと同じ切り捨てになる
- DLL の `.reloc`（ページ RVA とセクション配置）が切れると、優先ベースが塞がったときにロードへ失敗する

現行ソースは `AlignUp`、`PeCalcLayout`、`CgSnapRva`、`CgAbs32Add`、`PeRelocRva` を DWord の段階代入にしてある。**stage0 を作り直すときはこのツリーで** AB4.20 ビルドすること。`build.ps1` は不正 PE を検知して stage3 等へフォールバックする。

---

## 2. actba64 自己ホスト

作業ディレクトリ: `src\actba64`

**前提:** `bin\stage0\actba64.exe` があること。

| ステージ | 内容 |
|---|---|
| stage0 | AB4.20 で作った 32bit ホスト `actba64.exe` |
| stage1 | stage0 が `actba64.pj` を **64bit** でビルド |
| stage2 | stage1 で自己コンパイル |
| 比較 | stage1 と stage2 の SHA256 一致 |

```powershell
cd src\actba64
.\build.ps1                 # Include を stage0/1/2 へコピー + 全段階 + 比較
.\build.ps1 -SkipCopy       # Include コピーをスキップ
.\build.ps1 -Stage1Only     # stage1 まで
.\build.ps1 -SkipStage1     # 既存 stage1 を使い stage2 のみ
.\build.ps1 -SkipCompare    # バイナリ比較をスキップ
```

成功時の主成果物: `bin\stage2\actba64.exe`

### Include の置き場所

正本は常に [`src/Include`](../src/Include)。`build.ps1` は（`-SkipCopy` でなければ）**`bin\stage0` / `stage1` / `stage2` の各 `Include\` へ同じ内容をコピー**する。exe 隣が検索の最優先なので、回帰テストや自己ホストでパス解決に依存しない。

コンパイラは `Include\...` を次の順で探す（`PreprocPj`）:

1. exe と同じディレクトリ（例: `bin\stage1\Include\`）
2. その親〜3 階層上（`bin\stageN\` からは `src\Include\` に到達）
3. カレントディレクトリの `Include\`

配布の `release\Include` も正本のコピー（ルート `release_build.ps1`）。

### コンパイラソースの分割

長大だった Parser / AstLower / Preproc は関数境界で分割している。行数の目標・上限は [coding.md](./coding.md)（ファイル **目標 400 / 上限 1000**、関数 **10 行以内**）。

`actba64.pj` の `#SOURCE`（および単体ホスト用 `actba64.idx`）で複数 `.abp` を結合する。

| 接頭辞 | 役割 | 主なファイル（例。正本は `actba64.pj` の `#SOURCE`） |
|---|---|---|
| `Parser*` | トークン → AST | `Parser` / `ParserExpr` / `ParserFactor` / `ParserNew` / `ParserCmd` / `ParserStmtIO` / `ParserFileStmt` / `ParserN88*`（`-pN88` は `LexerN88` + `ParserN88Prog*`） / `ParserDim` / `ParserClass*` / `ParserCtrl` / `ParserSelect` / `ParserProc` / `ParserDriver` ほか |
| `AstLower*` | AST → IR（`AstToIr`） | `AstLower` / `AstLowerApi` / `AstLowerRt*` / `AstLowerAddr` / `AstLowerExpr*` / `AstLowerPrint` / `AstLowerStmt*` / `AstLowerNew` / `AstLowerFileStmt` / `AstLowerDriver` ほか |
| `Preproc*` | `#include` / `.pj` 結合 | `Preproc` / `PreprocInc` / `PreprocCond` / `PreprocPj` / `PreprocPjSrc` / `PreprocRes` ほか |

`#SOURCE` の順序どおりに連結されるため、分割ファイル間で共有の `Type` / `Dim` / 手続きを参照できる。
使い方:

```text
actba64 <src.abp|.pj> [-actba32] [-pN88] [-o <out>]
```

`-pN88` は N88-BASIC のソースを読む（行番号は省略可）（[language.md §1.7](./language.md#17-n88-basic-構文-pn88)）。

`.pj` の `#OUTPUT_RELEASE` は `-o` が無いときに使う（パスは `.pj` ディレクトリ基準）。DLL は `#MODULETYPE=1` で、再配置は `PeReloc.abp` が `.reloc` に書く（[language.md §8.4](./language.md#84-dll-を出力する)）。

サンプル:

```powershell
.\bin\stage2\actba64.exe .\samples\n88_shapes.abp -o .\samples\n88_shapes.exe
.\bin\stage2\actba64.exe .\samples\math_test.abp -o .\samples\math_test.exe

# 32bit PE
.\bin\stage2\actba64.exe hello.abp -actba32 -o hello32.exe
```

### 統合テスト

`src/actba64/test`（`src\actba64` からは `test\`）は統合テストである。`' Target: actba64` 付き `.abp` / `.pj` をコンパイルして実行する。既定 64bit と `-Actba32` の両方で回せる。

ユニットテストは `src/unittest` に置く。将来はプロジェクト全体を覆う。今は `bool` と `ByteCharUtils` の `IsLower` である。`run_test2.ps1` の対象ではない。

リポジトリ根の `check.ps1` が入口である。

- **git commit の前**は必ず `.\check.ps1 unit`（引数なしも同じ）。失敗したらコミットしない。振る舞いを変えたら、コミットしなくてもユニットテストを回す。
- **git push の前**は `.\check.ps1 integration`（下の `run_test2.ps1`、既定 stage1）。失敗したら push しない。

```powershell
.\run_test2.ps1                 # bin\stage1\actba64.exe（既定・64bit）
.\run_test2.ps1 stage0          # ブートストラップ起点（AB4.20 手動ビルド）の確認
.\run_test2.ps1 stage2
.\run_test2.ps1 stage2 -Actba32 # 同じテストを PE32 で
.\run_test2.ps1 -Rebuild
.\run_test2.ps1 -IncludeGui     # GUI 系も実行（下記。既定はスキップ）
.\run_test2.ps1 -KeepArtifacts
.\run_test2.ps1 -ShowSkipped    # SKIP 行も表示
```

| メタ | 意味 |
|---|---|
| `' Target: actba64` | このランナーの対象（必須） |
| `' Expect: N` | 終了コード期待値（省略時 0） |
| `' CompileFail: 1` | コンパイル失敗が期待。隣接 `test/<name>.err.txt` の各行が出力に含まれること（部分一致） |
| `' ExpectErrors: N` | `CompileFail` 時の診断件数下限（省略時 1） |
| `' Gui: 1` | 対話 UI 想定。**既定は SKIP**（`-IncludeGui` で実行） |
| `' Skip32: 1` | `-Actba32` 時はスキップ（ポインタ幅依存など） |
| `' Prebuild: file.pj` | 本体の前にその `.pj` をコンパイルし、成果物をテスト exe と同じディレクトリへ置く（DLL 名は `.pj` のベース名 + `.dll`） |

### コンパイル診断（複数エラー）

形式: `error: <file>(<line>): <message>` / `warning: <file>(<line>): <message>`（英語）。パースは文単位で続行し、意味解析も可能な限り複数報告する。エラー時は末尾 `error: N error(s)`。警告のみならコンパイル成功しつつ `warning: N warning(s)`。パースで 1 件でも失敗したらコード生成は行わない。`#strict` は変数同士の代入型不一致を warning（`As` で抑制）。

異常系の例: `test/t_err_then.abp`（`Then` 欠落）、`t_err_end_if.abp`、`t_err_undef.abp`、`t_err_multi_*.abp`。

**GUI の自動判定**（`' Gui: 1` が無くても GUI 扱い → 既定 SKIP）:

- `#USEWINDOW=1`
- ファイル名が `_pe_gui` で始まる（例: `_pe_gui5.abp`）

`-IncludeGui` 時は、一定時間プロセスが生きていれば PASS（メッセージループ型）。すぐ終了すれば `Expect` と比較する。

**その他のスキップ**（Summary 直後に内訳）:

| 理由 | 内容 |
|---|---|
| no Target | `' Target: actba64` が無い旧手動テスト |
| pj-covered | `.pj` の `#SOURCE` に含まれる `.abp`（プロジェクト側で実行） |
| gui | 上記 GUI（`-IncludeGui` で有効） |
| skip32 | `-Actba32` 時の `Skip32: 1`（ポインタ幅依存など） |

`SizeOf(UDT)` やポインタ幅に依存する期待値は、64bit 決め打ちせず `SizeOf(*Byte)` 相当（例: ポインタ用ダミー Type）や `' Skip32: 1` で扱う。

### Linux（`-linux`）

`actba64 src.abp -linux -o out` は x86-64 Linux の静的 ELF（libc なし）を出す（Lib が `.so` の Declare があるときだけ動的リンク、下記）。コードは PE32+ と同じ Win64 規約のまま、配置も同じ RVA を `0x400000` に置く（`ElfHdr` / `ElfWriter`）。

- **API スロット**（`LinuxRt`）: 呼び出しは Windows と同じ `call [rip+IAT]`。スロットには `Include\linux` の BASIC 関数 `Lx_<API名>`（例: `Lx_WriteFile`）の絶対アドレスを書く。無い API は `unsupported API: 名前` を stderr に出して終了コード 127
- **スタブ**（`LinuxStub`）: `_start`（rsp を保存し `jmp main` を call）、`Lx_Syscall(番号, a1..a6)`、`Lx_StackBase()`。GC のスタック底は `gs:[8]` の代わりに保存した rsp
- `#ifdef _LINUX` が使える。`Print` の行末は LF。内部の UTF-8 をそのまま書く
- 今あるのは標準入出力（`Print`、`Input`）・終了・メモリ／C 文字列・ヒープ・ファイル（`Open` / `Print #` / `Write #` / `Input #` / `Get` / `Put`、`Kill` / `MkDir` / `ChDir`）・時刻（`Date$` / `Time$` は今は UTC）・`Sleep`・`GetCommandLine` / `GetModuleFileName`・`lstrcat`・`GetFullPathName`・子プロセス（`CreateProcess` / `WaitForSingleObject` / `GetExitCodeProcess`、`LxProc`）
- ファイルの API（`LxFile`）はパスの `\` を `/` として扱う（コンパイラが `"Include\"` のように組み立てるため）。`CreateProcess` はコマンドラインを空白で分け（`""` の中は 1 つ）、先頭のプログラムだけ `\` を `/` にして fork + execve。ハンドルは pid + `LX_PROC_BIAS`
- ファイルの行末も LF（`BaFileWriteNl`）。パスは UTF-8 のまま A 版の代わりへ渡す（`BasicPathWide` は `-linux` で 0）
- `Include\linux` では `*VoidPtr` / `*Word` の添字と `VoidPtr` の配列を使わない（どれも 4 バイト刻みになる）。8 バイト・2 バイトは `LxGetQ` / `LxSetQ` / `LxSetW` で読み書きする。`VoidPtr` を返す関数の呼び出しに式を足すと（`Lx_StackBase() + n * 8`）32bit に切れるので、いったん局所変数に入れてから足す
- **呼ばれない関数を消す**（`LinuxPrune`、`-linux` だけ）: IR を関数（`OP_LABEL` の直後が `OP_ENTER`）に分け、先頭（`jmp main`）から分岐・`OP_CALL_LAB`・`OP_LEA_RAX_LAB`（`AddressOf` / `Virtual`）・次の関数への落ち込み・API の Lx_ 版をたどる。届かない関数は `OP_NOP` にするので、コードも API の取り込みも文字列も出ない（Hello World は 212KB → 29KB）
- **警告**（`LinuxCheck`）: 残った呼び出しのうち Linux 版の無い API は `warning: file(行): 'MessageBeep' has no Linux version; …` を出す。行は呼んだ文（`OP_CALL_API` の `arg2`）。実行時ルーチンの中なら `warning: (runtime): …`
- 実際には通らないが静的には届く Windows 専用の呼び出し（`BasicPath` の W 版、`Sleep` のメッセージ処理など）は `#ifndef _LINUX` で外す
- `MultiByteToWideChar` / `WideCharToMultiByte`（`LxUnicode`）: コードページは何でも UTF-8 として扱う（Linux に CP932 は無い）
- ELF のファイルでは `.idata` を `.text` の直後のページに置く（`.data` の 0 はファイルに持たない）
- **共有ライブラリ**（`ElfDyn` / `LinuxDyn` / `LinuxThunk`）: `Declare Function strlen Lib "libc.so.6" (s As BytePtr) As Long` のように Lib が `xxx.so` / `xxx.so.N` なら、その ELF は動的リンクになる（`PT_INTERP` = `/lib64/ld-linux-x86-64.so.2`、`PT_DYNAMIC`、`DT_NEEDED`、`R_X86_64_GLOB_DAT`）。ブロブは `.idata` の後ろのページ、GOT はその DLL の ILT（Linux では使わない）。`.so` が無ければ今までどおり静的
  - IAT スロットは取り込みごとの踏み台を指す。踏み台は `[rsp+8+8i]` の引数を SysV 規約に並べ替える（整数 → rdi, rsi, rdx, rcx, r8, r9、ByVal の `Double` / `Single` → xmm0..7、残りはスタック、`al` = xmm の数なので `printf` のような可変長引数も呼べる）。rsi / rdi は踏み台が保存する
  - 取り込みの名前は Declare の名前、シンボル名は Alias（同じ関数を型の違う Declare で呼べる）。Declare の `Double` / `Single` の仮引数へは呼び出し側でその型に変換する（Windows でも同じ）
  - 未対応: 戻り値の `Double`（Declare の戻り値の型は読み捨てている）、構造体の値渡し、`.so` から BASIC へのコールバック（`qsort` など）。`ExitProcess` は exit_group なので libc の `stdio` はバッファが残る（`puts` などを使うなら `fflush(0)` を呼ぶ）
  - 名前が実行時ルーチンと同じ（`rand` など）だとそちらが呼ばれるので、Alias で別の名前にする
- テストのメタ（`run_test_linux.ps1` だけ）: `' Args: …` 実行時の引数、`' Warn: N` 警告の数（省略時 0）、`' WarnAt: file(行)` 警告の場所、`' MaxSize: N` ELF の上限バイト数
- **ヒープ**（`LxHeap`）: `HeapAlloc` などは mmap した 4MB の領域から 16<<k バイトの区分で切り出し、区分ごとの空きリストで使い回す。1MB を超えるものは 1 つずつ mmap / munmap

```powershell
.\run_test_linux.ps1            # test\linux\*.abp を -linux でビルドし WSL で実行（WSL が無ければ SKIP）
.\run_test_linux.ps1 stage2
```

終了コードは `' Expect: N`、標準出力・標準エラーは隣の `<name>.out.txt` / `<name>.stderr.txt` とバイト単位で比べる。`check.ps1 integration` は `run_test2.ps1` の後にこれも回す。

#### Linux でのセルフホスト

`actba64.pj` と `src\rc\rc.pj` を `-linux` で作れば、Linux で動くコンパイラと rc になる（隣に `Include` を置く。`.rc` の `#resource` は隣の `rc` を起動する）。Linux 版のコンパイラは Windows 版と同じバイト列を出す（`-linux` の ELF も PE も）。

```powershell
.\run_selfhost_linux.ps1          # bin\linux へ Linux 版を作り、WSL で次を確かめる
.\run_selfhost_linux.ps1 stage2
```

- Linux 版が `actba64.pj -linux` で出す ELF = Linux 版そのもの（不動点）、`rc.pj -linux` の ELF = Linux 版の rc
- Linux 版が出す `actba64.exe` と `#resource` のテスト（`t_resource` / `t_iconres` / `t_bmpres`）の PE = Windows の同じコンパイラが出すもの
- `check.ps1 integration` は `run_test_linux.ps1` の後にこれも回す（WSL が無ければ SKIP）

---

## 3. リリース一式（`release\`）

リポジトリ根で実行する。

```powershell
.\release_build.ps1                 # actba64 ブートストラップ → ProjectEditor → release\
.\release_build.ps1 -SkipSelfHost   # 既存 stage2 を使い、エディタ再コンパイルとコピーのみ
.\release_build.ps1 -SkipCompare
```

| パス | 内容 |
|---|---|
| `release\ProjectEditor.exe` | エディタ（64bit GUI） |
| `release\actba64.exe` | コンパイラ（既定 64bit、`-actba32` で 32bit） |
| `release\Include\` | `src\Include` のコピー |
| `release\help\` | エディタ向け HTML ヘルプ |
| `release\ProjectEditor_lang_*.csv` | UI 言語パック（既定は英語組み込み） |
| `release\keywords.txt` | エディタのハイライト予約語（1 行 1 語） |
| `release\setting.ini` | `Language=ja` 等（ファイル無し / `en` なら英語） |

`Include` の正本は [`src/Include`](../src/Include) のみ。`VoidPtr` は `*Byte`（ポインタ幅は **コンパイル対象** に従う: 既定 8、`-actba32` で 4）。

前提:

- 初回は `src\actba64\bin\stage0\actba64.exe`（AB4.20）があること
- `src\projecteditor\Callback.wbp` と `MakeWindow.wbp` があること
- `release\ProjectEditor.exe` を起動したままだと上書きに失敗することがある

`release\` は `.gitignore` 対象（`bin\` と同様）。

---

## 4. よくある失敗

| 症状 | 対処 |
|---|---|
| `stage0 missing: ...\actba64.exe` | AB4.20 で `actba64.pj` を `bin\stage0\` にビルドする |
| stage1 vs stage2 が DIFF | ソース変更直後など。`-SkipCompare` で継続し原因を調査 |
| テストで `compiler not found` | 先に `.\build.ps1`（または `-Rebuild`） |
| `ProjectEditor RAD file missing` | `Callback.wbp` / `MakeWindow.wbp` を `src\projecteditor\` に置く |
| `copy failed ... release\ProjectEditor.exe` | エディタを終了してから再実行 |
| ほぼ全テストが `build failed (exit=1)`・コンパイラ出力が空 | `Include` が見えていない／読み込み中に異常終了。`.\build.ps1`（コピー込み）をやり直すか、`Test-Path bin\stage1\Include\default\default.idx` を確認 |
| 途中まで PASS のあと大量に `build failed (exit=0)`、または PowerShell が `actba64.exe` を「認識できない」 | 実行中に `bin\<stage>\actba64.exe` が消えていることが多い（Windows Defender 等の隔離）。`Test-Path bin\stage1\actba64.exe` を確認し、リポジトリまたは `src\actba64\bin` を除外リストへ追加してから `.\build.ps1` → `.\run_test2.ps1` をやり直す |
| `warning: not found: Include\default\default.idx` | 上記 Include 検索パスを確認。正本欠落か、カレントが想定外 |
| AB4.20 で `すでに定義されています`（`WM_*` / `WS_*` / `LB_*` など） | その定数は [`src/Include/default/WinConsts.sbp`](../src/Include/default/WinConsts.sbp) に置く。エディタの `.sbp` へ再 `Const` しない（AB4.20 の標準ヘッダと重なる） |

---

## 5. ProjectEditor

操作仕様は [projecteditor.md](./projecteditor.md) です。`release\ProjectEditor.exe` は 64bit の MDI エディタで、隣の `actba64.exe` を呼びます。

標準ヘッダの正本は [`src/Include`](../src/Include) です。`release_build.ps1` が `release\Include` へコピーします。ProjectEditor 専用の Include コピーはリポジトリに置きません。

AB 4.20 と actba64 の両方で組むソースでは、AB 4.20 の標準ヘッダが既に持つ Win32 定数を `.sbp` に書きません。actba64 向けの共有定義は `WinConsts.sbp` に置き、`default.idx` が自動挿入します。
