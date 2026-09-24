# 未実装・今後の作業

実装状況の正本は [language.md](./language.md)。ActiveBasic との差分の詳細は [different.md](./different.md)。

**AB 4.20 ヘルプ（テキスト）:** ローカル参照 `docs/ActiveBasic4.20.md`（gitignore）。本書は BasicHelp.html の抽出であり、以下はその記載と ActBa64 実装の差分メモ。

**意図的に対応しない（todo 対象外）**

- 行番号付きソース、`Goto` / `GoSub` の行番号参照（ラベル `*` 分岐も未対応）
- DirectX 9 / `d3d9types.sbp` / `dx_graphics.sbp`（D3D9）— 代わりに **D3D11**（`Include/d3d11/`・サンプル `dx_d3d11.sbp`）

## 実装優先度

判断の目安: **4.20 資産の移植しやすさ**、**Win32/COM/D3D11 サンプルの完成度**、**言語核の穴埋め**、**エディタ UX**。優先度は随時見直す。

| 段階 | 意味 |
|---|---|
| **P0** | 次に手を付ける候補。移植・CI・代表サンプルで詰まりやすい |
| **P1** | P0 の後。互換・生産性が上がるが代替手段あり |
| **P2** | 中長期。ゲーム/メディア/RAD や大規模 Include |
| **P3** | 低優先・方針未定。明示 `Let` など |

### P0 — 移植・基盤

- ~~**標準ライブラリ**~~: 済（`StrUtils.abp` → `default.idx`）
- ~~**Ex 文字列 `Ex"..."`**~~: 済（`test/t_ex_string.abp`）
- ~~**ファイル I/O 仕上げ**~~: 済（`Eof` / `Loc` / `Lof`、`Print #` — `BasicFile.abp`）
- ~~**ビットマクロ**~~: 済（組込 + テスト）
- ~~**プリプロセス**~~: 済（`#define` / `#ifdef` 等 + テスト）
- **D3D11 共通 API**: サンプル横断の `dx_Init` / `dx_Quit` / クリア・Present の形を `Include/d3d11/` に寄せ、`dx_DrawText`（または相当）で 4.20 Hello World 相当
- **ProjectEditor**: ソース読込速度・スクロールちらつき（日常開発のボトルネック）

### P1 — 言語・相互運用

- ~~**`Enum`**~~: 済（`test/t_enum.abp`）
- ~~**`#strict`**~~: 済（代入の型不一致を **warning**。`As` キャストで抑制。`Include\default` は対象外。`test/t_strict_*.abp`）
- ~~**`Continue`**~~: 済（`test/t_continue.abp`）
- ~~**`Type Align(n)`**~~: 済（`Type Name Align(n)` — `test/t_type_align.abp`）
- ~~**`ELM(n)`**~~: 済（組込）
- ~~**`Input "prompt", var`**~~: 済（`test/t_input_prompt.abp`）
- ~~**`GetByte` / `Set*` 系**~~: 済（`Memory.abp` → `default.idx`）
- ~~**乱数**~~: 済（`Randomize` / `Rnd` — `test/t_rnd.abp`）。~~**Math `Log` / `Int` / `Fix` / 三角**~~: 済（IEEE Double `Math.abp` — `test/t_math_*.abp`）

- **`#resource` / `.rc`**: GUI アイコン・メニュー ID の本格運用
- **関数ポインタ型**: `CreateThread` / コールバックで型安全に（`AddressOf` は済）
- **D3D11**: `dx_SetProjection` / `dx_SetCamera` / `dx_GetDevice` 相当 — `dxxform` 以上の共通化
- **ProjectEditor**: スクロールバー、コンソール実行後にウィンドウを閉じない、日本語メニュー

### P2 — OOP・メディア・規模

- **`New` / `Delete` 演算子**、`Sub ~ClassName`、**`Super.*`**、メンバ Class の自動 ctor/dtor
- **厳密 `Protected` / `Private`**
- **`ReDim`**, **`Const` マクロ関数**, **ネスト手続き**
- **`Int64` / `QWord` / `Char`** と算術（64bit ポインタは済）
- **`Single` IEEE 演算**（`Double` / `Math.abp` は済。Single の汎用 SSE は未）

