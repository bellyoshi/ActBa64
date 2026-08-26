# ActBa64 ドキュメント

ActiveBasic 互換サブセットコンパイラ（完全互換ではない）のドキュメント一覧です。  
リポジトリ全体の概要は [README.md](../README.md) を参照してください。

## 仕様・手順

| 文書 | 内容 |
|---|---|
| [language.md](./language.md) | 言語仕様（ソース・構文・型・標準ライブラリ、32/64 ターゲット） |
| [build.md](./build.md) | ビルド手順（AB4.20 stage0 → 自己ホスト → リリース一式） |
| [different.md](./different.md) | ActiveBasic との相違点（非対応・改良点・今後の予定） |

エディタ向けリファレンス（F1）: [src/projecteditor/help/actba64_ref.html](../src/projecteditor/help/actba64_ref.html)

## 資料・メモ

| 文書 | 内容 |
|---|---|
| [book/ActiveBasicについて.md](./book/ActiveBasicについて.md) | ActiveBasic の来歴と入手先 |
| [book/ActiveBasicで作られたソフト.md](./book/ActiveBasicで作られたソフト.md) | ActiveBasic 製ソフトのリンク集 |
| [notes/abassembler-const-limit.md](./notes/abassembler-const-limit.md) | abassembler の `too many Const` 失敗と対処の記録 |

## ソース側の関連文書

| 文書 | 内容 |
|---|---|
| [src/actba32/README.md](../src/actba32/README.md) | 旧 32bit ツールチェーン（参照用） |
| [src/actba32/abc-spec.md](../src/actba32/abc-spec.md) | 旧 abc 中間段の仕様 |
