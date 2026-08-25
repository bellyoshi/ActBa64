# ActiveBasic との相違点

完全互換ではない。言語の共通核は [language.md](./language.md)、ビルドは [build.md](./build.md)。

## 対応しないこと

### 行番号

- **行番号非対応**
  - 言語仕様をシンプルに保つため、`10 PRINT ...` のような行番号付き記述には対応しない。
  - 将来的に、エディター側で「行番号 → ラベル」へ自動変換してからコンパイルできるようにする可能性はあるが、言語仕様として行番号を導入する予定はない。

### DirectX 9（ActiveBasic 付属ライブラリ）

- **DirectX 9 非対応**
  - `d3d9types.sbp` の `D3DCOLOR_RGBA` / `D3DCOLOR_XRGB`、`D3DCULL_*` 等の D3D9 定数・型。
  - `dx_graphics.sbp` の `dx_BeginScene` / `dx_EndScene` / `dx_Clear` / `dx_DrawText` / `dx_Present` / `dx_GetDevice`（`IDirect3DDevice9` 取得）/ `dx_SetProjection` / `dx_SetCamera` / `dx_SetCullMode` / `dx_SetDefaultLight` 等。
  - `dx_input.sbp`（`CInputKeyboard::GetState` 等）、`dx_music.sbp`（`CAudio::GetLength` 等）。
  - ActiveBasic の DirectX 9 プロジェクトをそのままコンパイル・実行することはできない。D3D11 向けに書き換えるか、サンプルの `d3d11.sbp` / `dx_d3d11.sbp` を起点に移植する。

## 改良点

### コマンドラインからのコンパイラ実行

- **CLI ベースのコンパイル**
  - ActiveBasic が主に GUI ベースであるのに対し、本処理系ではコンパイラをコマンドラインから直接実行できる。
  - これにより、AI ツールやスクリプト、CI 環境などからの自動ビルド・自動テストが容易になり、開発速度・開発効率の向上が期待できる。

### 64bit 対応

- **64bit を正式サポート**
  - ActiveBasic ver 4.20 には 64bit 対応機能が存在するものの、バグにより実質的にコンパイル・実行が困難。
  - ActiveBasic ver 5 はリリース候補版のまま開発が停止しており、64bit が正式機能として確立していない。
  - 本処理系では 64bit 環境でのコンパイルおよび実行を前提とした設計とし、64bit 対応を正式にサポートする。

### DirectX 11

- **DirectX 9 の代わりに DirectX 11 を採用**
  - ActiveBasic 4.20（BasicHelp 参照）は DirectX 9.0 向け Include（`d3d9types.sbp`、`dx_graphics.sbp`、`dx_input.sbp`、`dx_music.sbp`）を同梱している。
  - 本処理系は DirectX 9 をサポートしない。代わりに DirectX 11 を前提とする。
  - `Class` の vtable から COM インターフェース（`ID3D11Device`、`ID3D11DeviceContext` 等）を呼び出せる。`d3d11.dll` / `dxgi.dll` / `d3dcompiler_47.dll` をリンク可能。
  - サンプル: [`src/actba64/samples/dxsample/`](../src/actba64/samples/dxsample/)（`d3d11.sbp` に型・定数・vtable 定義、`dx_d3d11.sbp` に `dx_Init` / `dx_Render` / `dx_Quit`）。
  - BasicHelp の DirectX プログラミング章に沿った API 名・利用パターン（ウィンドウハンドルからの初期化、メッセージループ内での描画、終了処理）を、可能な範囲で D3D11 上に再現していく。

### 文字列（長さプレフィックス）

- ActiveBasic 4.20 互換: データ直前 32bit に長さ、`Len(Chr$(0))=1`、埋め込み NUL 可
- actba32 / actba64 共通

## 今後対応していくもの（現時点では未対応）

メモ・チェックリスト。実装状況は [language.md](./language.md) を優先する。

### 言語・構文

| 項目 | メモ |
|---|---|
| Ex文字列 | |
| 関数ポインタ | |
| ByRef | 要確認 |
| `#strict` | |
| `#define` | |
| `GoSub` / `Return` | 関数内 `Return` との折り合い |
| `Enum` | |
| `Let` | |
| `TypeDef` | |
| `With` | |
| `Class` | フェーズ1（メンバ・メソッド・ctor/dtor・`Dim As Class(args)`）は実装済み。[language.md §3.3](./language.md#33-classフェーズ1)。今後: `Inherits` / `Virtual` / `New`/`Delete` など |

### ファイル I/O

| 項目 | メモ |
|---|---|
| `Open` / `Close` | `Open filename$ [For Access] As number` |
| `Print #` / `Input #` | |
| `Field` / `Get` / `Put` | |
| `Write` | |
| `Eof` / `Loc` / `Lof` | |
| `rc` ファイル取り込み | |

### 入出力・対話

| 項目 | メモ |
|---|---|
| `Input` | `Input "文字列", variable` 未対応。現状 `Input variable` のみ |
| `Cls` | |
| `MsgBox` | `MessageBox` は動作 |
| `Beep` | |
| `Inkey$` | |
| `Input$(Length)` | |

### パス・プロセス

| 項目 | メモ |
|---|---|
| `ChDir` | |
| `Exec` | |
| `Kill` | |
| `MkDir` | |

### 数値・変換・文字列関数

| 項目 | メモ |
|---|---|
| `Randomize` / `Rnd()` | |
| `CDbl` / `CInt` / `CSng` | |
| `Abs` / `Sgn` | |
| `ATn` / `Tan` / `Exp` / `Log` / `Fix` / `Int` / `Sqr` | 要確認 |
| `Asc` / `Chr$` | 要確認 |
| `Left$` / `Len` / `Oct$` / `Right$` | 要確認 |
| `Date$` / `Time$` | |
| `Hex$` / `Str$` / `String$` / `Val` / `ZeroString` | |
| `InStr` | |
| `HIBYTE` / `HIWORD` / `LOBYTE` / `LOWORD` / `MAKELONG` / `MAKEWORD` | |
| `SetDouble` / `SetWord` | |
| `GetDouble` / `GetSingle` / `GetDWord` | |
| `StrPtr` | |
| `calloc` / `realloc` | |
| `AddressOf` / `ELM` / `RGB` / `SizeOf` | |

### GUI・Win32・マルチメディア

| 項目 | メモ |
|---|---|
| `Window` / `DelWindow` | 要確認 |
| ハンドル | |
| Win32API | |
| DirectX | D3D11 基盤はサンプルで動作。BasicHelp 相当の `dx_graphics.sbp` 一式（`dx_DrawText` 等）、`dx_input.sbp`、`dx_music.sbp` の D3D11 版は未整備 |
| RAD | Project Editor の機能拡充 |

### 標準ライブラリ

- **`Include` の拡充** — ユーティリティや共通モジュールを増やし、再利用しやすくする
