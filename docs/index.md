# ActBa64 ドキュメント

ActBa64 は、ActiveBasic（4.20 / 4.24）の言語の大部分をコンパイルするコンパイラです。ActiveBasic 自身で書かれています。「ActiveBasic で ActiveBasic もどきを作ったらどうなるか？」という実験から始まり、今では自分自身・リソースコンパイラ・専用エディタをすべて自分でコンパイルできるツールチェーンになりました。

目標は、既存の ActiveBasic のプログラムを **ソースを書き換えずに** コンパイルして動かすことです。ただし本ツールチェインは、ActiveBasicを参考に独自に実装したものであり、完全な互換性は有していません。仕様や挙動が一部異なる場合があります。違いは [ActiveBasic との相違](./different.md) にまとめています。

ActBa64 は非公式のプロジェクトであり、ActiveBasic の開発元である Discoversoft とは無関係です。

## 重要

ご自身のソースはバックアップとって確かめてください。
CallBack.wbpとMakeWindow.wbpをProjectEditorが書き換えます。これらが完全になっていないため、ActiveBasicのコードを破壊する可能性があります。

ダウンロードは[こちら](https://github.com/bellyoshi/ActBa64/releases)

## Hello World

1. `ProjectEditor.exe` を起動します。
2. 次のコードを書きます。

   ```
   Print "Hello World!"
   ```

3. メニュー **Basic** → **実行（終了後に待機）** を選びます。

コンソールが開き、`Hello World!` が表示されます。

4. ファイルメニューから名前を付けて保存を選び、保存ダイアログで適切なファイル名を入力します（例: `Hello.abp`）。

## 動かないコードの報告

「私の ActiveBasic で作ったコードが動かないよ」という方は、[Issues](https://github.com/bellyoshi/ActBa64/issues) に投稿していただけると対応していきます。

動かないコードと、お使いの ActiveBasic のバージョンもあると助かります。

## 仕様・手順

| 文書 | 内容 |
|---|---|
| [language.md](./language.md) | 言語仕様（ソース・構文・型・IEEE Double・ファイル I/O・標準ライブラリ、32/64 ターゲット） |
| [PE+32.md](./PE+32.md) | PE32+（64bit）と PE32（32bit、`-actba32`）の出力 |
| [string-gc.md](./string-gc.md) | String GC（ハイブリッドマーク掃き出しの設計・BSS レイアウト・セーフポイント） |
| [build.md](./build.md) | ビルド手順（AB4.20 stage0 → 自己ホスト → リリース一式）、統合テスト、[コンパイラソース分割](./build.md#コンパイラソースの分割) |
| [debugger.md](./debugger.md) | デバッガー（`-debug` の `.abdbg` の形式、`Debug` 文、abdbg.exe のコマンドと答え、段階） |
| [projecteditor.md](./projecteditor.md) | ProjectEditor（MDI、プロジェクト、コンパイル / 実行、ヘルプ、表示言語） |
| [coding.md](./coding.md) | コーディング規約（ファイル **目標 400 / 上限 1000 行**・関数 **10 行以内**） |
| [activebasic-versions.md](./activebasic-versions.md) | 対応する ActiveBasic のバージョン（3.10 / 3.13 / 4.23 / 4.24。5.0 と 2.62 以前の扱い） |
| [different.md](./different.md) | ActiveBasic との相違点（非対応・改良点・今後の予定） |
| [migrate-ab4.md](./migrate-ab4.md) | AB4 のコードを移すときの直し方（vtable を自分で埋めるコード → `Override`、引数の数が合わないコールバック → `cdecl`） |
| [known.md](./known.md) | 既知の問題（AB 4.20 と同じ挙動。`TRUE` と関係演算、識別子の大小区別） |
| [todo.md](./todo.md) | 未実装・今後の作業メモ |
| [release-notes.md](./release-notes.md) | リリースノート（v0.0.3 からの変更点） |

エディタ向けリファレンス（F1）: [src/projecteditor/help/actba64_ref.html](../src/projecteditor/help/actba64_ref.html)

## 資料・メモ

| 文書 | 内容 |
|---|---|
| [book/ActiveBasic.md](./book/ActiveBasic.md) | ActiveBasic の来歴と入手先 |
| [book/ActiveBasicで作られたソフト.md](./book/ActiveBasicで作られたソフト.md) | ActiveBasic 製ソフトのリンク集 |
| [notes/abassembler-const-limit.md](./notes/abassembler-const-limit.md) | abassembler の `too many Const` 失敗と対処の記録 |

## ソース側の関連文書

旧 `actba32` / `abc` / `abassembler` / `ablinker` は廃止済み。32bit 出力は `actba64 -actba32`（共通 IR → x86 + PE32、[PE+32.md](./PE+32.md)）。試作は `src/prototype*`。
