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
| `#ifdef` / `#ifndef` | 条件付きコンパイル（`_DEBUG`, `_WIN64`, `_AB_VER4` 等を自動定義） | 構文は [language.md §7.7](./language.md#77-条件付きコンパイル)。`.pj` の各ソースと `#include` にも適用する。自動定義は **`_WIN64`（64bit 時）、`_AB_VER4`、`_ACTBA64`**。`_DEBUG` は自動定義せず、`-debug` を付けたときだけ定義する（デバッグ情報 `.abdbg` も書く。デバッガーは作っているところ: [debugger.md](./debugger.md)）。`_ACTBA64` は AB 4.20 には無い |
| `#include` の再取り込み | 同じパスを複数回 `#include` すると、都度展開される | **パス単位で一度だけ**（2 回目以降はスキップ。AB 4.20 の都度展開とは異なる） |
| `On Error` / `Resume` | エラートラップ | 非対応 |

### 言語機能

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| 省略できる引数 | `Function F(a)(ByRef e As Long)` の 2 つ目の括弧 | 対応。省いた引数は 0、`ByRef` は `VarPtr` が 0。2 つ目の括弧がない `Sub` / `Function` も、省いた残りは 0 |
| 関数ポインタの引数型 | 引数型の一致検査 | 厳密照合は未（呼び出し自体は [language.md §5.2.1](./language.md#521-関数ポインタ型)） |

### リソース

| 項目 | ActiveBasic 仕様 (BasicHelp) | ActBa64 |
|---|---|---|
| `rc` ファイル取り込み | リソース埋め込み | **部分対応**（`#resource "file"` → RCDATA 1。`.rc` の ICON / BITMAP は隣の `rc.exe`。MENU は未） |

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
| `Single` / `Double` | IEEE 浮動小数点演算 | **`Single`** の `+` `-` `*` `/` と符号反転は Double で計算して Single に戻す（Single どうしの `/` は Single）。`Print` の Single は `StrS$`（有効 6 桁。`4/3` は `1.33333`）。`Double` の配列要素と UDT フィールドは `-actba32` でも 8 バイト転送。`Print` の Double は 64bit と `-actba32` で `StrD$`（ActiveBasic と同じ有効 15 桁で、`Sqr(5)` は `2.23606797749979`。10^15 以上と 10^-4 未満は `1.5E+20` / `1.5E-5` の形。無限大は `inf`）。指数のリテラル（`1.5e10`）も読む |
| `Class` | `Inherits`、`Virtual` / `Override`、`Super.Method`、`New`/`Delete`、アクセス制御 | `Inherits` は親フィールドを先頭に置く。`Virtual` 呼び出しは vtable。宣言だけの `Virtual` は COM、中身のある `Virtual` は先頭に隠しフィールド `__vptr` を置き、子は `Override` で差し替える（vtable は ctor より前に設定するので、基底の ctor からも子の `Override` が呼ばれる）。`Super` は親関数の直接呼び出し。基底 ctor/dtor は自動で呼ぶ（本体に `Super.Parent(...)` / `Super.~Parent()` があるときは呼ばない）。`New` / `Delete` は対応（ヒープ塊の先頭 24 バイトに要素の大きさ・Dtor・要素数。基底クラスのポインタで `Delete` しても実体の Dtor）。メソッドはマングル名 + 暗黙 `This`（次の行） |
| メソッドの `This` の渡し方 | （BasicHelp に記載なし）AB4.24 は `This` を **ECX** で渡す。宣言だけの `Virtual`（COM）の呼び出しは、ECX に加えて `This` をスタックの第1引数にも積む | `This` は**第1引数**（64bit は RCX、`-actba32` は stdcall の第1引数）。COM の呼び出しも第1引数に `This` を渡すだけ。そのため AB4 で「COM インターフェースの vtable に `AddressOf(obj->Method)` を入れ、`Method` の先頭に `This` を受けるだけの捨て引数（`dummy As Long`）を置く」書き方は、ActBa64 では捨て引数を消す（残すと引数が 1 つずつずれ、`-actba32` ではスタックも壊れる）。vtable やオブジェクトの先頭を `DWord` / `SetDWord` で扱うと 64bit ではアドレスが切れるので、`*VoidPtr` と `SizeOf(*Function)` を使う（`test/t_class_iface_impl.abp`）。宣言だけの `Virtual` を継承した Class の `__vptr` は NULL のままで、`GetDWord(obj)` の先の vtable を書き換える書き方は想定しない。中身のある `Virtual` と `Override` に書き換える（[migrate-ab4.md §1](./migrate-ab4.md#1-vtable-を自分で埋めるコード--virtual-と-override)） |
| 手続き・関数ポインタの `cdecl` | （AB4.24 は `Declare` だけ。`Function F cdecl(...)` と `*Function cdecl(...)` はコンパイルエラー） | `Function F cdecl(...)` / `Sub S cdecl(...)` / `*Function cdecl(...)` を書ける（ActBa64 だけ）。`-actba32` では cdecl の手続きは `ret` で戻り、呼んだ側が片付ける。関数ポインタの呼び出しは呼んだ後に `esp` を戻すので、引数の数が型と違うコールバックでもスタックはずれない（AB4.24 はずれる）。[language.md §3.2](./language.md#32-手続き)、[migrate-ab4.md §2](./migrate-ab4.md#2-引数の数が合わないコールバック--cdecl) |
| N88 `CIRCLE` … `F` | タイルストリングによる塗りつぶし | `F` 塗りつぶしのみ（タイル未対応） |
| 組込 vs Include | `Left$` / `Len` / `InStr` / `Hex$` 等は `basic\function.sbp` 等 | **`Len` / `Asc` / `Chr$` / … / `ELM` / ビットマクロ等は組込**。`InStr` / `Hex$` / `Val` は **`StrUtils.abp`（`default.idx` 自動挿入）**。`GetByte` 等は **`Memory.abp`（同上）** |
| 数学関数 | `Sin` / `Cos` / `Abs` / `Sqr` 等（浮動小数） | **`Math.abp` のマクローリン展開**。複雑な入れ子は一時変数経由が安全 |
| `Int64` / `QWord` / `Char` | 基本型として定義 | 64bit 出力と `-linux` では 64bit の整数。変数・仮引数・Type メンバ（配列のメンバも）・配列・戻り値（Function / メソッド / Declare / 関数ポインタ）が 8 バイトで、算術・比較・`For`・`Select Case`・`Print` / `Str$`・`SizeOf` / `Len` も 64bit。Long は符号で、DWord と 4294967295 までの整数のリテラルは 0 で広げる。4294967295 を超える十進（`9223372036854775807` まで）と 9〜16 桁の `&H` は Int64 のリテラル。QWord は、両辺とも符号なし（QWord・DWord・非負のリテラル）の `\` `Mod` と比較が符号なし、`>>` は論理シフト、Double との変換は 2^63 以上も正しく（符号なしの規則は 64bit の式だけで、DWord どうしの 32bit の演算は従来どおり）。`Val` は Double を経るので 2^53 まで正確。**`-actba32`** も 64bit の整数で、値は `edx:eax` の組（変数・仮引数・ByRef・戻り値（Function / メソッド / Declare）・算術・比較・シフト・`For`・Double との変換・`Print` / `Str$`・リテラル）。`\` `Mod` は ntdll の `_alldiv` などを呼ぶ。**`-actba32` の配列・Type のメンバ・Declare と関数ポインタの仮引数はまだ 32bit** で、そこの `QWord` を `DWord`、`Int64` を `Long` として読み `64-bit integers are not supported` の警告を出す。`DWord` は Double への変換だけ符号なし（DWord の配列・ポインタ先・`Function As DWord` の戻り値は Long と同じ）。型の位置（`As` / `SizeOf(` の後ろ）の **`Char` は `Byte`**（変数名の `char` はそのまま） |
| DLL 再配置 | ロード時のベース再配置 | DLL は末尾に `.reloc` を出す。32bit は絶対アドレスの HIGHLOW。64bit は空の再配置表（コードは RIP 相対）。EXE は出さない。`DYNAMIC_BASE` は立てないので、優先ベースが空いていればそのまま、塞がっていればローダーが移動する |
| 例外の巻き戻し情報（`.pdata`） | （AB4 は 32bit のみ） | 64bit の Windows の exe / DLL は `.pdata` を出す（`PeUnwind.abp`）。手続きはどれも `push rbp; mov rbp, rsp; sub rsp, N` で始まるので、rbp をフレーム レジスタにした UNWIND_INFO 1 つを全部の関数で共有する。これで OS が例外を配るときや `RtlCaptureStackBackTrace` で呼び出し履歴をたどれ、NULL の参照などはデバッガー無しでも c0000005 で終わる（以前は新しい Windows で c0000409 の fail fast になることがあった。`test/t_unwind_null.abp` / `t_unwind_walk.abp`）。`-actba32`（ebp の鎖）と `-linux` は出さない |
| `Function` の `As` 省略 | 戻り値の型を省くと既定の型（Double） | 戻り値は **Double**。戻り値に代入しなければ 0。型を推定できないので `cannot infer the type of Function 'f'; treated as Double` の警告を出す（コンパイルは続ける）。クラスのメソッドで `As` を省いた `Function` は従来どおり Long |
| `Const` の再定義 | 同じ名前の定数は一度だけ定義する | **同じ名前・同じ値（数値・Double・文字列とも）の再定義はエラーにしない**。標準ヘッダ（`default.idx`）が定義する `MB_OK` などを、ユーザのソースでも同じ値で定義していることがあるため。**値が違えば、後ろの定義の行で `Const 'a' is already defined with a different value` のエラー**。組込みの `TRUE` / `FALSE` は対象外（ソースで定義し直しても、組込みの値のまま） |
| ソース拡張子 | `.sbp` 推奨 | **メインのコードは `.abp`**（Active Basic Program。`.pj` で結合）、`#include` で読むファイルは `.sbp`（Sub Basic Program） |
| 呼ばれない手続き | 呼ばれない Function / Sub はコンパイルしない | 構文エラーのある最上位の Function / Sub は、名前がほかから参照されていなければエラーにせず読み飛ばす（参照されていれば元のエラー）。**構文は通るがコード生成で失敗した手続き・メソッド（未定義の名前など）も、本体（main）と Export からたどれなければエラーにせず、空の本体で出す**。たどれれば元のエラー |
| 名前の大文字小文字 | 区別しない | **型・フィールド・メソッド名は区別しない**。関数・`Declare`・`Const` は完全一致を先に探し、無ければ区別せずに探す（`printf` を `Printf` で呼べる。組込みの `TRUE` と、`common\bool.abp` の `true` = -1 は別のまま） |
| オーバーロード | 引数の数・型の違う同名の Function / Sub / メソッド / コンストラクタ | 2 つ目からの定義を内部で `name#2` … にし、呼び出しの引数の数と種類（整数・実数・ポインタ・構造体・文字列）で選ぶ。引数まで同じ定義は `already defined` |
| 前方参照の型 | 後ろで定義する型を使える | `TypeDef` / `Enum` も先に名前と大きさを登録する。値で持つフィールドの型が後ろで定義される `Type` / `Class` は、字句の並びでその型の後ろへ移してから読む |
| `Len` | 文字列は文字数、それ以外は変数・式のバイト数 | 文字列・`BytePtr`・Byte 配列・関数の戻り値は文字列の長さ。数値のスカラー変数・数値の配列・数値リテラル・数値の式はバイト数（`Len(len)` = 配列全体、`Len(0)` = 4）。`len` のように組み込み関数と同じ名前の変数も、`(` が続かなければ変数 |
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
- ステータスバーへの `SendMessage` の `SB_SETTEXT` / `SB_SETTIPTEXT` は、UTF-8 をワイド文字にして `SB_SETTEXTW` / `SB_SETTIPTEXTW` で送る。`CreateStatusWindow` の窓は Unicode なので、A 版のままだと UTF-8 が CP932 として表示され文字化けするため。窓のクラスが `msctls_statusbar32` のときだけ変換し、ほかのコントロールの `WM_USER+1` などはそのまま。妥当な UTF-8 でなければ A 版のまま。`SB_GETTEXT` は A 版のままなので CP932 を返す。
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
  - シェーダー・入力レイアウト・バッファの作成は [`dx_shader.sbp`](../src/Include/d3d11/dx_shader.sbp)（`dx_graphics.sbp` が取り込む）。`dx_CreateShaders(hlsl, pVS, pPS, pVSBlob)` は入口 `VS` / `PS`（`vs_4_0` / `ps_4_0`）をコンパイルして両シェーダーを作る。`dx_PosColorHlsl$()` は位置 float3 + 色 float4（28 バイト）の頂点のシェーダーで、`dx_CreatePosColorLayout(pVSBlob, pLayout)` がその入力レイアウトを作る（`pVSBlob` はここで Release する）。`dx_CreateBuffer(byteWidth, bindFlags, pData, pBuf)` は `D3D11_USAGE_DEFAULT` のバッファ。どれも成功で 1 を返し、失敗は `dx_FailStep` が手順の名前と HRESULT を出す。`dx_ReleaseCom(p)` は 0 でなければ Release して 0 にする。

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
| `rc` / `#resource` | リソースファイル取り込み | ファイル→RCDATA(1) は済。ICON / BITMAP は隣の `rc.exe`。MENU は未 |

### GUI・Win32・マルチメディア

| 項目 | ActiveBasic 仕様 (BasicHelp) | メモ |
|---|---|---|
| DirectX 9 Include | `Include\directx9\`（`d3d9` / `d3dx9*` / `dinput` / `dsound` / `dmusic*`） | **未移植**。D3D11 基盤はサンプルで動作。`dx_input`・`dx_music` 相当は未 |
| RAD | Project Editor | 機能拡充予定 |
| Prompt 窓 | `basic\prompt.sbp`（`PromptProc` / `DrawPromptBuffer`） | 未移植。`Print` / `Input` はコンソール。`Inkey$` / `Input$` は `#n88basic` のみ |
| デバッガランタイム | `system\debug.sbp` の `_DebugSys_*` | IDE デバッガ用。移植しない（ActBa64 のデバッガーは別プロセスの `abdbg.exe` と `.abdbg` を使う。[debugger.md](./debugger.md)） |