- **`Double` @ `-actba32`**
- **符号無し演算**の AB 4.20 ルール完全化
- **BASIC 命令**: `Window` / `MsgBox` / `Inkey$` 等（API 代替で足りるなら Include のみ）
- **DirectX 高レベル**: `CImage2D` / `CMeshModel` / `CRectPolygon`、`dx_input` / `dx_music` の D3D11・XAudio2 等への置き換え
- **`InitProc` / `RenderProc` 雛形**: `.pj` テンプレート化（RAD 全面再現の前段）
- **Win32 `api_*.sbp` 増分**: 需要に応じ `Declare` / idx 追加

### P3 — 保留・非推奨に近い

- **`GoTo` / `GoSub` / `Return`（`*ラベル`）** — 方針上導入しない。エディタ変換は別件
- **`On Error` / `Resume`** — 現代コードでは優先低。デバッガ・明示チェックを推奨
- **`Let`**, **`Print Using`** — 糖衣。`Print` / `Format` 系 Include で足りる
- **`CDbl` / `CInt` 関数群** — `As` キャストで代替可

---

## 言語・構文

| 項目 | メモ（AB 4.20 参照） |
|---|---|
| `New` / `Delete` | `New [num] Class[(params)]` / `Delete pObj`（4.20）。`Dim As Class(args)` で ctor は呼べる。演算子は未 |
| `Super.Method` | スーパークラス ctor/dtor 呼び出し（4.20 Class 章）。`Inherits` / `Virtual` は COM/vtable 向けに部分対応済 |
| 厳密な `Protected` / `Private` | 受理するが Public と同等 |
| メンバ Class の自動 ctor/dtor | 親 Class 内のメンバ Class 生成・破棄（4.20） |
| デストラクタ `Sub ~ClassName` | 明示 dtor 構文（4.20）。COM 向けは別途 |
| ~~`Continue`~~ | 済 — `For` / `While` / `Do` の先頭へ |
| `GoTo` / `GoSub` / `Return`（`*ラベル`） | 行番号は非対応方針。ラベル付き分岐・復帰も未 |
| `On Error` / `Resume` | エラートラップ（4.20 制御命令） |
| `Enum` … `End Enum` | 列挙型（4.20）。値は DWord 扱い |
| `#define` / `#ifdef` / `#ifndef` / `#else` / `#endif` | 条件コンパイル（済）。4.20 の `_DEBUG` / `_WIN64` 等の**自動定義**は要確認 |
| `#resource` | `*.rc` 取り込み（4.20）。`#RESOURCE` 埋め込みと同系 |
| `#strict` | 厳密型チェック・警告（4.20）。変数代入の型不一致を warning（`As` で抑制） |
| `ReDim` | 動的配列サイズ変更（4.20） |
| `Let` | 明示代入（4.20）。優先度低（`=` のみ） |
| `Const name(arglist) = expr` | マクロ定数関数（4.20 Const 章）。整数・文字列リテラルのみ対応 |
| ネスト手続き | 4.20 は Sub/Function 内定義可 |
| 関数ポインタ型 | `Dim As *Function(...)` / `*Sub(...)`、`TypeDef` で別名（4.20）。`AddressOf` のみ実用 |
| ~~`Type Align(n)`~~ | 済 — `Type Name Align(n)`（n=1,2,4,8,16） |
| ~~`Input "prompt", var`~~ | 済 |
| `Print Using "fmt"` | 書式付き出力（4.20 関数ポインタサンプル等） |
| ~~Ex 文字列 `Ex"..."`~~ | 済 |
| `Char` / `Int64` / `QWord` | 4.20 基本型一覧。ActBa64 は `Byte`/`Long`/`DWord` 中心 |

## 数値・型

| 項目 | メモ（AB 4.20 参照） |
|---|---|
| `Double` を `-actba32` で | 64bit は IEEE 加減乗除・比較・`Function As Double` 済。32bit は SSE 未実装 |
| `Single` の汎用演算 | 4.20 は IEEE 浮動小数。格納と Input 変換が中心 |
| 符号無し演算 | 4.20: 両オペランドが符号無し型なら符号無し演算 |
| `LongLong` / `QWord` / `Int64` 算術 | 4.20 基本型。型・算術とも未 |
| `CDbl` / `CInt` / `CSng` 等 | 4.20 変換関数。`As` キャストは可 |
| ~~`Randomize` / `Rnd`~~ | 済（`Math.abp`、`Rnd` は `[0,1)` Double） |
| ~~`Log` / `Int` / `Fix` / 三角（Math）~~ | 済（IEEE Double。旧千分率は廃止） |

