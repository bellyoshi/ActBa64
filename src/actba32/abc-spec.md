# ABC / ABPC 自己ホスト仕様（abc-spec v0.1）

## 0. バイナリ配置（ホスト vs セルフホスト）

| 場所 | 内容 | ビルド |
|------|------|--------|
| **prototype3 直下** | `abpc.exe` / `abc.exe` / `abassembler.exe` / `ablinker.exe` | **当面 ab420 GUI（人間がビルド）** — ホスト／ブートストラップ |
| **`selfhost\`** | ソース展開先 + セルフホスト成果物 | ソースを `selfhost\` に展開し、そこで `abpc <project.pj>` |

`.pj` の `#OUTPUT_RELEASE` は常にカレント直下（例: `.\abpc.exe`）。  
セルフホスト時は作業ディレクトリを `selfhost\` にするため、成果物は `selfhost\` に落ち、直下ホストを上書きしない。  
詳細手順は [README.md](./README.md) を参照。

## 1. 最終ゴール

```
（selfhost\ 上で） abpc abpc.pj  →  abpc.exe
```

既存の ActiveBasic IDE なしで、プロジェクトファイルから自分自身を再ビルドできること。  
同じ経路でツール一式もビルドできること:

```
（selfhost\ 上で）
abpc abc.pj          → abc.exe
abpc abassembler.pj  → abassembler.exe
abpc ablinker.pj     → ablinker.exe
abpc abpc.pj         → abpc.exe          ← 自己ホストの証明
```

自己ホストの合格条件:

1. ホスト（直下・ab420 製）の初期 `abpc.exe` がある
2. ソース（ツール `.abp`/`.pj`、`Include\`、`test\` 等）を `selfhost\` に展開し、そこで `abpc abpc.pj` が新しい `abpc.exe` を出す
3. その新しい `abpc.exe` でもう一度 `abpc abpc.pj` が通り、動作が一致する

## 2. 全体構成

```
abpc <project.pj>
        │
        ├─ 1. .pj を読む（ソース一覧・出力名・オプション）
        ├─ 2. #SOURCE の各 .abp を順に abc へ
        │         .abp → .asm
        ├─ 3. 各 .asm を abassembler へ
        │         .asm → .obj
        └─ 4. 全 .obj を ablinker へ
                  .obj... → .exe（#OUTPUT_RELEASE）
```

単一ファイル直指定（現行の `abpc hello.abp`）は、内部的に 1 ソースの仮想プロジェクトとして残してよい。

## 3. プロジェクトファイル（.pj）仕様

現行の ActiveBasic 風 `.pj` を読む。自己ホストに必要な指令だけを必須とする。

### 3.1 例（現行 `abpc.pj`）

```
' ActiveBasic Project file.

#VERSION=9
#MODULETYPE=0
#NAME=abpc
#PLATFORM=32
#USEWINDOW=0
#OPTION=&H00010000
#OUTPUT_RELEASE=.\abpc.exe
#OUTPUT_DEBUG=.\abpc_debug.exe
#RESOURCE=0

#SOURCE
abpc.abp
```

（現行 `abpc.pj` は `#SOURCE` に Utils/Common/FileIO も含む。セルフホストではこのファイルごと `selfhost\` に展開してビルドする。）

### 3.2 複数ソース例（現行 `ablinker.pj`）

```
#SOURCE
ablinker.abp
coff.abp
pe.abp
```

`#SOURCE` 以降の空でない行をソース一覧とする（コメント行 `'` は無視）。

### 3.3 abpc が解釈する指令

| 指令 | 必須 | 意味 |
|------|------|------|
| `#SOURCE` | ○ | 続く行が入力 `.abp` 一覧 |
| `#OUTPUT_RELEASE` | ○ | 出力 EXE パス |
| `#PLATFORM` | ○ | `32` のみ対応 |
| `#USEWINDOW` | △ | `0` = CUI、`1` = GUI（リンカの Subsystem） |
| `#NAME` | × | 表示・中間ファイル名のヒント |
| `#OUTPUT_DEBUG` | × | 無視してよい |
| `#VERSION` / `#MODULETYPE` / `#OPTION` / `#RESOURCE` | × | 無視してよい |

不明指令は警告または無視（エラーにしない）。

### 3.4 中間ファイル命名

プロジェクト `foo.pj`、ソース `a.abp` `b.abp` のとき例:

