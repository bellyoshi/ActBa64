# ビルド手順

ActBa64 は 2 段のブートストラップです。

1. **actba32** — 32bit ツールチェーン（`actba32` / `abc` / `abassembler` / `ablinker`）を自己ホスト
2. **actba64** — actba32 の成果物で 64bit コンパイラ `actba64.exe`（PE32+）をビルドし、自己コンパイルで固定点を確認

前提 OS: Windows（PowerShell）

---

## 1. actba32（ホスト）

作業ディレクトリ: `src\actba32`

### 1.1 stage0（手動・AB4.20）

ActiveBasic 4.20（ab420）で次の `.pj` をビルドし、`bin\stage0\` に置く。

| プロジェクト | 出力 |
|---|---|
| `abc.pj` | `bin\stage0\abc.exe` |
| `abassembler.pj` | `bin\stage0\abassembler.exe` |
| `ablinker.pj` | `bin\stage0\ablinker.exe` |
| `actba32.pj` | `bin\stage0\actba32.exe` |

`actba32` は **同じディレクトリ** の `abc` / `abassembler` / `ablinker` を呼ぶため、4 本そろえること。

`.pj` の `#OUTPUT_RELEASE` は `bin\stage0\` 向け。CLI の `-o` があればそちらの方が優先される。

旧名 `abpc.exe` が stage0 にある場合、`selfbuild.ps1` が `actba32.exe` へ自動リネームする。

### 1.2 stage1 / stage2（セルフホスト）

```powershell
cd src\actba32
.\selfbuild.ps1              # stage0 → stage1 → stage2 + 比較
.\selfbuild.ps1 -Stage1Only  # stage1 まで
.\selfbuild.ps1 -SkipCompare # 比較スキップ
```

手動相当:

```text
bin\stage0\actba32.exe abc.pj         -o bin\stage1\abc.exe
bin\stage0\actba32.exe abassembler.pj -o bin\stage1\abassembler.exe
bin\stage0\actba32.exe ablinker.pj    -o bin\stage1\ablinker.exe
bin\stage0\actba32.exe actba32.pj     -o bin\stage1\actba32.exe

bin\stage1\actba32.exe ...            -o bin\stage2\...
```

合格の目安: `bin\stage1\` と `bin\stage2\` の exe が一致（または同等に動作）すること。  
不一致でもビルド自体は成功扱いになる場合がある（`selfbuild.ps1` の比較は通知のみ）。

### 1.3 回帰テスト

```powershell
.\run_test2.ps1                 # stage0（既定）
.\run_test2.ps1 stage1
.\run_test2.ps1 stage2
.\run_test2.ps1 stage0 stage1 stage2
```

詳細: [src/actba32/README.md](../src/actba32/README.md) / [言語仕様](./language.md) / [abc-spec.md](../src/actba32/abc-spec.md)

---

## 2. actba64（本リポジトリの主成果物）

作業ディレクトリ: `src\actba64`

**前提:** `src\actba32\bin\stage2\` にツール 4 本があること（上記 §1 完了後）。

### 2.1 ステージ構成

| ステージ | 内容 |
|---|---|
| stage0 | `actba32\bin\stage2` を `bin\stage0` へコピー（32bit ブートストラップ） |
| stage1 | stage0 の `actba32` で `actba64.exe` をビルド |
| stage2 | stage1 の `actba64` で自己コンパイル |
| stage3 | stage2 の `actba64` で再コンパイル |
| 比較 | stage2 と stage3 の SHA256 一致（自己ホスト固定点） |

### 2.2 ビルド

```powershell
cd src\actba64
.\build.ps1                 # 全段階 + stage2/stage3 比較
.\build.ps1 -SkipCopy       # stage0 コピーをスキップ（既存 bin\stage0 を使用）
.\build.ps1 -Stage1Only     # stage1 まで
.\build.ps1 -SkipStage1     # 既存 stage1 を使い stage2/stage3 のみ
.\build.ps1 -SkipCompare    # バイナリ比較をスキップ
```

成功時の主成果物: `bin\stage2\actba64.exe`（固定点確認後は stage3 も同一）

使い方:

```text
actba64 <src.abp|.pj> -o <out.exe>
```

### 2.3 回帰テスト

`test\` 内の `' Target: actba64` 付き `.abp` / `.pj` をコンパイルして実行する。

```powershell
.\run_test2.ps1                 # bin\stage1\actba64.exe（既定）
.\run_test2.ps1 stage2
.\run_test2.ps1 stage3
.\run_test2.ps1 -Rebuild        # 先に build.ps1（stage1 時は -Stage1Only）
.\run_test2.ps1 -IncludeGui     # Gui: 1 のテストも実行
.\run_test2.ps1 -KeepArtifacts  # 生成 exe を残す
```

テスト先頭コメントの意味:

| メタ | 意味 |
|---|---|
| `' Target: actba64` | このランナーの対象（必須） |
| `' Expect: N` | 終了コード期待値（省略時 0） |
| `' Gui: 1` | 対話 UI 想定。既定は SKIP（`-IncludeGui` で有効） |

---

## 3. よくある失敗

| 症状 | 対処 |
|---|---|
| `source not found: ...\actba32\bin\stage2` | 先に `src\actba32` で `.\selfbuild.ps1` を完走する |
| `stage0 missing: ...\actba32.exe` 等 | ab420 で stage0 の 4 本を揃える（旧 `abpc.exe` は自動リネーム可） |
| `actba32 not found` / 子ツール not found | `actba32` と同じディレクトリに `abc` / `abassembler` / `ablinker` があるか確認 |
| stage2 vs stage3 が DIFF | ソース変更直後など。意図どおりなら `-SkipCompare` で継続し、原因を別途調査 |
| テストで `linker not found` | 先に `.\build.ps1`（または `-Rebuild`）を実行する |
