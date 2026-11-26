# デバッガー（計画と進み具合）

ActBa64 で作った exe を、ブレークポイント・ステップ実行・変数の表示ができるデバッガーで動かせるようにする計画です。デバッガーも ActiveBasic（ActBa64）で書きます。

## 全体の作り

```
actba64 -debug ──▶ xxx.exe ＋ xxx.abdbg（デバッグ情報）
                         ▲
abdbg.exe（AB で書くデバッガー本体。Win32 Debug API）
   ▲ 標準入出力でコマンドをやり取りする
ProjectEditor（ブレークポイント・今の行・変数・呼び出し履歴の表示）
```

決めたこと:

- デバッガーは**別のプロセス（`abdbg.exe`）**にする。CLI のままテストでき、エディターが落ちない。Linux 版（ptrace）も同じやり取りで作れる
- デバッグ情報は exe とは**別のファイル `.abdbg`** にする（テキスト。exe の中身は変えない）
- **`-debug` 1 つ**で `_DEBUG` の定義とデバッグ情報の両方を出す（AB4 のデバッグ実行と同じ）

## 段階

| 段階 | 内容 | 状態 |
|---|---|---|
| D0 | コンパイラが `.abdbg` を書く（行の表・手続き・ローカル変数・グローバル変数）。`Debug` 文 | 済 |
| D1 | `abdbg.exe` の土台: 起動・ブレークポイント（`0xCC`）・続行・呼び出し履歴（rbp をたどる）・例外で落ちた行を出す | |
| D2 | ステップオーバー / ステップイン / ステップアウト | |
| D3 | 変数の表示（Long・Int64・Double・ポインタ・String → Type / Class のメンバ・配列） | |
| D4 | ProjectEditor に入れる（余白のクリックでブレークポイント、F5 / F9 / F10 / F11 / Shift+F11、変数・呼び出し履歴の窓） | |
| D5 | 条件付きブレークポイント・ウォッチ・`-actba32`（WOW64）・Linux | |

## `-debug` で出すもの（D0）

`-debug` を付けると、exe と同じ場所に拡張子を `.abdbg` にしたファイルを書きます（`hello.exe` → `hello.abdbg`）。**exe の中身は変わりません**（`#IFDEF _DEBUG` の部分と `Debug` 文のほかはリリースとバイト単位で同じ）。`-linux` では書きません。`-X` と一緒に使うと、消した手続きは `.abdbg` にも出ません。

### `.abdbg` の形式

UTF-8 のテキストで、1 行に 1 件です。数は 10 進、名前とパスは行の最後に置きます（空白を含んでよい）。

```
ABDBG 1
arch x64
text 4096
data 167936
func <番号> <始まりの RVA> <終わりの RVA> <名前>
var <手続きの番号> <off> <ByRef> <kind> <typeIdx> <型> <名前>
file <番号> <フルパス>
line <RVA> <file の番号> <行> <文の始まりなら 1>
```

| 行 | 意味 |
|---|---|
| `arch` | `x64` か `x86`（`-actba32`） |
| `text` / `data` | `.text`（機械語）と `.data`（グローバル変数）の RVA。実際のアドレスは、読み込まれた先頭（ASLR で変わる）＋ RVA |
| `func` | 手続きの範囲（`leave; ret` まで）。モジュールの本体は `(module)`。Include の手続きも出る |
| `var` | 手続きの番号が `-1` ならグローバル変数で、`off` は `.data` の先頭から。ほかはその手続きのローカル変数・仮引数で、`off` は `[rbp+off]`（`-actba32` は `[ebp+off]`）。`ByRef` が 1 なら、その場所にあるのは値へのポインタ。`kind` / `typeIdx` はコンパイラの型の番号（`TY_*`・`LOW_PTI_*`、Type / Class は型表の番号）で、`型` はそれを読みやすくした名前（`Long`、`DWord`、`String`、`Double`、`*Byte`、`Pt`、`*Pt`、`Long()` など） |
| `file` | ソースファイル（`#include` したものも）。`line` から番号で引く |
| `line` | その RVA から次の `line` の RVA の手前までが、そのファイルのその行の機械語。`文の始まり` が 1 の位置がブレークポイントを置ける所。0 は入れ子の文の後ろ（`For` の `Next` の加算と判定、`Loop While` の判定など）で、行を調べるのには使うがステップ実行では止まらない。ファイル番号 `-1` / 行 `0` はどの行でもない（手続きの外） |

コードの無い行（`Dim` だけの行、`Else`、`End If` など）は出ません。デバッガーはそういう行に置かれたブレークポイントを次の行へずらします。

### `Debug` 文

`Debug` はデバッガーの下で動いているときだけ止まります（`IsDebuggerPresent` を見て `DebugBreak`）。`-debug` なしで訳したとき、デバッガー無しで動かしたとき、`-linux` では何もしません。止まるのは `kernel32` の中なので、デバッガーは戻り先（`BasicDebug` の呼び出し元）の行を出します。

### コンパイラの中

| ファイル | 役目 |
|---|---|
| `DbgInfo.abp` | 下ろすとき: 文の始まり・入れ子の後ろ・手続きの始まりと終わりに `OP_DBG_LINE` / `OP_DBG_FUNC` / `OP_DBG_FEND` を IR に入れる（`LowStmtList`、`LowModStmtNext`、`AstToIrEmitFuncSetup` / `Finish`、`LowEmitMainOpen` / `Close`） |
| `DbgInfoVar.abp` | 手続きの終わりでローカル変数の表を、`AstToIr` の終わりでグローバル変数の表を写す |
| `DbgInfoEmit.abp` | 機械語にするとき、`OP_DBG_*` の位置（`.text` の先頭からの offset）を覚える。印は機械語を出さない |
| `DbgInfoType.abp` / `DbgInfoWrite.abp` / `DbgInfoLines.abp` | 書き出し。結合したソースの行は `PpMapFind` でファイルと行に戻す |

`OP_DBG_*` は `-debug` のときだけ入るので、リリースの IR と機械語は前と同じです。`-X`（`LinuxPrune`）は手続きの最後の命令を見て次の手続きへ落ちるかを決めるので、`OP_DBG_*` を飛ばして見ます。

## これから（D1 の作り）

- `CreateProcess` に `DEBUG_ONLY_THIS_PROCESS`、`WaitForDebugEvent` / `ContinueDebugEvent` で回す。`CREATE_PROCESS_DEBUG_INFO.lpBaseOfImage` が読み込まれた先頭
- ブレークポイント: 文の始まりの 1 バイトを `0xCC` にする。止まったら元に戻し、rip を 1 戻して TF で 1 命令進め、`0xCC` を書き直す
- 最初の `ntdll` のブレークポイントは読み飛ばす
- `CONTEXT` は 16 バイト境界に置く
- 呼び出し履歴は rbp をたどる（どの手続きも `push rbp; mov rbp, rsp` で始まる）。戻り先は `[rbp+8]`