```
a.asm  a.obj
b.asm  b.obj
→ #OUTPUT_RELEASE の exe
```

作業ディレクトリは `.pj` のあるディレクトリ（またはカレント）。パスは `.pj` 相対。

### 3.5 リンク

複数 `.obj` を 1 つの EXE にリンクする。  
エントリシンボルは `_main`（先頭ソースのトップレベル、または規約で固定）。  
`coff.abp` / `pe.abp` のような Type/Const のみのユニットは、コードが無くても `.obj` としてシンボル／データを出せるか、**コンパイル単位を結合してから 1 回アセンブル**する方式でもよい。

**推奨（実装を簡単にする）:**  
`#SOURCE` をテキスト結合（または `#include` 展開相当）してから **1 つの `.asm` / 1 つの `.obj`** にする。  
自己ホスト初期はこちらでよい。後で別コンパイル＋リンクに進化させる。

```
推奨パイプライン（Phase 自己ホスト）:
  .pj → ソース結合 → 1x .abp相当 → abc → 1x .asm → abassembler → 1x .obj → ablinker → .exe
```

## 4. 非目標

- ActiveBasic 全互換
- 64bit / クラス / イベント / COM
- 最適化
- 浮動小数点
- `Select Case` / `GoTo` / `With` / `ReDim`
- リソース（`#RESOURCE`）埋め込み

## 5. 言語サブセット（abc がコンパイルする ABP）

目標ソース: `abpc.abp` / `abc.abp` / `abassembler.abp` / `ablinker.abp` / `coff.abp` / `pe.abp`

### 5.1 字句

- コメント: `'` 〜 行末
- 識別子: `[A-Za-z_][A-Za-z0-9_]*` および末尾 `$`（`Trim$`）
- 整数: 十進 / `&H` 十六進
- 文字列: `"..."`（エスケープなし）
- 演算子: `+ - *`、`= <> < > <= >=`、`And Or Xor`、`()`
- 大小文字は区別しない
- 文の区切りは改行（`:` 連結は非対応）

### 5.2 型

| 型 | サイズ |
|----|--------|
| `Byte` | 1 |
| `Word` | 2 |
| `Long` / `DWord` / `HANDLE` | 4 |
| `*T` | 4 |
| `String` | §5.7 |
| `Type` 名 | メンバ合計（自然整列） |

条件式は「0 以外が真」。

### 5.3 宣言

```
Const NAME = <定数式>

Dim name As T
Dim name(N) As T          ' 添字 0..N
Dim name[N] As T          ' 同上（スタックバッファ記法）
Dim p As *T

Type NAME
    field As T
    field(N) As T
End Type
```

定数式: 整数、他 Const、`Or` / `And` / `Xor`、括弧。

### 5.4 手続き

```
Sub Name(arg As T, ByRef x As T, ...)
End Sub

Function Name(...) As T
    Name = <値>
End Function
```

- 呼び出し規約: **stdcall**
- `Exit Sub` / `Exit Function` / `Exit While`
- ネスト手続きなし
- エントリ: 結合後ソースのトップレベル文 → `_main`

### 5.5 文

```
左辺 = 式
If 式 Then ... [ElseIf ...] [Else ...] End If
While 式 ... Wend
For i = 式 To 式 [Step 式] ... Next
Name(...) / Call Name(...)
Print 式
End
```

### 5.6 式・左辺

- 演算・比較・`And`/`Or`/`Xor`
- 呼び出し、`SizeOf(T)`、`VarPtr(x)`、`StrPtr(s)`
- `a(i)` / `p[i]` / `x.Field` / `p.Field`

### 5.7 文字列（案 A・既定）

NUL 終端バイト列。連結・`Mid$` 等は都度確保。

必須ランタイム: `Len` / `Left$` / `Mid$` / `Chr$` / `Asc` / `Str$` / `Hex$` / `MakeStr` / `StrPtr` / `InStr` / `+` / 内容比較。

### 5.8 プリプロセス

| 指令 | 意味 |
|------|------|
| `#include "path"` | 挿入 |
| `#console` | CUI ヒント（`.pj` の `#USEWINDOW=0` と併用可） |
| `#strict` | 無視 |

## 6. WinAPI / ランタイム（リンカ自動 IAT）

