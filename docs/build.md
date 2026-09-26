# ビルド手順

ActBa64 は **1 本のコンパイラ** `actba64.exe` です。Lexer → Parser → AST → IR まで共通で、機械語と PE だけ分岐します。既定は PE32+ / AMD64、`-actba32` で PE32 / i386 を出します（中間 `.asm` / `.obj` は出さない）。

ブートストラップ:

1. **stage0** — 人が ActiveBasic 4.20 で `actba64.pj` をビルド（32bit **ホスト**。`#PLATFORM=32` は AB4.20 用で、出力ターゲットではない）
2. **stage1 / stage2** — そのコンパイラが自分自身を 64bit ホストとしてビルド（`-actba32` なし）

前提 OS: Windows（PowerShell）

リポジトリ根の `.\build.ps1` が上記に加えて ProjectEditor を組み、`release\` へ配布一式をコピーする。標準ヘッダは [`src/Include`](../src/Include) の 1 本。

---

## 1. stage0（手動・AB4.20）

作業ディレクトリ: `src\actba64`

ActiveBasic 4.20 で `actba64.pj` をビルドし、`bin\stage0\actba64.exe` に置く（`.pj` の `#OUTPUT_RELEASE` も同じパス）。`bin\stage0` フォルダは先に作ること。

`#PLATFORM=32` は **AB4.20 が 32bit exe を出すため** だけ。コンパイル対象の切替には使わない（対象は CLI の `-actba32`）。

**注意:** AB4.20 は加算を 16bit 化することがあり、古い stage0 だと出力 PE の `SizeOfImage` が壊れ OS が拒否する（`%1 is not a valid Win32 application`）。現行ソースは `AlignUp` / `PeCalcLayout` を DWord 段階演算に直してあるので、**stage0 を作り直すときはこのツリーで** AB4.20 ビルドすること。`build.ps1` は不正 PE を検知して stage3 等へフォールバックする。

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

配布の `release\Include` も正本のコピー（ルート `build.ps1`）。

### コンパイラソースの分割

長大だった Parser / AstLower / Preproc は関数境界で分割している。行数の目標・上限は [coding.md](./coding.md)（ファイル **目標 400 / 上限 1000**、関数 **10 行以内**）。

`actba64.pj` の `#SOURCE`（および単体ホスト用 `actba64.idx`）で複数 `.abp` を結合する。

| 接頭辞 | 役割 | 主なファイル |
|---|---|---|
| `Parser*` | トークン → AST | `Parser` / `ParserExpr` / `ParserStmtIO` / `ParserN88` / `ParserDim` / `ParserClass` / `ParserCtrl` / `ParserDriver` |
| `AstLower*` | AST → IR（`AstToIr`） | `AstLower` / `AstLowerApi` / `AstLowerRt` / `AstLowerAddr` / `AstLowerExpr` / `AstLowerExprOps` / `AstLowerStmt` / `AstLowerStmtCtrl` / `AstLowerDriver` |
| `Preproc*` | `#include` / `.pj` 結合 | `Preproc` / `PreprocPj` |

`#SOURCE` の順序どおりに連結されるため、分割ファイル間で共有の `Type` / `Dim` / 手続きを参照できる。
使い方:

```text
actba64 <src.abp|.pj> [-actba32] -o <out.exe>
```

サンプル:

```powershell
.\bin\stage2\actba64.exe .\samples\n88_shapes.abp -o .\samples\n88_shapes.exe
.\bin\stage2\actba64.exe .\samples\math_test.abp -o .\samples\math_test.exe

# 32bit PE
.\bin\stage2\actba64.exe hello.abp -actba32 -o hello32.exe
```

### 回帰テスト

`test\` 内の `' Target: actba64` 付き `.abp` / `.pj` をコンパイルして実行する。既定 64bit と `-Actba32` の両方で回せる。

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
| skip32 / double | `-Actba32` 時の `Skip32: 1` や `t_double*`（SSE 未対応） |

`SizeOf(UDT)` やポインタ幅に依存する期待値は、64bit 決め打ちせず `SizeOf(*Byte)` 相当（例: ポインタ用ダミー Type）や `' Skip32: 1` で扱う。

---

## 3. リリース一式（`release\`）

リポジトリ根で実行する。

```powershell
.\build.ps1                 # actba64 ブートストラップ → ProjectEditor → release\
.\build.ps1 -SkipSelfHost   # 既存 stage2 を使い、エディタ再コンパイルとコピーのみ
.\build.ps1 -SkipCompare
```

| パス | 内容 |
|---|---|
| `release\ProjectEditor.exe` | エディタ（64bit GUI） |
| `release\actba64.exe` | コンパイラ（既定 64bit、`-actba32` で 32bit） |
| `release\Include\` | `src\Include` のコピー |
| `release\help\` | エディタ向け HTML ヘルプ |
| `release\ProjectEditor_lang_*.csv` | UI 言語パック（既定は英語組み込み。`editor.lang` に `ja` 等） |

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
| テストで `linker not found` | 先に `.\build.ps1`（または `-Rebuild`） |
| `ProjectEditor RAD file missing` | `Callback.wbp` / `MakeWindow.wbp` を `src\projecteditor\` に置く |
| `copy failed ... release\ProjectEditor.exe` | エディタを終了してから再実行 |
| ほぼ全テストが `build failed (exit=1)`・コンパイラ出力が空 | `Include` が見えていない／読み込み中に異常終了。`.\build.ps1`（コピー込み）をやり直すか、`Test-Path bin\stage1\Include\default\default.idx` を確認 |
| 途中まで PASS のあと大量に `build failed (exit=0)`、または PowerShell が `actba64.exe` を「認識できない」 | 実行中に `bin\<stage>\actba64.exe` が消えていることが多い（Windows Defender 等の隔離）。`Test-Path bin\stage1\actba64.exe` を確認し、リポジトリまたは `src\actba64\bin` を除外リストへ追加してから `.\build.ps1` → `.\run_test2.ps1` をやり直す |
| `warning: not found: Include\default\default.idx` | 上記 Include 検索パスを確認。正本欠落か、カレントが想定外 |
