# actba32 — ツール配置とビルド方針

ルートのビルド手順: [doc/build.md](../../doc/build.md)

## ソースツリー

```
actba32/
│
├── *.abp / *.pj / *.idx     # ツールソース（actba32 / abc / abassembler / ablinker）
├── test/                    # 回帰テスト
│
├── bin/                     # 出力先のルート
│   ├── stage0/              # AB4.20（オリジナル 32bit）でビルドした成果物
│   │   └── actba32.exe 等
│   ├── stage1/              # stage0 の actba32 が出力した成果物
│   │   └── actba32.exe 等
│   └── stage2/              # stage1 自身が出力した成果物（完全自立確認用）
│       └── actba32.exe 等
│
├── run_test2.ps1            # 回帰テスト（stage0 / stage1 / stage2）
├── selfbuild.ps1            # stage0 → stage1 → stage2
└── README.md
```

`.pj` の `#OUTPUT_RELEASE` は **`bin\stage0\`**（例: `.\bin\stage0\actba32.exe`）。  
CLI の `-o` は `.pj` の out より優先する。未指定時は `.pj` の out を使う。

## ホスト（stage0）— ab420 / 人間作業

1. ab420 で該当 `.pj` を開く
2. 出力先は `.pj` どおり `bin\stage0\`
3. IDE からビルドする（`actba32` / `abc` / `abassembler` / `ablinker`）

`actba32` は **自分と同じディレクトリ** にある `abc` / `abassembler` / `ablinker` を呼ぶ。  
stage0 にはツール 4 本を揃える。標準ヘッダはリポジトリの `src/Include`（`selfbuild.ps1` が `bin\stage0\Include` へコピーする）。

## セルフホスト（stage1 / stage2）

リポジトリ直下のソースをそのまま使い、出力だけ `bin\stageN\` に分ける。

```powershell
.\selfbuild.ps1              # stage0 → stage1 → stage2 + 比較
.\selfbuild.ps1 -Stage1Only  # stage1 まで
.\selfbuild.ps1 -SkipCompare # 比較スキップ
```

手動相当:

```
# stage0 → stage1
bin\stage0\actba32.exe abc.pj -o bin\stage1\abc.exe
bin\stage0\actba32.exe abassembler.pj -o bin\stage1\abassembler.exe
bin\stage0\actba32.exe ablinker.pj -o bin\stage1\ablinker.exe
bin\stage0\actba32.exe actba32.pj -o bin\stage1\actba32.exe

# stage1 → stage2（自立確認）
bin\stage1\actba32.exe ... -o bin\stage2\...
```

合格の目安: `bin\stage1\` と `bin\stage2\` の exe が一致（または同等に動作）すること。

回帰テスト:

```powershell
.\run_test2.ps1                 # stage0（既定）
.\run_test2.ps1 stage0
.\run_test2.ps1 stage1
.\run_test2.ps1 stage2
.\run_test2.ps1 stage0 stage1 stage2
```

## 関連

- 言語・自己ホスト仕様: [abc-spec.md](./abc-spec.md)
