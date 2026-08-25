# ActiveBasic との相違点

完全互換ではない。言語の共通核は [language.md](./language.md)、ビルドは [build.md](./build.md)。

## 対応しないこと

### 行番号

- **行番号非対応**
  - 言語仕様をシンプルに保つため、`10 PRINT ...` のような行番号付き記述には対応しない。
  - 将来的に、エディター側で「行番号 → ラベル」へ自動変換してからコンパイルできるようにする可能性はあるが、言語仕様として行番号を導入する予定はない。

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
| DirectX | 当時 DirectX 9。現状は 11 向けから検討 |
| RAD | Project Editor の機能拡充 |

### 標準ライブラリ

- **`Include` の拡充** — ユーティリティや共通モジュールを増やし、再利用しやすくする
