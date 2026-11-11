# ActBa64

日本語 | [English](README.md)

ActBa64 は、ActiveBasic（4.20 / 4.24）の言語の大部分をコンパイルするコンパイラです。ActiveBasic 自身で書かれています。「ActiveBasic で ActiveBasic もどきを作ったらどうなるか？」という実験から始まり、今では自分自身・リソースコンパイラ・専用エディタをすべて自分でコンパイルできるツールチェーンになりました。

目標は、既存の ActiveBasic のプログラムを **ソースを書き換えずに** コンパイルして動かすことです。ただし、完全に同じ動きをするわけではありません。違いは [ActiveBasic との相違](docs/different.md) にまとめています。

## 特徴

- **1 本のコンパイラで 3 種類の出力。** `actba64.exe` は既定で 64bit の Windows PE（PE32+）を、`-actba32` で 32bit の PE（PE32）を、`-linux` で x86-64 Linux の ELF を出します。字句解析・構文解析・AST・中間表現は共通で、違うのは機械語とファイル形式だけです。
- **セルフホスト。** コンパイラは自分自身をコンパイルし、stage1 と stage2 はバイト単位で一致します。Linux 版のコンパイラも自分自身を再現し、Windows 版と同じ PE を出します。
- **Windows の GUI プログラム。** Win32 API の宣言、ウィンドウクラス、メニュー、ダイアログ、コモンダイアログ、コモンコントロールが使えます。文字列は内部で UTF-8 とし、API に渡すところで UTF-16 に変えるので、日本語が文字化けしません。Shift-JIS のソースもそのまま読めます。
- **言語機能。** クラス（`New` / `Delete`、継承、`Super`、`Virtual`、`Private` / `Protected`）、`Type`、`Enum`、関数ポインタ、`Const` マクロ、IEEE Double の数学関数、ファイル I/O（`Open`、`Input #`、`Print #`、`Field`、`Get #`、`Put #`）、`Print Using`、条件付きコンパイルなど。
- **DLL とリソース。** `#MODULETYPE=1` と `Function Export` で DLL を作れます。`#resource` で `.rc` のアイコンとビットマップを埋め込めます（同梱の `rc.exe` が処理します）。
- **N88-BASIC。** `#N88BASIC` で 640x480 のグラフィック窓（`LINE`、`CIRCLE`、`PSET`、`COLOR`、`LOCATE`、`INKEY$`）が使えます。`-pN88` を付けると、行番号付き・`Dim` なしの昔ながらの N88-BASIC のソースを読みます。
- **libc を使わない Linux 版。** `-linux` はカーネルを直接呼ぶ静的 ELF を出します。コンソール、ファイル、ヒープ、時刻、コマンドライン、子プロセスが使えます。`Lib` に `.so` を書いた `Declare` があると動的リンクの ELF になり、libc や libm を呼べます。
- **DirectX 11。** COM の vtable 経由で呼びます（DirectX 9 は非対応）。サンプルは `src/actba64/samples/dx*` にあります。
- **ProjectEditor。** 64bit の MDI エディタです。プロジェクト（`.pj`）、コンパイルと実行、エラー行へのジャンプ、検索、キーワードの色分け、F1 ヘルプ、日本語 / 英語の表示に対応しています。
- **わかりやすい診断。** エラーと警告は `error: ファイル(行): メッセージ` の形で、1 回のコンパイルで複数報告します。

## ダウンロード

