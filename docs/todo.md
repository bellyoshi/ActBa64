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

（当面なし。次は P1）

### P1 — 言語・相互運用

- **D3D11**: `dx_SetProjection` / `dx_SetCamera` 相当 — `dxxform` 以上のカメラ・射影の共通化

### P2 — OOP・メディア・規模

- **`Super.*`**、メンバ Class の自動 ctor/dtor
- **厳密 `Protected` / `Private`**（受理のみ。Public と同等）
- **`Const` マクロ関数**, **ネスト手続き**
- **`Int64` / `QWord` / `Char`** と算術
- **`Single` IEEE 演算**（格納と Input 変換が中心。汎用 SSE は未）
- **`Double` 配列要素・UDT フィールド @ `-actba32`** — 要素とフィールドのロード／ストアは `OP_LOAD_QWORD` / `OP_STORE_QWORD` のまま（32bit では 4 バイト）
- **符号無し演算**の AB 4.20 ルール完全化
- **DirectX 高レベル**: `CImage2D` / `CMeshModel` / `CRectPolygon`、`dx_input` / `dx_music` の D3D11・XAudio2 等への置き換え
- **`InitProc` / `RenderProc` 雛形**: `.pj` テンプレート化（RAD 全面再現の前段）
- **Win32 `api_*.sbp` 増分**: 需要に応じ `Declare` / idx 追加
- **DLL の再配置（`.reloc`）**: 優先ベース（64bit `0x180000000` / 32bit `0x10000000`）が塞がるとロード失敗

### P3 — 保留・非推奨に近い

- **`GoTo` / `GoSub` / `Return`（`*ラベル`）** — 方針上導入しない。エディタ変換は別件
- **`On Error` / `Resume`** — 現代コードでは優先低。デバッガ・明示チェックを推奨
- **`Let`**, **`Print Using`** — 糖衣。`Print` / `Format` 系 Include で足りる
- **`CDbl` / `CInt` 関数群** — `As` キャストで代替可

---

## 言語・構文

| 項目 | メモ（AB 4.20 参照） |
|---|---|
| `Super.Method` | スーパークラス ctor/dtor 呼び出し（4.20 Class 章） |
| 厳密な `Protected` / `Private` | 受理するが Public と同等 |
| メンバ Class の自動 ctor/dtor | 親 Class 内のメンバ Class 生成・破棄（4.20） |
| `GoTo` / `GoSub` / `Return`（`*ラベル`） | 行番号は非対応方針。ラベル付き分岐・復帰も未 |
| `On Error` / `Resume` | エラートラップ（4.20 制御命令） |
| プリプロセス自動定義 | `_WIN64` / `_AB_VER4` 等は有。`_DEBUG` の自動定義は要確認 |
| `#resource` の `.rc` / ICON・MENU | `rc.exe` 連携・型付きリソースは未 |
| `Let` | 明示代入（4.20）。優先度低（`=` のみ） |
| `Const name(arglist) = expr` | マクロ定数関数（4.20 Const 章） |
| ネスト手続き | 4.20 は Sub/Function 内定義可 |
| `Print Using "fmt"` | 書式付き出力（4.20 関数ポインタサンプル等） |
| 関数ポインタの厳密シグネチャ照合 | 引数型の照合は未 |
| `Char` / `Int64` / `QWord` | 4.20 基本型一覧。ActBa64 は `Byte`/`Long`/`DWord` 中心 |

## 数値・型

| 項目 | メモ（AB 4.20 参照） |
|---|---|
| `Double` 配列・UDT フィールドを `-actba32` で | 要素とフィールドの 8 バイト転送は未 |
| `Single` の汎用演算 | 4.20 は IEEE 浮動小数。格納と Input 変換が中心 |
| 符号無し演算 | 4.20: 両オペランドが符号無し型なら符号無し演算 |
| `LongLong` / `QWord` / `Int64` 算術 | 4.20 基本型。型・算術とも未 |
| `CDbl` / `CInt` / `CSng` 等 | 4.20 変換関数。`As` キャストは可 |

## 文字列・メモリ・ファイル

| 項目 | メモ（AB 4.20 参照） |
|---|---|
| `realloc` | 4.20 C ヒープ。未 |

## GUI・Win32・マルチメディア

| 項目 | メモ（AB 4.20 参照） |
|---|---|
| Project Editor / RAD | 4.20 のウィンドウ RAD・`MainWnd.sbp` 雛形の全面再現は未 |
| `InitProc` / `QuitProc` / `RenderProc` / `InputActionProc` | 4.20 DirectX プロジェクトのフック。手書きメッセージループで代替 |
| Win32 `api_*.sbp` 全量 | 4.20 は 382 関数超。主要 API は `default.idx` + `Declare` |
| ICON / MENU 等の型付きリソース | LoadIcon/LoadMenu 向けは未 |

### DirectX（4.20 は D3D9 + `dx_*.sbp` → ActBa64 は D3D11 で段階的に）

| 4.20（D3D9 系） | ActBa64 | メモ |
|---|---|---|
| `dx_SetProjection` / `dx_SetCamera` / `dx_SetCullMode` | 未（サンプル側に個別実装あり） | カメラ・射影の共通化は P1 |
| `dx_SetDefaultLight` / `dx_SetLightOff` | 未 | ライト |
| `CImage2D` / `CMeshModel` / `CRectPolygon` | 未 | 高レベル描画 |
| `CInputKeyboard` / `CInputMouse` | 未 | `dx_input.sbp`（DirectInput） |
| `CAudio` / `CAudio3D` / `CListener` | 未 | `dx_music.sbp` |
| `dx_ui.sbp` 等 | UI ラッパは未 | キー・TextOut 以上は未 |

## 標準ライブラリ

- BasicHelp の `basic\*.sbp` / `system\*.sbp` 相当を `.abp` として増やす（4.20 目録: `basic\function.sbp`, `basic\prompt.sbp`, `system\string.sbp` など）
- 4.20 の `#N88BASIC As EXE` / `IDNAME` 相当（実行ファイル名・サブシステム指定）は `.pj` / CLI で代替検討
