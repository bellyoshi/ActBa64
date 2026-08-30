# 未実装・今後の作業

実装状況の正本は [language.md](./language.md)。ActiveBasic との差分の詳細は [different.md](./different.md)。

## 言語・構文

| 項目 | メモ |
|---|---|
| `New` / `Delete` | `Dim As Class(args)` で ctor は呼べる。演算子は未 |
| `Super.Method` | `Inherits` / `Virtual` は COM/vtable 向けに部分対応済 |
| 厳密な `Protected` | 受理するが Public と同等 |
| メンバ Class の自動 ctor/dtor | |
| `Continue` | `For` / `While` / `Do` の先頭へ。現状は `Exit` のみ |
| `GoTo` / `GoSub` / `Return`（ラベル） | 行番号も非対応。導入しない方針 |
| `Enum` | |
| `#define` / `#ifdef` | |
| `#strict` | 行は受理するが無視。将来は警告 |
| `ReDim` | |
| `Let` | 優先度低（`=` 代入のみ） |
| ネスト手続き | |
| 関数ポインタの一般化 | `AddressOf` のみ |
| `Input "prompt", var` | 変数のみ対応済 |
| Ex文字列 | BasicHelp 未確認。要調査 |

## 数値・型

| 項目 | メモ |
|---|---|
| `Double` を `-actba32` で | 64bit は加減乗除・比較済。32bit は SSE 未実装 |
| `Single` の汎用演算 | 格納と Input 変換が中心 |
| `LongLong` / `QWord` 算術 | 型なし。ポインタ幅は `LONG_PTR` 等 |
| `CDbl` / `CInt` / `CSng` | `As` キャストは可 |
| `Randomize` / `Rnd` | |
| `Log` / `Int` / `Fix`（Math） | 千分率の `Sin` 等は済 |

## 文字列・メモリ・ファイル

| 項目 | メモ |
|---|---|
| `Open` / `Close` / `Print #` / `Input #` | WinAPI で代替可 |
| `Field` / `Get` / `Put` / `Write` | |
| `Eof` / `Loc` / `Lof` | |
| `InStr` / `Hex$` / `Val` / `Trim$` | `StrUtils.abp` 等（手動 Include） |
| `realloc` | `calloc` は `HeapAlloc` マップ済 |
| `ELM` | |
| `HIBYTE` / `HIWORD` / `MAKELONG` 等 | `LOWORD` のみ組込 |

## GUI・Win32・マルチメディア

| 項目 | メモ |
|---|---|
| `Window` / `DelWnd` / `MsgBox` / `Cls` / `Beep` | Win32 API で代替 |
| `Inkey$` / `Input$(n)` | |
| `ChDir` / `Exec` / `Kill` / `MkDir` | `CreateProcessA` 等で代替可 |
| `Date$` / `Time$` | |
| `#RESOURCE` / RAD 拡充 | |
| D3D11 の `dx_DrawText`・`dx_input`・`dx_music` | 初期化・三角形描画のサンプルは動作 |

## 標準ライブラリ

- BasicHelp の `basic\*.sbp` / `system\*.sbp` 相当を `.abp` として増やす

ProjectEditor
-[ ] abpなどのソースの読み込みに時間がかかる
-[ ] スクロールするときにちらつく
-[ ] スクロールバー
-[ ] 日本語メニュー
-[ ] コンソールプログラム。実行後コンソール閉じないように

Print double → バイナリー表示になっている。