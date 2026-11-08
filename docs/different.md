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
| `#ifdef` / `#ifndef` | 条件付きコンパイル（`_DEBUG`, `_WIN64`, `_AB_VER4` 等を自動定義） | 構文は [language.md §7.7](./language.md#77-条件付きコンパイル)。`.pj` の各ソースと `#include` にも適用する。自動定義は **`_WIN64`（64bit 時）、`_AB_VER4`、`_ACTBA64`**。`_DEBUG` は自動定義しない。`_ACTBA64` は AB 4.20 には無い |
| `#include` の再取り込み | 同じパスを複数回 `#include` すると、都度展開される | **パス単位で一度だけ**（2 回目以降はスキップ。AB 4.20 の都度展開とは異なる） |
| `On Error` / `Resume` | エラートラップ | 非対応 |

### 言語機能

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `Trim$` | なし | `StrUtils.abp`（`default.idx` 自動挿入）。前後の空白（スペース、タブ、CR、LF）を除く |
| UDT 配列の複数添字 | `a(i, j)` / `a(i, j, k)` | 添字 1 個の平坦アクセスのみ（2 次元以上） |
| 省略できる引数 | `Function F(a)(ByRef e As Long)` の 2 つ目の括弧 | 対応。省いた引数は 0、`ByRef` は `VarPtr` が 0。2 つ目の括弧がない `Sub` / `Function` も、省いた残りは 0 |
| 関数ポインタの引数型 | 引数型の一致検査 | 厳密照合は未（呼び出し自体は [language.md §5.2.1](./language.md#521-関数ポインタ型)） |

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
| `Single` / `Double` | IEEE 浮動小数点演算 | **`Single`** の汎用演算は未（格納と `Input` 変換のみ）。`Double` の配列要素と UDT フィールドは `-actba32` でも 8 バイト転送。`Print` の Double は 64bit と `-actba32` で `StrD$`。科学記法（`1.0e10`）は未対応 |
| `Class` | `Inherits`、`Virtual`、`Super.Method`、`New`/`Delete`、アクセス制御 | `Inherits` は親フィールドを先頭に置く。`Virtual` 呼び出しは COM vtable。`Super` は親関数の直接呼び出し（基底 ctor/dtor は自動では呼ばない）。`New` / `Delete` は対応（ヒープ塊の先頭 8 バイトが要素数）。メソッドはマングル名 + 暗黙 `This` |
| N88 `LOCATE` | 本家 N88 BASIC は行・桁 1 始まり | **`LOCATE x, y` は 0 始まり**（桁 x, 行 y） |
| N88 `CIRCLE` … `F` | タイルストリングによる塗りつぶし | `F` 塗りつぶしのみ（タイル未対応） |
| 組込 vs Include | `Left$` / `Len` / `InStr` / `Hex$` 等は `basic\function.sbp` 等 | **`Len` / `Asc` / `Chr$` / … / `ELM` / ビットマクロ等は組込**。`InStr` / `Hex$` / `Val` は **`StrUtils.abp`（`default.idx` 自動挿入）**。`GetByte` 等は **`Memory.abp`（同上）** |
| 数学関数 | `Sin` / `Cos` / `Abs` / `Sqr` 等（浮動小数） | **`Math.abp` のマクローリン展開**。複雑な入れ子は一時変数経由が安全 |
| `Int64` / `QWord` / `Char` | 基本型として定義 | **`Char` / `Int64` / `QWord` 型なし**（`Byte` / `Long` / `DWord` 等） |
| DLL 再配置 | ロード時のベース再配置 | DLL は末尾に `.reloc` を出す。32bit は絶対アドレスの HIGHLOW。64bit は空の再配置表（コードは RIP 相対）。EXE は出さない。`DYNAMIC_BASE` は立てないので、優先ベースが空いていればそのまま、塞がっていればローダーが移動する |
| ソース拡張子 | `.sbp` 推奨 | **`.abp`**（`.pj` で結合） |
| Win32 API | `api_*.sbp` に `Declare` 定義が同梱 | **`default.idx` + `api.idx` + `UnicodeApi.sbp` 自動挿入**。任意 `Declare Lib "dll"`（自作 DLL 含む）可。未登録呼び出しはエラー |
| DirectX | DirectX 9 + `dx_*.sbp` | **DirectX 11**（[改良点](#directx-11)）。高レベル `dx_*` 一式はサンプルのみ |
| 64bit | ver 4.20 はバグで実質困難 | **64bit PE32+ を正式サポート**（ポインタ・`String`・`HANDLE` = 8、`Long` = 4） |
| コンパイル | GUI IDE が主 | **CLI** `actba64 src -o out.exe` |

---

## 文字列の内部表現

ActiveBasic は Shift-JIS で Actba64 は UTF-8 という大きな違いがあります。

プログラミングの文字コードの違いというのは2つの側面を持っています。プログラムのソースのコードと実行時の文字列の内部構造としてどのエンコードを使っているかの２つです。

ActiveBasicは内部の文字列バイトは Shift-JIS（CP932）です。
ソースはUTF-8、Shift-JIS両方対応しています。当時はShift-JISで書くことを想定されています。

ActBa64 の文字列バイトは UTF-8 です。
ソースはUTF-8、Shift-JIS両方対応しています。
今後はUTF-8で書くことを推奨します。

### ソースコードについて
 ソースが妥当な UTF-8（先頭の BOM は読み飛ばす）ならそのまま保持します。
 それ以外は Shift-JIS(CP932) として解釈し、UTF-8 に変換してからコンパイルします。

### Print文
 文字化けがおこらないように工夫してあります。
 コンソールの出力コードページが Shift-JIS(CP932) のとき 
 内部の文字列はUTF8ですがCP932に変換して出力します。
 パイプとファイルへは UTF-8 のままです。

### API
 SetWindowTextAなどの最後のAがつくAPIはShft-JISで出力することを想定していて、そのままですとActba64では文字化けが起こります。
 そこでSetWindowTextがラッパーとなり関数内でUTF-8をUTF-16に変換しSetWindowTextWを呼び出します。
 Actba64上、内部でShift-JISは使われていません。
 ユーザー側のプログラムで・・・AがついているAPIを直接Declareしていた場合は残念ながら文字化けが発生しますので修正が必要になります。

以下API別の詳細です。

- `#n88basic` の窓文字は UTF-8 をワイド文字にして描きます。
- `SetWindowText` / `GetWindowText` / `GetWindowTextLength` / `CreateWindowEx` / `CreateFont` / `SetDlgItemText` / `GetDlgItemText` は UTF-8 をワイド文字 API に渡す。`GetWindowText` は UTF-8 を書き、戻り値は NUL を含まないバイト数。末尾 `A` の Declare は変換しない。
- `InsMenu` / `InsertMenu` / `AppendMenu` / `ModifyMenu` の見出しも UTF-8 をワイド文字 API に渡す。`MF_SEPARATOR` / `MF_BITMAP` / `MF_OWNERDRAW` の第 5 引数は文字列ではないので変換しない。末尾 `A` は変換しない。`GetMenuString` は UTF-8 を書く。
- `InsertMenuItem` / `SetMenuItemInfo` / `GetMenuItemInfo` は、`MIIM_STRING` または文字列の `MIIM_TYPE` のとき `dwTypeData` をワイド文字にする。`GetMenuItemInfo` は UTF-8 を書き、`cch` はそのバイト数。区切り・ビットマップ・オーナードローは変換しない。
- `TextOut` / `GetTextExtentPoint32` / `DrawText` / `DrawTextEx` は UTF-8 をワイド文字数で渡す。長さが負のときは NUL まで。末尾 `A` はバイト数のまま。`DT_MODIFYSTRING` の書き換えは呼び出し側のバッファへ戻さない。
- `CreateStatusWindow` の見出し、`RegisterClassEx` のクラス名とメニュー名、`UnregisterClass` は UTF-8 をワイド文字 API に渡す。65535 以下はアトムなので変換しない。`RegisterClassEx` は呼び出し側の `WNDCLASSEX` を変えない。登録はワイドなので窓は Unicode になり、無印の `DefWindowProc` / `DefFrameProc` / `DefMDIChildProc` は W 版。`GetClassName` は UTF-8 を書く。`GetClassInfoEx` が返すクラス名とメニュー名のポインタは、次に `GetClassInfoEx` を呼ぶまで有効な UTF-8。クラス名がアトム、NULL、または問い合わせに使った変換バッファのときは、引いた名前の UTF-8 を複製して返す。
- `CreateFontIndirect` の `lfFaceName` は UTF-8 をワイド文字 API に渡す。呼び出し側の `LOGFONT` はそのまま。`GetObject` は A 版なので、読み戻した `lfFaceName` は CP932。
- `ChooseFont` / `FindText` / `PrintDlg` / `PageSetupDlg` は A 版のまま。ダイアログが呼び出し側の ANSI バッファへ書き戻し、`FindText` は戻ったあとも書くため。
- `s[n]` は 0 始まりの 1 バイトです。
- `GetOpenFileName` と `GetSaveFileName` は、呼ぶあいだだけフィルタ（二重 NUL）・タイトル・初期フォルダ・拡張子を CP932 にし、戻る前に呼び出し側のポインタへ戻します。ファイル名バッファ（`lpstrFile`）に入れた初期ファイル名は呼ぶ前に CP932 にします。成功したら `lpstrFile` と `lpstrFileTitle` を UTF-8 に書き換え、`nFileOffset` / `nFileExtension` も UTF-8 のバイト位置に直します。複数選択（フォルダ 0 ファイル 0 … 0 0）も同じです。UTF-8 にすると `nMaxFile` / `nMaxFileTitle` に入らないときは、ダイアログが書いた CP932 のままです。ダイアログ自体は A 版なので、CP932 にない文字のファイル名は選べません。
- `CreateFile` / `GetFileAttributes` / `ShellExecute` と、`ChDir` / `MkDir` / `Kill` / `Exec` は、パスが妥当な UTF-8 ならワイド文字 API に渡します。妥当な UTF-8 でないとき（`GetCmd` や `DragQueryFile` が返す CP932 など）は A 版に渡すので、CP932 のパスもそのまま開けます。`ShellExecute` は文字列のどれか 1 つでも妥当な UTF-8 でなければ、すべて A 版に渡します。末尾 `A` の Declare と、`ab_file.sbp` の `CopyFile` / `MoveFile` / `DeleteFile` / `FindFirstFile` などは変換しません。


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
| 関数ポインタの厳密シグネチャ照合 | 引数型の一致検査 | `*Function` / 間接 call 自体は済 |

### ファイル I/O

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| `rc` / `#resource` | リソースファイル取り込み | ファイル→RCDATA(1) は済。ICON は隣の `rc.exe`。MENU は未 |

### GUI・Win32・マルチメディア

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| DirectX 9 Include | `Include\directx9\`（`d3d9` / `d3dx9*` / `dinput` / `dsound` / `dmusic*`） | **未移植**。D3D11 基盤はサンプルで動作。`dx_input`・`dx_music` 相当は未 |
| RAD | Project Editor | 機能拡充予定 |
| Prompt 窓 | `basic\prompt.sbp`（`PromptProc` / `DrawPromptBuffer`） | 未移植。`Print` / `Input` はコンソール。`Inkey$` / `Input$` は `#n88basic` のみ |
| デバッガランタイム | `system\debug.sbp` の `_DebugSys_*` | IDE デバッガ用。未移植 |

