# ActBa64

ActiveBasic 互換のサブセットコンパイラです。完全互換ではありません。

| 成果物 | 役割 |
|---|---|
| `actba64.exe` | ActiveBasic サブセット → 既定 **64bit PE（PE32+）**。`-actba32` で **32bit PE（PE32）** |

## 構成

| パス | 内容 |
|---|---|
| `src/Include` | 標準ヘッダ（コンパイラ / エディタ共通） |
| `src/actba64` | コンパイラ（Lexer → Parser → AST → IR は共通。機械語と PE だけ 64 / `-actba32` で分岐） |
| `src/projecteditor` | エディタ |
| `release/` | 配布一式（`build.ps1` が生成。git 管理外） |
| `src/prototype*` | 開発途中の試作（旧 abc / アセンブラ / リンカ。現行ツールチェーンではない） |
| `docs/` | ドキュメント（[一覧](docs/index.md)） |

## ドキュメント

- [ビルド手順](docs/build.md)
- [言語仕様](docs/language.md)
- [ActiveBasic との相違](docs/different.md)
- [未実装メモ](docs/todo.md)
- エディタ向けリファレンス: [src/projecteditor/help/actba64_ref.html](src/projecteditor/help/actba64_ref.html)（F1）

## ビルド

詳細は [docs/build.md](docs/build.md)。要約:

```powershell
# 要: src\actba64\bin\stage0\actba64.exe（ActiveBasic 4.20 で actba64.pj をビルド）
# → release\ に ProjectEditor.exe / actba64.exe / Include / help
.\build.ps1

# 既存 stage2 だけ使い、エディタ再コンパイルとコピーのみ
.\build.ps1 -SkipSelfHost
```

段階ごとの手動ビルド:

```powershell
cd src\actba64
.\build.ps1
.\run_test2.ps1 stage2
.\run_test2.ps1 stage2 -Actba32
```

## 使い方

```text
actba64 <src.abp|.pj> [-actba32] -o <out.exe>
```

例:

```powershell
.\bin\stage2\actba64.exe hello.abp -o hello.exe
.\bin\stage2\actba64.exe hello.abp -actba32 -o hello32.exe

# N88BASIC 図形（640x480）
.\bin\stage2\actba64.exe .\samples\n88_shapes.abp -o .\samples\n88_shapes.exe
```

`#n88basic` で `LINE` / `CIRCLE` が使えます。`Sleep` と千分率の `Math`（`Sin` / `Cos` 等）は標準ヘッダから常時利用できます。詳細は [docs/language.md](docs/language.md)。
