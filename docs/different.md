# ActiveBasic との相違点

完全互換ではない。言語の共通核は [language.md](./language.md)、ビルドは [build.md](./build.md)。

**ActiveBasic 4.20 仕様の参照:** ローカル `docs/ActiveBasic4.20.md`（gitignore。BasicHelp 抽出。型・文法・Win32/DirectX API・`dx_*.sbp` 等）。  
ActBa64 の実装状況は本書と [language.md](./language.md) を併せて確認すること（実装が docs より進んでいる箇所あり）。

---

## 機能の対応状況（非対応・制限を含む）

実装済みの一覧は後述 [実装済み](#実装済みactivebasic-互換の一部)。ここでは AB との差分が大きい項目を列挙する。

### 行番号

- **ActiveBasic 仕様:** 行番号あり／なしの混在可。`Goto` / `GoSub` で行番号または `*` 付きラベルを参照。
- **ActBa64:** 行番号非対応。`10 PRINT ...` 形式は使えない。
- 言語仕様をシンプルに保つため、行番号は導入しない。将来的にエディター側で「行番号 → ラベル」へ自動変換してからコンパイルする可能性はある。

### DirectX 9（ActiveBasic 付属ライブラリ）

- **ActiveBasic 仕様:** DirectX 9.0。Include は `d3d9types.sbp`、`dx_graphics.sbp`、`dx_input.sbp`、`dx_music.sbp`。`dx_Init(hWnd, ...)` → `dx_BeginScene` / `dx_EndScene` / `dx_Present`、`dx_GetDevice` で `IDirect3DDevice9` 取得。クラス `CAudio` / `CImage2D` / `CMeshModel` / `CInputKeyboard` 等。
- **ActBa64:** DirectX 9 は非対応。D3D9 プロジェクトはそのまま動かない。

### 制御・プリプロセス

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Goto` / `GoSub` / `Return` | 行番号または `*ラベル` へ分岐・復帰 | 非対応（キーワードなし） |
| `#define` | 条件コンパイル用識別子定義（`#ifdef` 専用） | ○ |
| `#ifdef` / `#ifndef` | 条件付きコンパイル（`_DEBUG`, `_WIN64`, `_AB_VER4` 等を自動定義） | ○（自動定義は **`_WIN64`（64bit 時）と `_AB_VER4` のみ**。`_DEBUG` は自動定義しない） |
| `#include` の再取り込み | 同じパスを複数回 `#include` すると、都度展開される | **パス単位で一度だけ**（2 回目以降はスキップ。AB 4.20 の都度展開とは異なる） |
| `ReDim` | 動的配列サイズ変更 | 非対応 |
| `Continue` | ループ先頭へ制御移動（`For` / `While` / `Do`） | ○ |
| `On Error` / `Resume` | エラートラップ | 非対応 |

### 言語機能

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Enum` … `End Enum` | 列挙型（`DWord` 値、省略時は前値+1） | ○（初回省略時は **1**、`Dim x As EnumName` は 4 バイト） |
| `Let` | 代入の明示（通常は省略可） | キーワードなし（`=` 代入のみ） |
| `New` / `Delete` | `New [[num]] Class[(params)]`、`Delete pObj` | 非対応（`Dim As Class(args)` で ctor は呼べる） |
| 関数ポインタ型 | `Dim As *Function(...)` / `*Sub(...)`、`TypeDef`、`AddressOf`、間接呼び出し | **対応**（引数型の厳密照合は未。詳細は [language.md §5.2.1](./language.md)） |
| Ex文字列 | エスケープ付き `Ex"..."` | ○ |

### ファイル I/O（言語命令）

`Open` / `Close` / `Input #` / `Write` / `Field` / `Get #` / `Put #` / `Print #` / `Eof` / `Loc` / `Lof` は `BasicFile.abp` で対応（番号 1..16）。WinAPI でも代替可。

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Open` | `Open filename$ [For Input/Output/Append] As number` | ○（`As #n` 可。パス式は `As` キャストなし） |
| `Close` | `Close [#filenumber]` | ○（省略で全閉） |
| `Print #` | `Print #FileNumber, data [, ...]` | ○ |
| `Input #` | `Input #filenumber, variable [, ...]` | ○（カンマ／改行区切りフィールド） |
| `Write` | `Write [#filenumber, ] [data, ...]`（`,` 区切り） | ○ |
| `Get#` / `Put#` | `Get/Put #filenumber, recode, StrBuffer`（`Field` 必須） | ○ |
| `Field` | `Field #filenumber, fieldbyte`（ランダムファイル） | ○ |
| `Eof` / `Loc` / `Lof` | ファイル状態・位置 | ○ |
| `rc` ファイル取り込み | リソース埋め込み | **部分対応**（`#resource "file"` → RCDATA 1。`.rc`/ICON/MENU は未） |

### GUI・対話・マルチメディア命令

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Window` | `Window hNewWnd, hOwnerWnd, x, y, w, h, title$, style [, ...]` | 非対応（Win32 API で代替） |
| `DelWnd` | `DelWnd hWnd` | 非対応 |
| `MsgBox` | BASIC 命令 | 非対応（`MessageBoxA` API は可） |
| `Cls` / `Beep` | コンソール制御 | 非対応 |
| `Inkey$` | `Inkey$()` — 非同期 1 文字 | 非対応 |
| `Input$(Length)` | 同期、指定長読み取り | 非対応 |
| RAD / `#RESOURCE` | Project Editor・リソース | `#resource` 埋め込みは部分対応。RAD / `.pj` `#RESOURCE=` は未 |

---

## 動作が異なるもの

BasicHelp どおりに書いても結果が一致しない、または別の経路で実現する項目。

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 の動作 |
|---|---|---|
| `#strict` | 厳密型チェック。異なる基本型間代入・ポインタ不一致等を警告 | **変数同士の代入**で型不一致を warning（`As` で抑制）。リテラル代入は対象外。`Include\default` は抑制 |
| `Input` | `Input "prompt", variable` または `Input variable` | **両方対応**（`String` / `Long` / `Byte` / `Single` / `Double`） |
| `Single` / `Double` | IEEE 浮動小数点演算 | **`Double`（64bit）**: 加減乗除・比較・`Function As Double` / Double 仮引数・小数リテラルは AST 上 IEEE ビット（千分率は不使用）。`Math.abp` も IEEE Double。**`Single`**: 格納と Input 変換が中心（汎用演算は未）。N88 `CIRCLE` 角度・aspect は `Double`。`-actba32` は SSE 未実装のため Double 演算テストをスキップ |
| `Const` | `Const name = expr` および `Const name(arglist) = expr`（マクロ関数） | 整数・文字列リテラル中心。複雑な定数式・マクロ関数は制限あり |
| `Class` | `Inherits`、`Virtual`、`Super.Method`、`New`/`Delete`、厳密なアクセス制御 | `Inherits` / `Virtual` / vtable 呼び出しは**部分対応**（COM/D3D11 向け）。`New`/`Delete` / `Super` 演算子なし。`Private` / `Public` / `Protected` は**受理のみ**（アクセス制御なし）。メソッドはマングル名 + 暗黙 `Me` |
| `For` … `Next` | `For c = start To end [Step step]`、`Exit For` | **Step / Exit For 対応**（[language.md §4](./language.md#4-文) 参照） |
| `Do` … `Loop` | `Do [While/Until cond] ... [Loop [While/Until cond]]` | **While/Until 両対応** |
| 関係演算の値 | 真 = `-1`、偽 = `0` | 同じ |
| `TRUE` / `FALSE` 定数 | **`TRUE` = 1**、`FALSE` = 0（BasicHelp） | **同じ**（組み込み + `WinConsts.sbp`）。小文字 `true` / `false` は AB 同様**未対応** |
| 文字列 | 長さプレフィックス（dword）、埋め込み NUL 可 | **AB 4.20 互換**（[改良点](#文字列長さプレフィックス)） |
| N88 `LOCATE` | 本家 N88 BASIC は行・桁 1 始まり | **`LOCATE x, y` は 0 始まり**（桁 x, 行 y） |
| N88 `CIRCLE` … `F` | タイルストリングによる塗りつぶし | `F` 塗りつぶしのみ（タイル未対応） |
| 組込 vs Include | `Left$` / `Len` / `InStr` / `Hex$` 等は `basic\function.sbp` 等 | **`Len` / `Asc` / `Chr$` / … / `ELM` / ビットマクロ等は組込**。`InStr` / `Hex$` / `Val` / `Trim$` は **`StrUtils.abp`（`default.idx` 自動挿入）**。`GetByte` 等は **`Memory.abp`（同上）** |
| 数学関数 | `Sin` / `Cos` / `Abs` / `Sqr` 等（浮動小数） | **`Math.abp`（IEEE Double）**。ネストした関数呼び出しは対応（複雑な入れ子は一時変数経由が安全） |
| メモリ | `malloc` / `calloc` / `realloc` / `free` | `malloc` / `free` / `memcpy` / `FillMemory`。**`calloc` は `HeapAlloc` へマップ**。`realloc` なし |
| `GetByte` 等 / `SetWord` 等 | ポインタ経由の読み書き | **`Memory.abp`**（浮動小数版は未） |
| `HIBYTE` / `HIWORD` / `MAKELONG` 等 | ビット分解・合成マクロ | **組込** |
| `Int64` / `QWord` / `Char` | 基本型として定義 | **`Char` / `Int64` / `QWord` 型なし**（`Byte` / `Long` / `DWord` 等） |
| ソース拡張子 | `.sbp` 推奨 | **`.abp`**（`.pj` で結合） |
| Win32 API | `api_*.sbp` に `Declare` 定義が同梱 | **`default.idx` + `api.idx` + `UnicodeApi.sbp` 自動挿入**。任意 `Declare Lib "dll"`（自作 DLL 含む）可。未登録呼び出しはエラー |
| DirectX | DirectX 9 + `dx_*.sbp` | **DirectX 11**（[改良点](#directx-11)）。高レベル `dx_*` 一式はサンプルのみ |
| 64bit | ver 4.20 はバグで実質困難 | **64bit PE32+ を正式サポート**（ポインタ・`String`・`HANDLE` = 8、`Long` = 4） |
| コンパイル | GUI IDE が主 | **CLI** `actba64 src -o out.exe` |

---

## 既知の問題（AB 4.20 仕様をそのまま踏襲）

ActBa64 の不具合ではなく、**ActiveBasic 4.20 と同じ挙動**として把握しておく項目。

### 定数 `TRUE` (=1) と関係演算の真 (-1) が一致しない

- **定数** `TRUE` / `FALSE` は **1 / 0**（Win32 慣習・BasicHelp）。
- **関係演算**（`=` など）の**式の値**は、真 **-1**、偽 **0**。
- そのため `(TRUE = TRUE)` は **-1** になるが、`(-1 = TRUE)` は **`-1 = 1` で偽**になり、連鎖比較 `(TRUE = TRUE) = TRUE` は直感とずれる（AB 4.20 も **`False`**）。

```basic
#console
If (TRUE = TRUE) = TRUE Then
    Print "True"
Else
    Print "False"    ' AB 4.20 / ActBa64 ともこちら
End If

If (-1 = -1) = -1 Then
    Print "True"     ' こちらは真
Else
    Print "False"
End If
```

比較結果そのものを扱うときは **`-1` / `0` リテラル**や中間変数を使う。回帰: `test/t_true_chain.abp`。

### 小文字 `true` / `false`

AB 4.20 では **`true` / `false` は識別子として無効**。ActBa64 も **`TRUE` / `FALSE`（大文字）のみ**組み込み。小文字は未定義変数としてエラーになる。

### 識別子の大小区別（AB 4.20 同様）

**定数・変数・Sub/Function・Declare 名・Type/Class 名**は定義どおりの綴りで参照する（`TRUE` ≠ `true`、`Foo` ≠ `foo`）。**言語キーワード**、**組み込みランタイム**（`FillMemory` / `memcpy` / `malloc` 等）だけ大小無視。Win32 API は `api.idx` の Declare 名（および Alias の裸名）と一致させる。

---

## 改良点

### コマンドラインからのコンパイラ実行

- **CLI ベースのコンパイル**
  - ActiveBasic が主に GUI ベースであるのに対し、本処理系ではコンパイラをコマンドラインから直接実行できる。
  - AI ツール・スクリプト・CI からの自動ビルド・テストが容易。

### 64bit 対応

- **64bit を正式サポート**
  - ActiveBasic ver 4.20 には 64bit 対応機能が存在するものの、バグにより実質的にコンパイル・実行が困難。
  - ActiveBasic ver 5 は RC のまま開発停止。
  - 本処理系は 64bit 環境を前提とした設計。

### IEEE Double

- **浮動小数は IEEE 754 Double を正式サポート**（64bit ターゲット）
  - 小数リテラル・式・`Math.abp`・`Function As Double` / Double 仮引数・N88 `CIRCLE` 角度・aspect・`Input` の数値変換まで一貫して Double ビット列を扱う。
  - 旧内部表現（千分率整数）は廃止。
  - `-actba32` では SSE 未実装のため Double 演算は未対応（テストはスキップ）。
  - 回帰: `test/t_double_*.abp` / `test/t_dbl_*.abp` / `test/t_math_*.abp`。

### DirectX 11

- **DirectX 9 の代わりに DirectX 11 を採用**
  - `Class` vtable から COM（`ID3D11Device` 等）を呼び出せる。
  - サンプル: [`src/actba64/samples/dxsample/`](../src/actba64/samples/dxsample/)（共通ヘッダ [`src/Include/d3d11/d3d11.sbp`](../src/Include/d3d11/d3d11.sbp)、各サンプルの `dx_d3d11.sbp` に `dx_Init` / `dx_Render` / `dx_Quit`）。
  - 行列変換（移動・回転・拡大縮小）+ キーボード操作: [`src/actba64/samples/dxxform/`](../src/actba64/samples/dxxform/)。
  - 6面立方体 + 行列変換: [`src/actba64/samples/dxcube2/`](../src/actba64/samples/dxcube2/)。
  - BasicHelp の DirectX 章の利用パターン（初期化 → メッセージループ内描画 → 終了）を D3D11 上で再現していく。

### 文字列（長さプレフィックス）

- **ActiveBasic 仕様:** データ直前 32bit に長さ。`Len(Chr$(0))=1`。埋め込み NUL 可。
- actba32 / actba64 共通で AB 4.20 互換。

---

## 実装済み（ActiveBasic 互換の一部）

BasicHelp に記載があり、ActBa64 で利用できる主要項目。詳細は [language.md](./language.md)。

### 言語・構文

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `With` … `End With` | 構造体メンバを `.Member` で省略、ネスト可 | **実装済み** |
| `ByRef` / `ByVal` | 既定は値渡し。`ByRef p As Type` で参照渡し | **実装済み** |
| `TypeDef` | `TypeDef newtype = basetype`（型エイリアス） | **実装済み**（`*Function` / `*Sub` 別名も可） |
| `Type` / `Class` | UDT / OOP（後者は [動作が異なる](#動作が異なるもの) 参照） | **実装済み**（`Type Name Align(n)`、`Inherits` / `Virtual` は部分対応） |
| `#include` | `"path"` / `<path>` で `.sbp` 取り込み（同一パスの再 `#include` は都度展開） | **`"path"`**（ソース相対）と **`<path>`**（`Include\` 検索）の両方可（拡張子は `.abp` / `.sbp` 可）。**同一パスは一度だけ**（[制御・プリプロセス](#制御プリプロセス)） |
| 行継続 `_` | 行末 `_` で次行と連結 | **実装済み** |
| `Declare` | `Declare Sub/Function ... Lib "dll" [Alias "..."]` | **実装済み**（32/64 とも IAT。`Lib` は任意 DLL・自作 C/C++ 可。詳細は [language.md §8](./language.md#8-winapi--iat)） |
| `Enum` | 列挙型 | **実装済み** |
| Ex文字列 | `Ex"..."`（エスケープ付き） | **実装済み** |
| `#strict` | 型不一致を警告 | **実装済み**（変数代入。詳細は [動作が異なるもの](#動作が異なるもの)） |
| `#define` / `#ifdef` | 条件コンパイル | **実装済み** |
| 関数ポインタ | `*Function` / `*Sub` / `TypeDef` / `AddressOf` / 間接 call | **実装済み**（[language.md §5.2.1](./language.md)） |

### 入出力・文字列・メモリ（組み込み）

| 関数 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Len` | 文字列長または UDT サイズ | 組込 |
| `Asc` / `Chr$` | 文字コード変換 | 組込 |
| `Left$` / `Mid$` / `Right$` / `Str$` | 部分文字列・数値文字列化 | 組込 |
| `InStr` / `Hex$` / `Val` / `Trim$` | 検索・16 進・数値化・前後空白除去 | **`StrUtils.abp`**（`default.idx` 自動挿入） |
| `VarPtr` / `StrPtr` / `MakeStr` | ポインタ取得・NUL 終端から String 生成 | 組込 |
| `AddressOf` | 手続き先頭アドレス（関数ポインタ） | 組込（`*Function` / `*Sub` 変数へ代入して間接呼び出し可） |
| `SizeOf` / `ELM` | 型サイズ / 添字上限→要素数 | **両方組込** |
| `malloc` / `free` | C ヒープ | 組込（`free` → `HeapFree`） |
| `RGB` / `LOWORD` | 色・ワード分解 | 組込 |

### 数学（Include `Math.abp`）

| 関数 | ActiveBasic 仕様 | ActBa64 |
|---|---|---|
| `Abs` / `Sgn` / `Sqr` / `Sin` / `Cos` / `Tan` / `Atn` / `Exp` / `Log` / `Int` / `Fix` | 浮動小数数学 | **IEEE Double**（自動 Include）。`MathPi()` / `MathE()`。`test/t_math_*.abp` |
| `Rnd` / `Randomize` | `[0,1)` 乱数 | **済**（`Rnd` は Double。`test/t_rnd.abp`） |
| `Log10` / `SinDeg` / `CosDeg` | — | Double。`MathDiv` / `MathMod` は整数ヘルパとして残置 |

---

## 今後対応していくもの（現時点では未対応）

メモ・チェックリスト。実装状況は [language.md](./language.md) を優先する。

### 言語・構文

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `GoSub` / `Return` | `*ラベル` 付きサブルーチン | 関数 `Return` とは別。方針上は非対応寄り |
| `Let` | 明示代入（省略可） | 優先度低 |
| `Class` 拡張 | `New`/`Delete`、`Super`、厳密な `Private`/`Protected`、メンバ Class の自動 ctor/dtor | `Inherits`/`Virtual` は COM/vtable 向けに部分対応済。アクセス修飾子は受理のみ |
| 関数ポインタの厳密シグネチャ照合 | 引数型の一致検査 | `*Function` / 間接 call 自体は済 |

### ファイル I/O

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `rc` / `#resource` | リソースファイル取り込み | ファイル→RCDATA(1) は済。`.rc` 直接 / ICON・MENU は未 |

### 入出力・対話

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `Cls` | 画面クリア | |
| `MsgBox` | BASIC 命令 | `MessageBoxA` で代替 |
| `Beep` | ビープ音 | |
| `Inkey$` | 非同期 1 キー | |
| `Input$(Length)` | 同期・固定長読み取り | |

### パス・プロセス

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `ChDir` | カレントディレクトリ変更 | |
| `Exec` | 外部プログラム実行 | `CreateProcessA` で代替可 |
| `Kill` | ファイル削除 | |
| `MkDir` | ディレクトリ作成 | |

### 数値・変換・文字列関数

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `CDbl` / `CInt` / `CSng` | 型変換関数 | `As` キャストは可 |
| `Oct$` | 8 進文字列 | |
| `Date$` / `Time$` | 日付・時刻文字列 | |
| `ZeroString` | ゼロ埋め文字列 | 未（`Hex$` / `Val` / `Trim$` / `InStr` は `StrUtils.abp` で済） |
| `SetDouble` / `GetDouble` / `GetSingle` 等 | メモリ読み書き | **`Memory.abp`** は Byte〜DWord まで。浮動 Get/Set は未 |
| `realloc` | C ヒープ | `calloc`（→ `HeapAlloc` ゼロ埋め）は済。`realloc` 未 |

### GUI・Win32・マルチメディア

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `Window` / `DelWnd` | BASIC ウィンドウ生成・破棄 | Win32 API で代替 |
| Win32API 全量 | `api_*.sbp` 382 関数超 | 主要 API は `api.idx` Declare。不足分・自作 DLL はソース側 `Declare` |
| DirectX | D3D9 + `dx_graphics.sbp` 等 | **D3D11 基盤はサンプルで動作**。`dx_input`・`dx_music` 等の D3D11 版は未整備 |
| RAD | Project Editor | 機能拡充予定 |

### 標準ライブラリ

- **`Include` の拡充** — BasicHelp の `basic\*.sbp` / `system\*.sbp` 相当を `.abp` として増やし、再利用しやすくする。
