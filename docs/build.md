# ビルド手順

ActBa64 は **1 本のコンパイラ** `actba64.exe` です。既定は PE32+ / AMD64、`-actba32` で PE32 / i386 を出します。

ブートストラップ:

1. **stage0** — 人が ActiveBasic 4.20 で `actba64.pj` をビルド（32bit **ホスト**。`#PLATFORM=32` は AB4.20 用で、出力ターゲットではない）
2. **stage1 / stage2** — そのコンパイラが自分自身を 64bit ホストとしてビルド（`-actba32` なし）

前提 OS: Windows（PowerShell）

リポジトリ根の `.\build.ps1` が上記に加えて ProjectEditor を組み、`release\` へ配布一式をコピーする。標準ヘッダは [`src/Include`](../src/Include) の 1 本。

---

## 1. stage0（手動・AB4.20）

作業ディレクトリ: `src\actba64`

ActiveBasic 4.20 で `actba64.pj` をビルドし、`bin\stage0\actba64.exe` に置く（`.pj` の `#OUTPUT_RELEASE` も同じパス）。`bin\stage0` フォルダは先に作ること。

`#PLATFORM=32` は **AB4.20 が 32bit exe を出すため** だけ。コンパイル対象の切替には使わない（対象は CLI の `-actba32`）。

---

## 2. actba64 自己ホスト

作業ディレクトリ: `src\actba64`

**前提:** `bin\stage0\actba64.exe` があること。

| ステージ | 内容 |
|---|---|
| stage0 | AB4.20 で作った 32bit ホスト `actba64.exe` |
| stage1 | stage0 が `actba64.pj` を **64bit** でビルド |
| stage2 | stage1 で自己コンパイル |
| stage3 | stage2 で再コンパイル |
| 比較 | stage2 と stage3 の SHA256 一致 |

```powershell
cd src\actba64
.\build.ps1                 # Include を stage0 へコピー + 全段階 + 比較
.\build.ps1 -SkipCopy       # Include コピーをスキップ
.\build.ps1 -Stage1Only     # stage1 まで
.\build.ps1 -SkipStage1     # 既存 stage1 を使い stage2/stage3 のみ
.\build.ps1 -SkipCompare    # バイナリ比較をスキップ
```

成功時の主成果物: `bin\stage2\actba64.exe`

使い方:

```text
actba64 <src.abp|.pj> [-actba32] -o <out.exe>
```

サンプル:

```powershell
.\bin\stage2\actba64.exe .\samples\n88_shapes.abp -o .\samples\n88_shapes.exe
.\bin\stage2\actba64.exe .\samples\math_test.abp -o .\samples\math_test.exe

# 32bit PE
.\bin\stage2\actba64.exe hello.abp -actba32 -o hello32.exe
```

### 回帰テスト

`test\` 内の `' Target: actba64` 付き `.abp` / `.pj` をコンパイルして実行する。既定 64bit と `-Actba32` の両方で回せる。

```powershell
.\run_test2.ps1                 # bin\stage1\actba64.exe（既定・64bit）
.\run_test2.ps1 stage2
.\run_test2.ps1 stage2 -Actba32 # 同じテストを PE32 で
.\run_test2.ps1 -Rebuild
.\run_test2.ps1 -IncludeGui
.\run_test2.ps1 -KeepArtifacts
```

| メタ | 意味 |
|---|---|
| `' Target: actba64` | このランナーの対象（必須） |
| `' Expect: N` | 終了コード期待値（省略時 0） |
| `' Gui: 1` | 対話 UI 想定。既定は SKIP |
| `' Skip32: 1` | `-Actba32` 時はスキップ（ポインタ幅依存など） |

---

## 3. リリース一式（`release\`）

リポジトリ根で実行する。

```powershell
.\build.ps1                 # actba64 ブートストラップ → ProjectEditor → release\
.\build.ps1 -SkipSelfHost   # 既存 stage2 を使い、エディタ再コンパイルとコピーのみ
.\build.ps1 -SkipCompare
```

| パス | 内容 |
|---|---|
| `release\ProjectEditor.exe` | エディタ（64bit GUI） |
| `release\actba64.exe` | コンパイラ（既定 64bit、`-actba32` で 32bit） |
| `release\Include\` | `src\Include` のコピー |
| `release\help\` | エディタ向け HTML ヘルプ |

`Include` の正本は [`src/Include`](../src/Include) のみ。`VoidPtr` は `*Byte`（ポインタ幅は **コンパイル対象** に従う: 既定 8、`-actba32` で 4）。

前提:

- 初回は `src\actba64\bin\stage0\actba64.exe`（AB4.20）があること
- `src\projecteditor\Callback.wbp` と `MakeWindow.wbp` があること
- `release\ProjectEditor.exe` を起動したままだと上書きに失敗することがある

`release\` は `.gitignore` 対象（`bin\` と同様）。

---

## 4. よくある失敗

| 症状 | 対処 |
|---|---|
| `stage0 missing: ...\actba64.exe` | AB4.20 で `actba64.pj` を `bin\stage0\` にビルドする |
| stage2 vs stage3 が DIFF | ソース変更直後など。`-SkipCompare` で継続し原因を調査 |
| テストで `linker not found` | 先に `.\build.ps1`（または `-Rebuild`） |
| `ProjectEditor RAD file missing` | `Callback.wbp` / `MakeWindow.wbp` を `src\projecteditor\` に置く |
| `copy failed ... release\ProjectEditor.exe` | エディタを終了してから再実行 |