## 文字列・メモリ・ファイル

| 項目 | メモ（AB 4.20 参照） |
|---|---|
| ~~`Print #`~~ | 済（`BasicFile.abp`） |
| ~~`Eof` / `Loc` / `Lof`~~ | 済 |
| ~~`InStr` / `Hex$` / `Val` / `Trim$`~~ | 済（`StrUtils.abp` + `default.idx`）。`Oct$` は未 |
| `ZeroString` / `_splitpath` | `system\string.sbp`（4.20） |
| `GetByte` … `SetDouble` | `Memory.abp`（`default.idx`）。`GetSingle` / `SetSingle` / `GetDouble` / `SetDouble` は未 |
| `realloc` | 4.20 C ヒープ。`calloc` は `HeapAlloc` マップ済 |
| ~~`ELM(n)`~~ | 済（組込） |
| ~~`HIBYTE` / `HIWORD` 等~~ | 済（組込） |

済（`BasicFile.abp`）: `Open` / `Close` / `Input #` / `Write` / `Field` / `Get #` / `Put #`

## GUI・Win32・マルチメディア

| 項目 | メモ（AB 4.20 参照） |
|---|---|
| `Window` / `DelWnd` | `basic\prompt.sbp`（4.20）。Win32 API で代替 |
| `MsgBox` / `Cls` / `Beep` | BASIC 命令（4.20）。`MessageBoxA` 等で代替 |
| `Inkey$` / `Input$(n)` | 4.20 対話入出力 |
| `ChDir` / `Exec` / `Kill` / `MkDir` | 4.20。`CreateProcessA` 等で代替可 |
| `Date$` / `Time$` | 4.20 |
| Project Editor / RAD | 4.20: `.pj`・ウィンドウ RAD・`MainWnd.sbp` 雛形 |
| `InitProc` / `QuitProc` / `RenderProc` / `InputActionProc` | 4.20 DirectX プロジェクトのフック。手書きメッセージループで代替 |
| Win32 `api_*.sbp` 全量 | 4.20 は 382 関数超。主要 API は `default.idx` + `Declare` |
| `#RESOURCE` / `#resource` / `.rc` | リソース埋め込み |

### DirectX（4.20 は D3D9 + `dx_*.sbp` → ActBa64 は D3D11 で段階的に）

| 4.20（D3D9 系） | ActBa64 | メモ |
|---|---|---|
| `dx_Init` / `dx_Quit` / `dx_BeginScene` / `dx_EndScene` / `dx_Present` | サンプル `dx_d3d11.sbp` に相当処理の一部 | 解像度・ウィンドウモード引数など API 形状は未統一 |
| `dx_Clear` / `dx_GetDevice` / `dx_DrawText` | 未 | 4.20 Hello World 手順 |
| `dx_SetProjection` / `dx_SetCamera` / `dx_SetCullMode` | 未 | カメラ・射影 |
| `dx_SetDefaultLight` / `dx_SetLightOff` | 未 | ライト |
| `CImage2D` / `CMeshModel` / `CRectPolygon` | 未 | `dx_graphics.sbp` 高レベル描画 |
| `CInputKeyboard` / `CInputMouse` | 未 | `dx_input.sbp`（DirectInput） |
| `CAudio` / `CAudio3D` / `CListener` | 未 | `dx_music.sbp` |
| `dx_ui.sbp` 等 | `Include/d3d11/dx_ui.sbp` 着手 | UI ラッパ |

済（D3D11 サンプル）: 三角形・頂点色・立方体・行列変換（`dxxform` / `dxcube2` 等）、キーボード簡易入力

## 標準ライブラリ

- BasicHelp の `basic\*.sbp` / `system\*.sbp` 相当を `.abp` として増やす（4.20 目録: `basic\function.sbp`, `basic\prompt.sbp`, `system\string.sbp`, `Math` 系など）
- 4.20 プリプロセス `#console` / `#prompt`（=`#N88BASIC`）は ActBa64 で対応。`#include <...>` の angle 形式も可
- 4.20 の `#N88BASIC As EXE` / `IDNAME` 相当（実行ファイル名・サブシステム指定）は `.pj` / CLI で代替検討

ProjectEditor
-[ ] abpなどのソースの読み込みに時間がかかる
-[ ] スクロールするときにちらつく
-[ ] スクロールバー
-[ ] 日本語メニュー
-[ ] コンソールプログラム。実行後コンソール閉じないように
