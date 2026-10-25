# ActiveBasic との相違点

完全互換ではない。言語の共通核は [language.md](./language.md)、ビルドは [build.md](./build.md)。AB 4.20 と同じ挙動として残る既知の問題は [known.md](./known.md)。

**ActiveBasic 4.20 仕様の参照:** ローカル `docs/ActiveBasic4.20.md`（gitignore。BasicHelp 抽出。型・文法・Win32/DirectX API・`dx_*.sbp` 等）。  
実装が本書より進んでいるときは [language.md](./language.md) を優先する。

---

## 機能の対応状況（非対応・制限を含む）

実装の正本は [language.md](./language.md)。本書は結果や有無が AB とずれる点だけを書く。対応していて結果も同じものは言語仕様側に書く。

### DirectX 9（ActiveBasic 付属ライブラリ）

- **ActiveBasic 仕様:** DirectX 9.0。Include は `d3d9types.sbp`、`dx_graphics.sbp`、`dx_input.sbp`、`dx_music.sbp`。`dx_Init(hWnd, ...)` → `dx_BeginScene` / `dx_EndScene` / `dx_Present`、`dx_GetDevice` で `IDirect3DDevice9` 取得。クラス `CAudio` / `CImage2D` / `CMeshModel` / `CInputKeyboard` 等。
- **ActBa64:** DirectX 9 は非対応。D3D9 プロジェクトはそのまま動かない。

