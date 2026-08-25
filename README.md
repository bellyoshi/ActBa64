# ActBa64

ActiveBasic 互換のサブセットコンパイラです。完全互換ではありません。

| 成果物 | 役割 |
|---|---|
| `actba64.exe` | ActiveBasic サブセット → **64bit PE（PE32+）** |
| `actba32.exe` | ActiveBasic サブセット → **32bit PE**（内部で `abc` / `abassembler` / `ablinker` を呼ぶ） |

## 構成

| パス | 内容 |
|---|---|
| `src/Include` | 標準ヘッダ（actba32 / actba64 / エディタ共通） |
| `src/actba32` | 32bit ツールチェーン（`actba32` / `abc` / `abassembler` / `ablinker`）の自己ホスト |
| `src/actba64` | 64bit コンパイラ（actba32 からブートストラップ） |
| `src/projecteditor` | エディタ |
| `release/` | 配布一式（`build.ps1` が生成。git 管理外） |
| `src/prototype*` | 開発途中の試作 |
| `docs/` | ドキュメント（[一覧](docs/index.md)） |

## ドキュメント

- [ビルド手順](docs/build.md)
- [言語仕様](docs/language.md)
- [ActiveBasic との相違](docs/different.md)
- エディタ向けリファレンス: [src/projecteditor/help/actba64_ref.html](src/projecteditor/help/actba64_ref.html)（F1）

## ビルド

詳細は [docs/build.md](docs/build.md)。要約:

```powershell
# リリース一式（要: src\actba32\bin\stage0 に ab420 成果物）
# → release\ に ProjectEditor.exe / actba64.exe / actba32.exe / Include / help
.\build.ps1

# 既存 stage2 だけ使い、エディタ再コンパイルとコピーのみ
.\build.ps1 -SkipSelfHost
```

段階ごとの手動ビルド:

```powershell
# 1) 32bit（要: bin\stage0 に ab420 成果物）
cd src\actba32
.\selfbuild.ps1

# 2) 64bit
cd ..\actba64
.\build.ps1
.\run_test2.ps1 stage2
```

## 使い方

```text
actba64 <src.abp|.pj> -o <out.exe>
actba32 <src.abp|.pj> [-o <out.exe>]
```

例:

```powershell
.\bin\stage2\actba64.exe hello.abp -o hello.exe

# N88BASIC 図形（640x480）
.\bin\stage2\actba64.exe .\samples\n88_shapes.abp -o .\samples\n88_shapes.exe
```

`#n88basic` で `LINE` / `CIRCLE` が使えます。`Sleep` と千分率の `Math`（`Sin` / `Cos` 等）は標準ヘッダから常時利用できます。詳細は [docs/language.md](docs/language.md)。
