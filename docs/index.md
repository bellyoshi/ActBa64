# ActBa64 ドキュメント

Actba64はActiveBasic 互換サブセットコンパイラ です。

ActiveBasicでActiveBasicもどきをつくったらどうなるか？
という実験プロジェクトです。完全に同じ動きをするわけではありませんのでご了承ください。



リポジトリ全体の概要は [README.md](../README.md) を参照してください。

## 仕様・手順

| 文書 | 内容 |
|---|---|
| [language.md](./language.md) | 言語仕様（ソース・構文・型・IEEE Double・ファイル I/O・標準ライブラリ、32/64 ターゲット） |
| [string-gc.md](./string-gc.md) | String GC（ハイブリッドマーク掃き出しの設計・BSS レイアウト・セーフポイント） |
| [build.md](./build.md) | ビルド手順（AB4.20 stage0 → 自己ホスト → リリース一式）、統合テスト、[コンパイラソース分割](./build.md#コンパイラソースの分割) |
| [projecteditor.md](./projecteditor.md) | ProjectEditor（MDI、プロジェクト、コンパイル / 実行、ヘルプ、表示言語） |
| [coding.md](./coding.md) | コーディング規約（ファイル **目標 400 / 上限 1000 行**・関数 **10 行以内**） |
| [activebasic-versions.md](./activebasic-versions.md) | 対応する ActiveBasic のバージョン（3.10 / 3.13 / 4.23 / 4.24。5.0 と 2.62 以前の扱い） |
| [different.md](./different.md) | ActiveBasic との相違点（非対応・改良点・今後の予定） |
| [known.md](./known.md) | 既知の問題（AB 4.20 と同じ挙動。`TRUE` と関係演算、識別子の大小区別） |
| [todo.md](./todo.md) | 未実装・今後の作業メモ |
| [release-notes.md](./release-notes.md) | リリースノート（v0.0.3 からの変更点） |

エディタ向けリファレンス（F1）: [src/projecteditor/help/actba64_ref.html](../src/projecteditor/help/actba64_ref.html)

## 資料・メモ

| 文書 | 内容 |
|---|---|
| [book/ActiveBasicについて.md](./book/ActiveBasicについて.md) | ActiveBasic の来歴と入手先 |
| [book/ActiveBasicで作られたソフト.md](./book/ActiveBasicで作られたソフト.md) | ActiveBasic 製ソフトのリンク集 |
| [notes/abassembler-const-limit.md](./notes/abassembler-const-limit.md) | abassembler の `too many Const` 失敗と対処の記録 |

## ソース側の関連文書

旧 `actba32` / `abc` / `abassembler` / `ablinker` は廃止済み。32bit 出力は `actba64 -actba32`（共通 IR → x86 + PE32）。試作は `src/prototype*`。