### 制御・プリプロセス

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `#ifdef` / `#ifndef` | 条件付きコンパイル（`_DEBUG`, `_WIN64`, `_AB_VER4` 等を自動定義） | 構文は [language.md §7.7](./language.md#77-条件付きコンパイル)。自動定義は **`_WIN64`（64bit 時）、`_AB_VER4`、`_ACTBA64`**。`_DEBUG` は自動定義しない。`_ACTBA64` は AB 4.20 には無い |
| `#include` の再取り込み | 同じパスを複数回 `#include` すると、都度展開される | **パス単位で一度だけ**（2 回目以降はスキップ。AB 4.20 の都度展開とは異なる） |
| `On Error` / `Resume` | エラートラップ | 非対応 |

### 言語機能

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Let` | 代入の明示（通常は省略可） | キーワードなし（`=` 代入のみ） |
| UDT 配列の複数添字 | `a(i, j)` / `a(i, j, k)` | 添字 1 個の平坦アクセスのみ（2 次元以上） |
| 関数ポインタの引数型 | 引数型の一致検査 | 厳密照合は未（呼び出し自体は [language.md §5.2.1](./language.md#521-関数ポインタ型)） |
| `Class` の残り | `Super`、厳密なアクセス制御、メンバ Class の自動 ctor/dtor | `Super` なし。`Private` / `Public` / `Protected` は受理のみ。メンバ Class の自動 ctor/dtor は未（`New` / `Delete` 自体は [language.md §3.3](./language.md#33-class)） |

### リソース

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `rc` ファイル取り込み | リソース埋め込み | **部分対応**（`#resource "file"` → RCDATA 1。`.rc` の ICON は隣の `rc.exe`。MENU は未） |

### GUI・対話・マルチメディア命令

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Cls` | Prompt 窓のクリア | コンソール全面クリア（Prompt 窓ではない。引数は受け取るが常にテキスト画面） |
| `Inkey$` | `Inkey$()` — 非同期 1 文字 | **`#n88basic` / `#prompt` のみ**（`n88key.abp`）。窓の `WM_KEYDOWN`。無ければ `""` |
| `Input$(Length)` | 同期、指定長読み取り | **`#n88basic` / `#prompt` のみ**。同じキーを `Length` 文字待つ |
| RAD / `#RESOURCE` | Project Editor・リソース | `#resource` 埋め込みは部分対応。RAD / `.pj` `#RESOURCE=` は未 |

---

## 動作が異なるもの

BasicHelp どおりに書いても結果が一致しない、または別の経路で実現する項目。

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 の動作 |
|---|---|---|
| `#strict` | 厳密型チェック。異なる基本型間代入・ポインタ不一致等を警告 | 変数代入に加え、`Long`→`Byte`（呼び出し結果を含む）と引数の `String`→`VoidPtr`・`VoidPtr`→`Long` を warning（`As` で抑制）。数値リテラルは対象外。`Include\default` は抑制 |
| `Single` / `Double` | IEEE 浮動小数点演算 | **`Single`** の汎用演算は未（格納と `Input` 変換のみ）。**`-actba32`**: `Double` の配列要素と UDT フィールドの 8 バイト転送は未。`Print` の Double 自動変換は 64bit のみ。科学記法（`1.0e10`）は未対応 |
| `Class` | `Inherits`、`Virtual`、`Super.Method`、`New`/`Delete`、厳密なアクセス制御 | `Inherits` / `Virtual` / vtable 呼び出しは**部分対応**（COM/D3D11 向け）。`New` / `Delete` は対応（ヒープ塊の先頭 8 バイトが要素数）。`Super` 演算子なし。`Private` / `Public` / `Protected` は**受理のみ**（アクセス制御なし）。メソッドはマングル名 + 暗黙 `This` |
| N88 `LOCATE` | 本家 N88 BASIC は行・桁 1 始まり | **`LOCATE x, y` は 0 始まり**（桁 x, 行 y） |
| N88 `CIRCLE` … `F` | タイルストリングによる塗りつぶし | `F` 塗りつぶしのみ（タイル未対応） |
| 組込 vs Include | `Left$` / `Len` / `InStr` / `Hex$` 等は `basic\function.sbp` 等 | **`Len` / `Asc` / `Chr$` / … / `ELM` / ビットマクロ等は組込**。`InStr` / `Hex$` / `Val` / `Trim$` は **`StrUtils.abp`（`default.idx` 自動挿入）**。`GetByte` 等は **`Memory.abp`（同上）** |
| 数学関数 | `Sin` / `Cos` / `Abs` / `Sqr` 等（浮動小数） | **`Math.abp` のマクローリン展開**。複雑な入れ子は一時変数経由が安全 |
| `Int64` / `QWord` / `Char` | 基本型として定義 | **`Char` / `Int64` / `QWord` 型なし**（`Byte` / `Long` / `DWord` 等） |
| DLL 再配置 | ロード時のベース再配置 | 出力は可（`.edata`）。**`.reloc` なし**。優先ベース（64bit `0x180000000` / 32bit `0x10000000`）が塞がるとロード失敗 |
| ソース拡張子 | `.sbp` 推奨 | **`.abp`**（`.pj` で結合） |
| Win32 API | `api_*.sbp` に `Declare` 定義が同梱 | **`default.idx` + `api.idx` + `UnicodeApi.sbp` 自動挿入**。任意 `Declare Lib "dll"`（自作 DLL 含む）可。未登録呼び出しはエラー |
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
  - サンプル: [`src/actba64/samples/dxsample/`](../src/actba64/samples/dxsample/)（共通ヘッダ [`src/Include/d3d11/d3d11.sbp`](../src/Include/d3d11/d3d11.sbp)、各サンプルの `dx_d3d11.sbp` に `dx_Init` / `dx_Render` / `dx_Quit`）。
  - 行列変換（移動・回転・拡大縮小）+ キーボード操作: [`src/actba64/samples/dxxform/`](../src/actba64/samples/dxxform/)。
  - 6面立方体 + 行列変換: [`src/actba64/samples/dxcube2/`](../src/actba64/samples/dxcube2/)。
  - BasicHelp の DirectX 章の利用パターン（初期化 → メッセージループ内描画 → 終了）を D3D11 上で再現していく。
  - `dx_SetProjection` / `dx_SetCamera` は [`dx_camera.sbp`](../src/Include/d3d11/dx_camera.sbp)。ビューと射影は `g_dxView` / `g_dxProj`（デバイスの `SetTransform` はない）。`dx_SetCullMode` は [`dx_graphics.sbp`](../src/Include/d3d11/dx_graphics.sbp) がラスタライザステートへ渡す。

---

## 今後対応していくもの（現時点では未対応）

メモ・チェックリスト。実装状況は [language.md](./language.md) を優先する。

### 言語・構文

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `Let` | 明示代入（省略可） | 優先度低 |
| DLL `.reloc` | ベース再配置 | 出力は済。優先ベースが塞がるとロード失敗 |
| `Class` 拡張 | `Super`、厳密な `Private`/`Protected`、メンバ Class の自動 ctor/dtor | `New`/`Delete` は済。`Inherits`/`Virtual` は COM/vtable 向けに部分対応済。アクセス修飾子は受理のみ |
| 関数ポインタの厳密シグネチャ照合 | 引数型の一致検査 | `*Function` / 間接 call 自体は済 |

### ファイル I/O

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `rc` / `#resource` | リソースファイル取り込み | ファイル→RCDATA(1) は済。ICON は隣の `rc.exe`。MENU は未 |

### GUI・Win32・マルチメディア

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| 共通ダイアログ / コモンコントロール | `ChooseColor` / `ChooseFont` / `PageSetupDlg` / `PrintDlg` / `InitCommonControlsEx` | 型（`CHOOSECOLOR` 等）と `InitCommonControls` はある。上記 5 つの `Declare` は無い。`FillMemory` / `memcpy` / `Sleep` は組込 |
| DirectX 9 Include | `Include\directx9\`（`d3d9` / `d3dx9*` / `dinput` / `dsound` / `dmusic*`） | **未移植**。D3D11 基盤はサンプルで動作。`dx_input`・`dx_music` 相当は未 |
| RAD | Project Editor | 機能拡充予定 |
| Prompt 窓 | `basic\prompt.sbp`（`PromptProc` / `DrawPromptBuffer`） | 未移植。`Print` / `Input` はコンソール。`Inkey$` / `Input$` は `#n88basic` のみ |
| デバッガランタイム | `system\debug.sbp` の `_DebugSys_*` | IDE デバッガ用。未移植 |

