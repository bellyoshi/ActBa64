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

現行ソースは `AlignUp`、`PeCalcLayout`、`CgSnapRva`、`CgAbs32Add` を DWord の段階代入にしてある。**stage0 を作り直すときはこのツリーで** AB4.20 ビルドすること。`build.ps1` は不正 PE を検知して stage3 等へフォールバックする。

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
| `Parser*` | トークン → AST | `Parser` / `ParserExpr` / `ParserFactor` / `ParserNew` / `ParserCmd` / `ParserStmtIO` / `ParserFileStmt` / `ParserN88*` / `ParserDim` / `ParserClass*` / `ParserCtrl` / `ParserSelect` / `ParserProc` / `ParserDriver` ほか |
| `AstLower*` | AST → IR（`AstToIr`） | `AstLower` / `AstLowerApi` / `AstLowerRt*` / `AstLowerAddr` / `AstLowerExpr*` / `AstLowerPrint` / `AstLowerStmt*` / `AstLowerNew` / `AstLowerFileStmt` / `AstLowerDriver` ほか |
| `Preproc*` | `#include` / `.pj` 結合 | `Preproc` / `PreprocInc` / `PreprocCond` / `PreprocPj` / `PreprocPjSrc` / `PreprocRes` ほか |

`#SOURCE` の順序どおりに連結されるため、分割ファイル間で共有の `Type` / `Dim` / 手続きを参照できる。
使い方:

```text
actba64 <src.abp|.pj> [-actba32] [-o <out>]
```

`.pj` の `#OUTPUT_RELEASE` は `-o` が無いときに使う（パスは `.pj` ディレクトリ基準）。DLL は `#MODULETYPE=1`（[language.md §8.4](./language.md#84-dll-を出力する)）。

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

配布物の `release\ProjectEditor.exe` は MDI エディタです。ソースは子ウィンドウで、同時に最大 8 枚開いたままにします。**Window** メニューは Cascade / Tile Horizontal / Tile Vertical です。

標準ヘッダの正本は [`src/Include`](../src/Include) です。`release_build.ps1` が `release\Include` へコピーします。ProjectEditor 専用の Include コピーはリポジトリに置きません。

### プロジェクトウィンドウ

`.pj` を開くと（File → Open、または起動時の引数）、ソースは開かずプロジェクトウィンドウが出ます。`#SOURCE` の次の行から、次の `#` 指令の手前までを一覧します。空行と `'` コメントは除きます（最大 128 件）。行をクリックするとそのファイルを開き、既に開いていれば前面にします。別の `.pj` を開くと一覧が差し替わります。プロジェクトウィンドウを閉じると、プロジェクトは解除されます。

MDI の見本は [`src/actba64/samples/mdi/mdi.pj`](../src/actba64/samples/mdi/mdi.pj) です。

### コンパイルと実行

Basic メニューの **64bit**（既定）は、エディタと同じディレクトリの `actba64.exe` を呼びます。見つからなければパス上の同名です。**32bit** は同じ `actba64.exe` に `-actba32` を付けて呼びます。

| 状態 | 渡す入力 | 出力 |
|---|---|---|
| プロジェクトウィンドウが開いている | その `.pj` | `#OUTPUT_RELEASE`（`.pj` のあるディレクトリ基準）。無ければ `.pj` の拡張子を `.exe` にしたもの |
| プロジェクトを開いていない | 前面のソース 1 ファイル | そのパスの拡張子を `.exe` にしたもの |

呼び方は `actba64 <入力> -o <出力>` です。32bit のときは `actba64 -actba32 <入力> -o <出力>` です。コンパイル前に、プロジェクトなら開いているメンバーのうち未保存のファイルを、単体なら前面のファイルを保存します。プロジェクトを開いているあいだは、前面が別ファイルでも Compile / Run はその `.pj` を渡します。メッセージウィンドウで、`ファイル(行):` を含む `error:` / `warning:` 行をクリックするとそのファイルの行頭へ移ります。位置の無い行や、ドラッグによる選択では移動しません。

**Run** はコンパイルに成功したあと起動します。プロジェクトでは `#USEWINDOW` が 0 のとき `cmd /k` でコンソールを残し、1 以上なら exe を直接起動します（未指定は 0）。単体ファイルでは、先頭 120 行に `#console` があるときだけ `cmd /k` です。

AB 4.20 と actba64 の両方で組むソースでは、AB 4.20 の標準ヘッダが既に持つ Win32 定数を `.sbp` に書きません。actba64 向けの共有定義は `WinConsts.sbp` に置き、`default.idx` が自動挿入します。
