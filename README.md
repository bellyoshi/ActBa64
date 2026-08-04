# ActBa64

ActiveBasic 互換のサブセットコンパイラです。完全互換ではありません。

| 成果物 | 役割 |
|---|---|
| `actba64.exe` | ActiveBasic サブセット → **64bit PE（PE32+）** |
| `actba32.exe` | ActiveBasic サブセット → **32bit PE**（内部で `abc` / `abassembler` / `ablinker` を呼ぶ） |

## 構成

| パス | 内容 |
|---|---|
| `src/actba32` | 32bit ツールチェーン（`actba32` / `abc` / `abassembler` / `ablinker`）の自己ホスト |
| `src/actba64` | 64bit コンパイラ（actba32 からブートストラップ） |
| `src/prototype*` | 開発途中の試作 |
| `doc/` | ドキュメント |

## ドキュメント

- [ビルド手順](doc/build.md)
- [言語仕様](doc/language.md)

## ビルド

詳細は [doc/build.md](doc/build.md)。要約:

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
```