**kernel32:**  
`ExitProcess`, `GetCommandLineA`, `lstrlenA`, `lstrcpyA`,  
`CreateFileA`, `ReadFile`, `WriteFile`, `CloseHandle`, `GetFileSize`,  
`GetModuleFileNameA`, `GetFileAttributesA`, `DeleteFileA`,  
`CreateProcessA`, `WaitForSingleObject`,  
`GetProcessHeap`, `HeapAlloc`, `HeapFree`,  
`GetStdHandle`, `WriteFile`（`Print` 用）

**user32（任意）:** `MessageBoxA`

**コンパイラ提供:** `malloc` / `free` / `memcpy` / `ZeroMemory` / `NULL` など。

## 7. アセンブラ命令セット（abassembler）

| 命令 | 用途 |
|------|------|
| `push` imm/reg/sym | 引数 |
| `pop` reg | |
| `call` sym/reg | |
| `ret` / `ret imm` | stdcall |
| `mov` reg/mem ↔ imm/reg/mem | |
| `lea` reg, mem | |
| `add/sub/and/or/xor` | |
| `cmp` | |
| `jmp/je/jne/jl/jle/jg/jge` | |
| `db` / `dd` | |
| `bits` / `section` / `extern` / `global` / label | |

## 8. コード生成規約（abc）

- 32bit NASM 風テキスト
- グローバル → `.data`
- 文字列リテラル → `str_N db "...", 0`
- 局所 → `[ebp-offset]`、引数 → `[ebp+8]`…
- API は `extern _Name@N`
- `global _main`

## 9. 実装フェーズ

`.pj` 駆動を軸に、言語を段階追加する。

| Phase | 内容 | 受け入れ |
|-------|------|----------|
| 0 | 現状: `abpc file.abp` + MessageBox のみ | `hello.abp` |
| 1 | `ret` / `mov`、空の `_main` | 即終了 EXE |
| 2 | `Dim Long`、式、`If` | `ExitProcess(式)` |
| 3 | `While`/`For`、`Sub`/`Function` | ループ計算 |
| 4 | 配列・ポインタ・`VarPtr` | バッファ読み書き |
| 5 | `String` ランタイム | パス文字列処理 |
| 6 | `Type` / `#include` / WinAPI 表 | `coff.abp` 相当 |
| 7 | **`abpc` が `.pj` を読む**（ソース結合→1 obj→exe） | `abpc hello.pj` |
| 8 | `abpc abc.pj` → 自己ホスト可能な `abc` | `abc` 2 世代一致 |
| 9 | `abpc abassembler.pj` / `ablinker.pj` | 両ツール自己ビルド |
| **10** | **`abpc abpc.pj → abpc.exe` を 2 回** | **最終ゴール** |

Phase 7 以降、CLI は次を正式とする:

```
abpc <project.pj>
abpc <input.abp> [output.exe]     ' 互換（単一ファイル）
```

## 10. 既存ソースとの関係

- ツール `.abp` は本サブセットに収まるよう、必要なら最小限の書き換えのみ
- `.pj` は現行ファイルをそのまま入力にする（フォーマット変更しない）
- ホスト ActiveBasic（ab420）でも同じ `.abp` がビルドできる状態を維持する（二重メンテを避ける）
- 直下のホスト exe は当面 ab420 GUI で人手ビルド。セルフホストはソースを `selfhost\` に展開してからビルド（§0 / README.md）

## 11. 未決事項

1. 複数 `#SOURCE` を「結合して 1 コンパイル」にするか「別 obj をリンク」にするか → **初期は結合を推奨**
2. String を NUL 終端（案 A）で確定するか
3. `#USEWINDOW=0` で Subsystem を CUI(3) にするか、現状 GUI(2) のままか
4. `#SOURCE` 結合時の重複 `Type`/`Const` の扱い（`#include` と二重定義防止）

## 12. 直近の一手

1. 本仕様で合意
2. Phase 1–3（言語の骨）を `abc` + `abassembler` に入れる
3. Phase 7 で `abpc` の入力を `.pj` 対応にする
4. `abpc.pj` が要求する構文が揃い次第、Phase 10 を狙う

---

## 13. 実装メモ（進行状況）

### Phase 1（完了）

| 項目 | 状態 |
|------|------|
| `abc.abp`: `#console` / `End` / `ExitProcess(n)` / 空プログラム | **完了**（`t1` / `t1_exit=42`） |
| `abassembler.abp`: `ret` / `mov` / `jmp` / `push reg` | **完了**（`t1_mov`） |
| `.data` 空回避 | `dummy db 0` |

