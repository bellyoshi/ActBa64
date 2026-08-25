# ActiveBasic との相違点

完全互換ではない。言語の共通核は [language.md](./language.md)、ビルドは [build.md](./build.md)。

**ActiveBasic 4.20 仕様の参照:** BasicHelp.html（CHM エクスポート。型・文法・Win32/DirectX API・`dx_*.sbp` 等）。  
ActBa64 の実装状況は本書と [language.md](./language.md) を併せて確認すること（実装が docs より進んでいる箇所あり）。

---

## 対応しないこと

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
| `#define` | 条件コンパイル用識別子定義（`#ifdef` 専用） | 非対応 |
| `#ifdef` / `#ifndef` | 条件付きコンパイル（`_DEBUG`, `_WIN64`, `_AB_VER4` 等を自動定義） | 非対応 |
| `ReDim` | 動的配列サイズ変更 | 非対応 |
| `Continue` | ループ先頭へ制御移動（`For` / `While` / `Do`） | 非対応 |
| `On Error` / `Resume` | エラートラップ | 非対応 |

### 言語機能

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Enum` … `End Enum` | 列挙型（`DWord` 値、省略時は前値+1） | 非対応 |
| `Let` | 代入の明示（通常は省略可） | キーワードなし（`=` 代入のみ） |
| `New` / `Delete` | `New [[num]] Class[(params)]`、`Delete pObj` | 非対応（`Dim As Class(args)` で ctor は呼べる） |
| 関数ポインタ型 | `AddressOf(Proc)` で取得し、`CreateThread` 等へ渡す | `AddressOf` は組み込み。型・呼び出し規約の一般サポートは限定的 |
| Ex文字列 | BasicHelp に該当トピックなし | 非対応（要調査） |

### ファイル I/O（言語命令）

BasicHelp の BASIC ファイル命令は未実装。代わりに WinAPI（`CreateFileA` / `ReadFile` / `WriteFile` 等）を `Declare` または IAT 解決で利用可能。

| 項目 | ActiveBasic 仕様 (BasicHelp) |
|---|---|
| `Open` | `Open filename$ [For Input/Output/Append] As number` |
| `Close` | `Close [#filenumber]` |
| `Print #` | `Print #FileNumber, data [, ...]` |
| `Input #` | `Input #filenumber, variable [, ...]` |
| `Write` | `Write [#filenumber, ] [data, ...]`（`,` 区切り） |
| `Get#` / `Put#` | `Get/Put #filenumber, recode, StrBuffer`（`Field` 必須） |
| `Field` | `Field #filenumber, fieldbyte`（ランダムファイル） |
| `Eof` / `Loc` / `Lof` | ファイル状態・位置 |
| `rc` ファイル取り込み | リソース埋め込み |

### GUI・対話・マルチメディア命令

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Window` | `Window hNewWnd, hOwnerWnd, x, y, w, h, title$, style [, ...]` | 非対応（Win32 API で代替） |
| `DelWnd` | `DelWnd hWnd` | 非対応 |
| `MsgBox` | BASIC 命令 | 非対応（`MessageBoxA` API は可） |
| `Cls` / `Beep` | コンソール制御 | 非対応 |
| `Inkey$` | `Inkey$()` — 非同期 1 文字 | 非対応 |
| `Input$(Length)` | 同期、指定長読み取り | 非対応 |
| RAD / `#RESOURCE` | Project Editor・リソース | 未対応 |

---

## 動作が異なるもの

BasicHelp どおりに書いても結果が一致しない、または別の経路で実現する項目。

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 の動作 |
|---|---|---|
| `#strict` | 厳密型チェック。異なる基本型間代入・ポインタ不一致等を警告 | 行は受理するが**無視**（警告なし） |
| `Input` | `Input "prompt", variable` または `Input variable` | **`Input variable` のみ**（プロンプト文字列なし）。`String` / `Long` / `Byte` / `Single` / `Double` に代入可 |
| `Single` / `Double` | IEEE 浮動小数点演算 | **格納サイズのみ**（4/8 バイト）。演算は整数中心。小数リテラル・N88 角度は**千分率固定小数**（`1.5` → 1500）。三角関数等は `Math.abp` |
| `Const` | `Const name = expr` および `Const name(arglist) = expr`（マクロ関数） | 整数・文字列リテラル中心。複雑な定数式・マクロ関数は制限あり |
| `Class` | `Inherits`、`Virtual`、`Super.Method`、`New`/`Delete`、厳密なアクセス制御 | `Inherits` / `Virtual` / vtable 呼び出しは**部分対応**（COM/D3D11 向け）。`New`/`Delete` 演算子なし。`Protected` は受理するが **Public と同等**。メソッドはマングル名 + 暗黙 `Me` |
| `For` … `Next` | `For c = start To end [Step step]`、`Exit For` | **Step / Exit For 対応**（[language.md §4](./language.md#4-文) 参照） |
| `Do` … `Loop` | `Do [While/Until cond] ... [Loop [While/Until cond]]` | **While/Until 両対応** |
| 関係演算の値 | 真 = `-1`、偽 = `0` | 同じ |
| 文字列 | 長さプレフィックス（dword）、埋め込み NUL 可 | **AB 4.20 互換**（[改良点](#文字列長さプレフィックス)） |
| N88 `LOCATE` | 本家 N88 BASIC は行・桁 1 始まり | **`LOCATE x, y` は 0 始まり**（桁 x, 行 y） |
| N88 `CIRCLE` … `F` | タイルストリングによる塗りつぶし | `F` 塗りつぶしのみ（タイル未対応） |
| 組込 vs Include | `Left$` / `Len` / `InStr` / `Hex$` 等は `basic\function.sbp` 等 | **`Len` / `Asc` / `Chr$` / `Left$` / `Mid$` / `Right$` / `Str$` / `VarPtr` / `StrPtr` / `AddressOf` / `SizeOf` / `MakeStr` / `RGB` / `LOWORD` は組込**。`InStr` / `Hex$` / `Val` / `Trim$` 等は **`StrUtils.abp` 等のライブラリ**（自動挿入されない） |
| 数学関数 | `Sin` / `Cos` / `Abs` / `Sqr` 等（浮動小数） | **`Math.abp`（千分率固定小数）**。ネストした関数呼び出し式は actba64 で壊れる場合あり |
| メモリ | `malloc` / `calloc` / `realloc` / `free` | `malloc` / `free` / `memcpy` / `FillMemory`。**`calloc` は `HeapAlloc` へマップ**。`realloc` なし |
| `GetByte` 等 / `SetWord` 等 | ポインタ経由の読み書き | 組み込みなし（自前でポインタ参照） |
| `HIBYTE` / `HIWORD` / `MAKELONG` 等 | ビット分解・合成マクロ | 組み込みなし（`LOWORD` のみ組込） |
| `Int64` / `QWord` / `Char` | 基本型として定義 | **`Char` / `Int64` / `QWord` 型なし**（`Byte` / `Long` / `DWord` 等） |
| ソース拡張子 | `.sbp` 推奨 | **`.abp`**（`.pj` で結合） |
| Win32 API | `api_*.sbp` に `Declare` 定義が同梱 | **`Include\default\default.idx` を自動挿入**。未登録 API は `Declare Lib` またはコンパイルエラー |
| DirectX | DirectX 9 + `dx_*.sbp` | **DirectX 11**（[改良点](#directx-11)）。高レベル `dx_*` 一式はサンプルのみ |
| 64bit | ver 4.20 はバグで実質困難 | **64bit PE32+ を正式サポート**（ポインタ・`String`・`HANDLE` = 8、`Long` = 4） |
| コンパイル | GUI IDE が主 | **CLI** `actba64 src -o out.exe` |

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

### DirectX 11

- **DirectX 9 の代わりに DirectX 11 を採用**
  - `Class` vtable から COM（`ID3D11Device` 等）を呼び出せる。
  - サンプル: [`src/actba64/samples/dxsample/`](../src/actba64/samples/dxsample/)（`d3d11.sbp`、`dx_d3d11.sbp` に `dx_Init` / `dx_Render` / `dx_Quit`）。
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
| `TypeDef` | `TypeDef newtype = basetype`（型エイリアス） | **実装済み** |
| `Type` / `Class` | UDT / OOP（後者は [動作が異なる](#動作が異なるもの) 参照） | **実装済み**（Class はフェーズ1+） |
| `#include` | `"path"` / `<path>` で `.sbp` 取り込み | **`#include "path"`**（`.abp`） |
| 行継続 `_` | 行末 `_` で次行と連結 | **実装済み** |
| `Declare` | `Declare Sub/Function ... Lib "dll" [Alias "..."]` | **actba64 のみ**（actba32 は非対応） |

### 入出力・文字列・メモリ（組み込み）

| 関数 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Len` | 文字列長または UDT サイズ | 組込 |
| `Asc` / `Chr$` | 文字コード変換 | 組込 |
| `Left$` / `Mid$` / `Right$` / `Str$` | 部分文字列・数値文字列化 | 組込 |
| `VarPtr` / `StrPtr` / `MakeStr` | ポインタ取得・NUL 終端から String 生成 | 組込 |
| `AddressOf` | 手続き先頭アドレス（関数ポインタ） | 組込 |
| `SizeOf` / `ELM` | 型サイズ / 添字上限→要素数 | `SizeOf` 組込。**`ELM` なし** |
| `malloc` / `free` | C ヒープ | 組込（`free` → `HeapFree`） |
| `RGB` / `LOWORD` | 色・ワード分解 | 組込 |

### 数学（Include `Math.abp`）

| 関数 | ActiveBasic 仕様 | ActBa64 |
|---|---|---|
| `Abs` / `Sgn` / `Sqr` / `Sin` / `Cos` / `Tan` / `Atn` / `Exp` / `Log` / `Int` / `Fix` | 浮動小数数学 | **千分率固定小数**版（自動 Include） |

---

## 今後対応していくもの（現時点では未対応）

メモ・チェックリスト。実装状況は [language.md](./language.md) を優先する。

### 言語・構文

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| Ex文字列 | BasicHelp 未確認 | 要調査 |
| 関数ポインタ | `AddressOf(Proc)` をスレッド等へ | `AddressOf` のみ。一般化は未 |
| `#strict` | 型不一致を警告 | 現状無視。将来は警告出力 |
| `#define` / `#ifdef` | 条件コンパイル | |
| `GoSub` / `Return` | `*ラベル` 付きサブルーチン | 関数 `Return` とは別 |
| `Enum` | 列挙型定義 | |
| `Let` | 明示代入（省略可） | 優先度低 |
| `Class` 拡張 | `New`/`Delete`、`Super`、厳密 `Protected`、メンバ Class の自動 ctor/dtor | `Inherits`/`Virtual` は部分対応済 |

### ファイル I/O

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `Open` / `Close` | ファイル番号で入出力チャネル | WinAPI で代替可 |
| `Print #` / `Input #` | ファイル番号付き I/O | |
| `Field` / `Get` / `Put` | ランダムファイル・レコード単位 | |
| `Write` | カンマ区切り出力 | |
| `Eof` / `Loc` / `Lof` | ファイル状態 | |
| `rc` ファイル取り込み | リソース | |

### 入出力・対話

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `Input` プロンプト付き | `Input "文字列", variable` | 変数のみ対応済 |
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
| `Randomize` / `Rnd()` | 乱数 | |
| `CDbl` / `CInt` / `CSng` | 型変換関数 | `As` キャストは可 |
| `Oct$` | 8 進文字列 | |
| `Date$` / `Time$` | 日付・時刻文字列 | |
| `Hex$` / `Val` / `ZeroString` | 16 進文字列・数値化・ゼロ埋め | `StrUtils.abp` 等で一部 |
| `InStr` | 部分文字列検索 | `StrUtils.abp`（手動 Include） |
| `HIBYTE` / `HIWORD` / `LOBYTE` / `LOWORD` / `MAKELONG` / `MAKEWORD` | ビット操作 | `LOWORD` のみ組込 |
| `SetDouble` / `SetWord` / `GetDouble` / `GetSingle` / `GetDWord` / `GetByte` 等 | メモリ読み書き | ポインタ直接参照で代替 |
| `calloc` / `realloc` | C ヒープ | `calloc` は `HeapAlloc` マップ済。`realloc` 未 |
| `ELM` | `ELM(n)` — 添字上限から要素数 | |

### GUI・Win32・マルチメディア

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `Window` / `DelWindow` | BASIC ウィンドウ生成・破棄 | Win32 API で代替 |
| ハンドル型 | `HANDLE` / `HWND` 等 | WinTypes で定義済 |
| Win32API | `api_*.sbp` 382 関数超 | 主要 API は IAT 登録済。不足分は `Declare` |
| DirectX | D3D9 + `dx_graphics.sbp` 等 | **D3D11 基盤はサンプルで動作**。BasicHelp 相当の `dx_DrawText` 等・`dx_input`・`dx_music` の D3D11 版は未整備 |
| RAD | Project Editor | 機能拡充予定 |

### 標準ライブラリ

- **`Include` の拡充** — BasicHelp の `basic\*.sbp` / `system\*.sbp` 相当を `.abp` として増やし、再利用しやすくする。