最新版は [GitHub Releases](https://github.com/bellyoshi/ActBa64/releases) から入手できます。好きな場所に展開し、ファイルは同じフォルダにまとめたまま使ってください。

| ファイル | 役割 |
|---|---|
| `ProjectEditor.exe` | エディタ。同一フォルダの `actba64.exe` を呼びます |
| `actba64.exe` | コンパイラ |
| `rc.exe` | リソースコンパイラ。`actba64.exe` に起動されます。 |
| `Include\` | 標準ヘッダ。`actba64.exe` と同一フォルダに置きます |
| `help\` | F1 で開く HTML リファレンス |
| `fonts\`、`ProjectEditor_lang_*.csv`、`keywords.txt`、`setting.ini` | エディタのフォント、表示言語、色分けするキーワード、設定 |

## はじめかた

`hello.abp`:

```vb
#console
Print "Hello World!"
```

```powershell
actba64 hello.abp -o hello.exe              # 64bit Windows
actba64 hello.abp -actba32 -o hello32.exe   # 32bit Windows
actba64 hello.abp -linux -o hello           # x86-64 Linux ELF
```

`ProjectEditor.exe` を開いてプログラムを書き、Basic メニューの「実行」を選んでも動かせます。

### コマンドライン

```text
actba64 <src.abp|.pj> [-actba32] [-linux] [-pN88] [-o <out>]
```

| オプション | 意味 |
|---|---|
| `-o <out>` | 出力先。`.abp` では必須です。`.pj` に `#OUTPUT_RELEASE` があれば省略でき、そのパスは `.pj` のあるフォルダが基準です |
| `-actba32` | 64bit の代わりに 32bit の PE を出す |
| `-linux` | x86-64 Linux の ELF を出す |
| `-pN88` | ソースを N88-BASIC として読む |

プロジェクトファイル（`.pj`）は `#SOURCE` の下にソースを並べ、1 本のプログラムとしてコンパイルします。コンパイルに失敗すると終了コードは 0 以外になります。

## ソースからのビルド

必要なもの: Windows と PowerShell、そして最初のブートストラップのときだけ **ActiveBasic 4.20**。WSL があれば Linux のテストも回ります（無くても構いません）。

1. **stage0**: ActiveBasic 4.20 で `src/actba64/actba64.pj` をビルドし、`src\actba64\bin\stage0\actba64.exe` に置きます（32bit のホスト）。
2. **stage1 / stage2**: stage0 がコンパイラを 64bit でビルドし、できたコンパイラがもう一度自分自身をビルドします。2 つの結果は一致しなければなりません。

```powershell
cd src\actba64
.\build.ps1                     # stage0 → stage1 → stage2 のあと比較
cd ..\..
.\release_build.ps1             # ブートストラップ + rc.exe + ProjectEditor → release\
.\release_build.ps1 -SkipSelfHost   # 既存の stage2 を使う
```

ProjectEditor のビルドには、ActiveBasic の RAD が書く `Callback.wbp` と `MakeWindow.wbp` も `src\projecteditor\` に必要です。詳しい手順とよくある失敗は [docs/build.md](docs/build.md) にあります。

## テスト

```powershell
.\check.ps1 unit           # src\unittest のユニットテスト（コミット前に必ず）
.\check.ps1 integration    # src\actba64\test をコンパイルして実行する統合テスト + WSL での Linux テストと Linux セルフホスト（プッシュ前に必ず）
```

統合テストは、別のステージや 32bit の出力でも回せます。

```powershell
cd src\actba64
.\run_test2.ps1 stage2 -Actba32
.\run_test2.ps1 -IncludeGui     # GUI のテストも実行（既定ではスキップ）
```

## リポジトリの構成

| パス | 内容 |
|---|---|
| `src/actba64` | コンパイラ（字句解析、構文解析、AST から中間表現への変換、x64 / x86 のコード生成、PE と ELF の書き出し）。統合テストの `test/`、`samples/`、`example/` もここ |
| `src/Include` | コンパイラとエディタが共有する標準ヘッダ（`default`、`console`、`N88BASIC`、`d3d11`、`linux`） |
| `src/rc` | リソースコンパイラ（`rc.exe`） |
| `src/projecteditor` | ProjectEditor のソース、ヘルプ、言語ファイル |
| `src/common` | コンパイラとエディタで共有する部品 |
| `src/unittest` | ユニットテスト |
| `src/prototype*` | 初期の試作（旧アセンブラ / リンカ）。今のツールチェーンでは使いません |
| `docs/` | ドキュメント |

## ドキュメント

[docs.actba64.com](https://docs.actba64.com) でも公開しています。

- [言語仕様](docs/language.md)
- [ActiveBasic との相違](docs/different.md)
- [既知の問題](docs/known.md)（ActiveBasic 4.20 と同じ挙動のもの）
- [ビルドとテスト](docs/build.md)
- [ProjectEditor](docs/projecteditor.md)
- [String GC の設計](docs/string-gc.md)
- [コーディング規約](docs/coding.md)
- [リリースノート](docs/release-notes.md)
- [未実装メモ](docs/todo.md)

## 現状

開発中です。主にまだ無いもの: DirectX 9、`On Error` / `Resume`、`Int64` / `QWord` 型、指数表記の数値リテラル、`Single` の一般の演算、`MENU` リソース。`-linux` では `Include\linux` に Linux 版がある API だけが動き、それ以外はコンパイル時に警告します。