### Phase 2（完了）

| 項目 | 状態 |
|------|------|
| `Dim Long` / 代入 / `+ - *` / `If Else End If` / `ExitProcess(式)` | **完了** |
| `pop` / `add`/`sub`/`cmp` / `imul` / `jcc` / `mov [reg]` | **完了** |
| `t2.abp` | exit **7**（`1+2*3`） |
| `t2_if.abp` | exit **10** |
| 注意 | ActiveBasic では `"["` 単独リテラルが危ない → `Chr$(&H5B)` / `&H5B` 比較を使う |

次は Phase 3（`While`/`For`、`Sub`/`Function`）。

### Phase 3（完了）

| 項目 | 状態 |
|------|------|
| `While`/`Wend`/`For`/`Next` | **完了**（exit 10 / 15） |
| `Sub`/`Function` / 式中呼び出し | **完了**（`t3_func` exit 7） |
| 注意 | 式中の `(`/`)` は `InStr`/`Right$` よりバイト `40`/`41` で検出 |

次は Phase 4（配列・ポインタ・`VarPtr`）。

### Phase 4（完了）

| 項目 | 状態 |
|------|------|
| `Dim a(N)/a[N] As Byte\|Long` | **完了** |
| `Dim p As *Byte` / `p[i]` | **完了** |
| `VarPtr(x)` / `Const` | **完了** |
| `abassembler` `movzx` / `mov [reg], al` | **完了** |
| テスト | `t4_arr` **10**, `t4_ptr` **100**, `t4_varptr` **7** |

### Phase 5（完了）

| 項目 | 状態 |
|------|------|
| `Dim As String` / リテラル / `+` | **完了** |
| `Len` / `Asc` / `StrPtr` / `Chr$` / `Left$` / `Mid$` | **完了** |
| 文字列比較 / `Or` / `And` | **完了** |
| テスト | `t5_len` **2**, `t5_cat` **4**, `t5_left` **72**, `t5_path` **3** |

### Phase 6（完了）

| 項目 | 状態 |
|------|------|
| `Type` / フィールド / `SizeOf` | **完了** |
| `.` / `->` メンバ | **完了** |
| `#include` | **完了** |
| WinAPI stdcall 修飾 | **完了** |
| `abassembler` word `movzx` / `mov [reg],ax` | **完了** |
| テスト | `t6_sizeof` **20**, `t6_field` **332**, `t6_include` **40** |

### Phase 7（完了）

| 項目 | 状態 |
|------|------|
| `abpc` が `.pj` を読む | **完了** |
| `#SOURCE` 結合 → 1x abc/asm/obj | **完了** |
| 単一 `.abp` 互換 | **維持**（`t5_len` exit 2） |
| テスト | `t7.pj` → exit **50** |

### 共通化（整理）

| モジュール | 内容 |
|------------|------|
| `Utils.abp` | `Trim$` / `Lower$` / `StartsWith` / パス系 |
| `Common.abp` | `GetCmd` / `ZeroMem` / `HexPad$` |
| `FileIO.abp` | `LoadFile` / `WriteAll` / `FileExists` / テキスト I/O |
| `*.idx` | 上記 + `coff`/`pe` を `#include` |

### Phase 8（進行中）

| 項目 | 状態 |
|------|------|
| `abpc abc.pj` 自己ビルド | **ブロック中 → 修正済み要リビルド** |
| `FindOp2`/`FindOpWord` 末尾 `)` スキップ | **修正済** |
| 単一行 `If ... Then stmt` | **追加済** |
| 引数なし呼び出し `F()`（`Mid$(...,0)`） | **確認済** |
| `ElseIf` | **確認済** |
| Win 定数 (`MAX_PATH` 等) | **abc 組み込み**（`Common.abp` には書かない＝ホスト衝突回避） |
| `Print` / `Str$` / `Hex$` | **追加**（`push [reg]` バグ修正済） |
| モジュール変数 → `.data` + 手続き内から参照可 | **追加済（要リビルド）** |
| `mov reg, symbol` | **abassembler 追加済** |
| 結合時 `#include` 除去 + 依存先出し | **追加済** |

次: ホストで `abc.pj` / `abpc.pj` をリビルド → `abpc abc.pj` → 回帰。

---

**合格フレーズ（最終形態）:**

```
（selfhost\ 上で） abpc abpc.pj → abpc.exe
```
