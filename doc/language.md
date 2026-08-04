# ActBa 言語仕様

ActiveBasic 互換の **サブセット** 仕様です。完全互換ではありません。

| 実装 | 成果物 | 対象 |
|---|---|---|
| **actba64** | `actba64.exe` | 64bit PE（PE32+）へ直接出力 |
| **actba32** | `actba32` + `abc` / `abassembler` / `ablinker` | 32bit PE（asm→obj→exe） |

本文は両実装の共通核を先に書き、差分は各節末または [§9](#9-actba32-と-actba64-の差分) にまとめます。  
ビルド手順は [build.md](./build.md) を参照。

---

## 1. ソースとプロジェクト

### 1.1 ファイル

| 拡張子 | 意味 |
|---|---|
| `.abp` | ソース 1 ファイル |
| `.pj` | プロジェクト（複数 `.abp` を結合） |

### 1.2 字句

- コメント: `'` から行末
- 識別子: `[A-Za-z_][A-Za-z0-9_]*`、末尾 `$` 可（例: `Left$`）
- 整数: 十進 / `&H` 十六進
- 文字列リテラル: `"..."`（エスケープなし）
- 大小文字は区別しない
- 文の区切りは改行（actba64 は `:` 連結なし。actba32 は `:` 可）

### 1.3 ディレクティブ行

| 行 | 意味 |
|---|---|
| `#console` | CUI プログラムの慣習マーカー（現状は無視してよい） |
| `#strict` | 無視 |
| `#include "path"` | ファイル挿入（深さ上限あり） |
| その他 `#...` | 字句レベルで行スキップ、または実装依存で無視 |

### 1.4 `.pj`（プロジェクト）

```
' ActiveBasic Project file.
#NAME=example
#PLATFORM=32          ' actba32 向け。actba64 は読まない
#USEWINDOW=0          ' 0=CUI / 1=GUI（actba32）
#OUTPUT_RELEASE=.\out.exe
#SOURCE
a.abp
b.abp
```

| 指令 | actba32 | actba64 |
|---|---|---|
| `#SOURCE` | 必須。続く行が入力 `.abp` | 必須（結合のみ） |
| `#OUTPUT_RELEASE` | 出力 EXE（CLI `-o` が優先） | 使わない（常に `-o`） |
| `#USEWINDOW` | サブシステム | 未使用（常に CUI） |
| `#PLATFORM` | `32` | 未使用 |
| その他 | 無視可 | 無視 |

`#SOURCE` のソースはテキスト結合して **1 コンパイル単位** になる。

### 1.5 CLI

```text
actba64 <src.abp|.pj> -o <out.exe>
actba32 <src.abp|.pj> [-o <out.exe>]
```

エントリは結合後ソースのトップレベル文。終了は `ExitProcess(n)` または `End`（終了コード 0）。

---

## 2. 型

| 型 | サイズ (32) | サイズ (64) | 備考 |
|---|---|---|---|
| `Byte` | 1 | 1 | |
| `Word` | 2 | 2 | |
| `Long` / `DWord` / `Integer` | 4 | 4 | 別名あり |
| `HANDLE` / `HWND` 等 | 4 | 4（別名） | `TypeDef` 可 |
| `*T` | 4 | **8** | ポインタ |
| `String` | ポインタ相当 (4) | ポインタ相当 (**8**) | NUL 終端バイト列 |
| `Type` 名 | メンバ合計 | メンバ合計 | 自然整列 |

条件式は「0 以外が真」。

### 2.1 配列

```
Dim a(N) As T     ' 添字 0..N（要素数 N+1）
Dim a[N] As T     ' 同上（バッファ記法）
```

`N` は定数式可。`Byte` / `Long` / `String` / UDT 配列をサポート。

### 2.2 ユーザ定義型

```
Type COFF_HEADER
    Machine As Word
    NumberOfSections As Word
    TimeDateStamp As DWord
End Type

TypeDef HWND = Long
TypeDef PBYTE = *Byte
```

メンバ参照: `x.field` / `p->field` / `a(i)` / `p[i]`（組み合わせ可）。

---

## 3. 宣言

### 3.1 Const / Dim

```
Const MAX_PATH = 260
Const GENERIC_READ = &H80000000

Dim a As Long
Dim b = 3 As Long
Dim c As Integer = 4
Dim p As *Byte
Dim buf[259] As Byte
Dim xs(7) As Long
Dim h As COFF_HEADER
```

- **actba64** の `Const`: 整数リテラル（符号付き）中心。複雑な定数式は制限あり
- **actba32**: より広い定数式。`Include\default` で組み込み定数を自動導入

### 3.2 手続き

```
Sub USAGE()
    Print "usage"
    End
End Sub

Function Add(a As Long, b As Long) As Long
    Add = a + b
End Function

Sub Inc(ByRef x As Long)
    x = x + 1
End Sub
```

- `ByRef` 対応。呼び出し側の `ByVal` は無視してよい
- 戻り値は `Function名 = 式`
- `Exit Sub` / `Exit Function`
- ネストした `Sub`/`Function` は不可
- **`Declare` は非対応**（WinAPI は名前解決＋IAT）

呼び出し規約: actba32 は **stdcall**、actba64 は **x64 Windows ABI**。

---

## 4. 文

```
左辺 = 式
Name(引数...)                    ' Call キーワード不要（可なら無視）

If 式 Then
    ...
ElseIf 式 Then
    ...
Else
    ...
End If

If 式 Then 文                    ' 単行 If

Select Case 式
    Case 定数
        ...
    Case Else
        ...
End Select

While 式
    ...
Wend

For i = 式 To 式
    ...
Next

Do
    ...
Loop

Print 式
Print 式;
End
ExitProcess(式)
```

| 文 | actba64 | actba32 |
|---|---|---|
| `If` / `ElseIf` / 単行 If | ○ | ○ |
| `Select Case` | ○ | ○ |
| `While` / `Wend` | ○ | ○ |
| `For ... To ... Next` | ○（**Step なし**） | ○（**Step あり**） |
| `Do ... Loop` | ○（裸） | ○ + **While/Until** |
| `Exit Do` / `Exit While` | ○ | ○ |
| `Exit For` | ✕ | ○ |
| `Print` | ○ | ○ |
| `Input` / `MsgBox` | ✕ | ○（ランタイム／API） |

---

## 5. 式

### 5.1 演算子

| 演算 | actba64 | actba32 |
|---|---|---|
| `+ - *`（整数） | ○ | ○ |
| 文字列 `+`（連結） | ○ | ○ |
| 単項 `-` | ○ | ○ |
| `= <> < > <= >=` | ○ | ○ |
| `And` / `Or` | ○（ビット。条件では短絡） | ○ |
| `Xor` | ✕ | ○ |
| `/` `\` `Mod` | ✕ | ○ |

### 5.2 アドレス・サイズ・組込

```
VarPtr(左辺)
AddressOf(手続き名)
SizeOf(型名)
Len(文字列 | UDT変数)     ' 文字列長 or 構造体サイズ
Asc(s)
Left$(s, n)
Mid$(s, start[, len])
Str$(n)
StrPtr(s)
MakeStr(p As *Byte)
```

### 5.3 メモリ

```
p = malloc(n)
p = calloc(n)
free(p)
memcpy(dst, src, n)
```

（実装により `RtlMoveMemory` / `FillMemory` 等へマップ）

---

## 6. 文字列

- 表現: NUL 終端のバイト列（ANSI 寄り）
- 連結・`Left$` / `Mid$` 等は必要に応じて確保
- 内容比較は実装依存（`=` やヘルパ関数）
- `InStr` / `Lower$` などは **言語組み込みではなく** ライブラリ `.abp` として提供される場合がある

actba32 の方がランタイムが広い（`Chr$` / `Hex$` / `Right$` / `Val` / `InStr` 等）。

---

## 7. プリプロセスと標準ヘッダ

### 7.1 `#include`

```
#include "Utils.abp"
```

パスはソース相対（または実装が解決するパス）。循環・深さ超過はエラー。

### 7.2 actba32 の自動 Include

actba32（`abc`）は `Include\default\default.idx` を先頭に自動挿入する。  
Win32 型・定数（`Windows.sbp` / `WinTypes.sbp` / `WinConsts.sbp`）が使える。  
**`Declare Lib` 群は載せない**（IAT 解決）。

actba64 は自動挿入なし。必要な `Const` / ヘルパはソース側で明示する。

---

## 8. WinAPI / IAT

コンパイラが名前を認識した API はインポートテーブルに載る。

### 8.1 共通でよく使うもの（kernel32）

`ExitProcess`, `GetCommandLineA`, `lstrlenA`, `lstrcpyA`, `lstrcatA`,  
`CreateFileA`, `ReadFile`, `WriteFile`, `CloseHandle`, `GetFileSize`,  
`GetFileAttributesA`, `GetProcessHeap`, `HeapAlloc`, `HeapFree`, `GetStdHandle`

### 8.2 actba32 で追加されやすいもの

`GetModuleFileNameA`, `DeleteFileA`, `CreateProcessA`, `WaitForSingleObject`, `GetTickCount`,  
一部 user32（`MessageBoxA` 等）

未登録の名前は通常の関数呼び出しとして扱われ、リンク／実行時に失敗しうる。

---

## 9. actba32 と actba64 の差分

| 観点 | actba32 | actba64 |
|---|---|---|
| 出力 | 32bit PE | 64bit PE32+ |
| ポインタ / `String` | 4 バイト | 8 バイト |
| `Long` | 4 | 4（LP64 ではない） |
| 演算 | `Xor` `/` `\` `Mod` | なし |
| ループ | `Step`, `Do While/Until`, `Exit For` | より狭い |
| 標準ヘッダ | 自動 `Include\default` | 明示 `#include` |
| 文字列ランタイム | `_rt_*` が広い | 必要分をインライン／一部 API |
| 文連結 `:` | ○ | ✕ |

共通の実用コア: `#include` / `.pj`、`Dim`/`Const`/`Type`/`TypeDef`、  
`If`/`Select`/`While`/`For`/`Do`、`Sub`/`Function`/`ByRef`、  
配列・ポインタ・UDT、主要文字列組込、malloc 系、ファイル I/O API、`Print`、`ExitProcess`。

---

## 10. 非対応（意図的）

- ActiveBasic 全互換、クラス / イベント / COM
- 浮動小数点
- `GoTo` / `With` / `ReDim` / `Declare`
- ネスト手続き
- リソース（`#RESOURCE`）埋め込み
- 高度な最適化

---

## 11. 最小例

```
#console

Print "Hello"
ExitProcess(0)
```

```
#console

Function Add(a As Long, b As Long) As Long
    Add = a + b
End Function

Dim x As Long
x = Add(3, 4)
ExitProcess(x)
```

```
#console

Type Point
    x As Long
    y As Long
End Type

Dim p As Point
p.x = 10
p.y = 20
ExitProcess(p.x + p.y)
```

---

## 関連

- ビルド: [build.md](./build.md)
- actba32 自己ホスト・パイプライン詳細: [src/actba32/abc-spec.md](../src/actba32/abc-spec.md)
- 回帰テスト: `src/actba64/test/`（`' Target: actba64`）、`src/actba32/test/`
