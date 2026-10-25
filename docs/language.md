# ActBa 言語仕様

ActiveBasic 互換の **サブセット** 仕様です。完全互換ではありません。

| 実装 | 成果物 | 対象 |
|---|---|---|
| **actba64**（既定） | `actba64.exe` | 64bit PE（PE32+ / AMD64） |
| **actba64 -actba32** | 同じ `actba64.exe` | 32bit PE（PE32 / i386） |

言語仕様は 1 本です。残る差分はポインタ / `String` / `HANDLE` の幅（8 vs 4）、呼び出し規則（Microsoft x64 vs stdcall）、PE 形式だけです。  
ビルド手順は [build.md](./build.md)、ActiveBasic との差分は [different.md](./different.md) を参照。

---

## 1. ソースとプロジェクト

### 1.1 ファイル

| 拡張子 | 意味 |
|---|---|
| `.abp` | ソース 1 ファイル |
| `.pj` | プロジェクト（複数 `.abp` を結合） |

### 1.2 字句

- コメント:
  - `'` から行末
  - `/* ... */` ブロック（ネスト不可。途中にも可）
- 識別子: `[A-Za-z_][A-Za-z0-9_]*`、末尾 `$` 可（例: `Left$`）
- 整数: 十進 / `&H` 十六進
- 小数リテラル: `1.5` / `1.12345` など（符号・小数点付き十進）。字句テキストを保持し、**AST 上で IEEE 754 Double ビット**（`num`=下位32 / `left`=上位32）に変換する。科学記法（`1.0e10`）は未対応。コード生成は 64bit が `movabs rax, imm64`、`-actba32` は `edx:eax`
- 文字列リテラル: `"..."`（`""` で `"`）
- 識別子の大小文字: **定数・変数・Sub/Function・Type/Class 名は区別する**（AB 4.20 同様。`Foo` と `foo` は別）。**言語キーワード**（`If` / `Then` / `Dim` 等）と **組み込みランタイム名**（`FillMemory` / `malloc` 等）の認識のみ大小無視
- 文の区切りは改行。同一行の `:` 連結可（`a = 1: b = 2`）

行の継続:

```
Print a +_
    b +_
    c
```

行末の `_`（直後の空白・`'注釈` 可）で次行と 1 文に結合する。継続の先にある整数は式の一部で、行番号にはならない。  
`( )` / `[ ]` 内では、`(` `[` `,` の直後や閉じ括弧前など、パラメータ単位の改行も可（改行は空白扱い）。

### 1.3 ディレクティブ行

| 行 | 意味 |
|---|---|
| `#console` | `Include\console\console.idx` を自動挿入 |
| `#n88basic` / `#N88BASIC` / `#prompt` | N88BASIC 互換モード（[§1.6](#16-n88basic-モード)）。`#prompt` は完全別名 |
| `#USEWINDOW=0\|1` | 0=CUI / 1=GUI。ソース・`.pj` どちらでも可。`#n88basic` / `#prompt` は GUI を強制 |
| `#strict` | 型の暗黙変換を warning（`As` で抑制）。`Long`→`Byte` はデータ欠落、引数の `String`→`VoidPtr` と `VoidPtr`→`Long` も含む |
| `#include "path"` / `#include <path>` | ファイル挿入（深さ上限あり）。`"..."` はソース相対（絶対パス可）、`<...>` は `Include\` 配下を検索 |
| `#define` / `#ifdef` / `#ifndef` / `#else` / `#endif` | 条件付きコンパイル（[§7.7](#77-条件付きコンパイル)） |
| `#resource` | リソース埋め込み（[§5.2.2](#522-リソース埋め込み)） |
| その他 `#...` | 字句レベルで行スキップ、または実装依存で無視 |

ソース **1 行の最大長は 1024 バイト**（`PP_LINE_MAX`。改行は含まない）。超過するとコンパイルエラー（`too long line`）。長い `If` 条件などは複数行へ分割する（[§1.2](#12-行継続) の `_` や括弧内改行）。

`Include\default\default.idx`（`Windows.sbp` / `WinConsts.sbp` / `WinTypes.sbp`、`Math.abp`、`CvtNum.abp`、`Sleep.abp`、`Space.abp`、`DoubleStr.abp`、`BasicFile.abp`、`StringGc.abp`、`StrUtils.abp`、`SplitPath.abp`、`Memory.abp`、`BasicCmd.abp`）は **常時** 先頭へ挿入される（[`src/Include`](../src/Include)）。  
`#console` / `#n88basic` はそれに加えて各プロファイル idx を挿入する。

### 1.4 `.pj`（プロジェクト）

```
' ActiveBasic Project file.
#NAME=example
#PLATFORM=32          ' AB4.20 が stage0 を 32bit ホストとして出すため。出力ターゲットではない
#USEWINDOW=0          ' 0=CUI / 1=GUI
#OUTPUT_RELEASE=.\out.exe
#SOURCE
a.abp
b.abp
```

| 指令 | 意味 |
|---|---|
| `#SOURCE` | 必須。続く行が入力 `.abp`（結合して 1 コンパイル単位） |
| `#OUTPUT_RELEASE` | `.pj` からの相対出力パス。`-o` が無いとき使う（`-o` が優先） |
| `#USEWINDOW` | サブシステム（既定 CUI。`#n88basic` で GUI） |
| `#MODULETYPE` | `0` = EXE（既定）、`1` = DLL（[§8.4](#84-dll-を出力する)） |
| `#PLATFORM` | AB4.20 用。`actba64` は読まない（対象は `-actba32`） |
| その他 | 無視 |

`#SOURCE` のソースはテキスト結合して **1 コンパイル単位** になる。

### 1.5 CLI

```text
actba64 <src.abp|.pj> [-actba32] [-o <out>]
```

`-o` は `.abp` では必須。`.pj` に `#OUTPUT_RELEASE` があれば省略でき、そのパスは `.pj` のあるディレクトリ基準になる。`-o` を付けたときはそちらが優先。`-actba32` は引数のどこでも可。省略時は PE32+。

EXE のエントリは結合後ソースのトップレベル文です。終了は `ExitProcess(n)` または `End`（終了コード 0）。  
DLL（`#MODULETYPE=1`）の入口は `DllMain` です（[§8.4](#84-dll-を出力する)）。  
`#n88basic` 時の `End` は窓を出して閉じるまで待つ（actba64）。

### 1.6 N88BASIC モード

`#n88basic` / `#N88BASIC` / `#prompt` で `Include\N88BASIC\n88basic.idx`（`n88graph.abp` と `n88key.abp`）を挿入する。  
`#prompt` は ActiveBasic 互換の別名で、`#n88basic` と全く同じ動作。

| | 既定（64bit） | `-actba32` |
|---|---|---|
| ライブラリ挿入 | ○ | ○ |
| `LINE` / `CIRCLE` / `LOCATE` / `PAINT` 文 | ○（パーサ） | ○（同じパーサ） |
| `Inkey$` / `Input$(n)` | ○（`n88key.abp`） | ○ |
| 640×480 黒窓 GUI | ○（自動） | ○ |
| `End` → 窓待ち | ○（`N88_End`） | ○ |

N88 `LINE`（actba64 サブセット）:

```text
LINE (x1,y1)-(x2,y2)[,color][,B|BF]
LINE -(x2,y2)[,color][,B|BF]          ' 始点は LP（最終参照点）
```

- 省略時の `color` は 7（白）
- `B` = 四角形の枠、`BF` = 塗りつぶし四角
- 実行後 LP は終点へ移動

N88 `CIRCLE`（actba64 サブセット）:

```text
CIRCLE (x,y),r[,color][,start][,end][,aspect][,F[,color2]]
CIRCLE STEP(x,y),r[,...]              ' 中心は LP からの相対
CIRCLE ,r[,...]                       ' 中心は LP
```

- 角度 `start` / `end` はラジアン（`Double`）。省略または `start=end` で全周
- 負の角度は絶対値で円弧し、中心から半径線を引く（扇形。flags の startNeg/endNeg）
- `aspect` は垂直半径/水平半径（`Double`、省略時 `1.0`）
- `F` で塗りつぶし（タイルストリングは未対応）
- 実行後 LP は円の中心へ移動

N88 `LOCATE` / `PAINT`:

```text
LOCATE x, y                 ' または Locate(x, y) — 桁 x, 行 y（0 始まり。本家 N88 の 行,桁 1 始まりとは異なる）
PAINT (x, y), color1 [, color2]
```

- `LOCATE` 後の `Print` は窓上の文字位置へ描画（`;` なしなら次行へ）
- 数値の `Print` は `Str$`（Long）／`StrD$`（Double、64bit）で文字列化してから描画
- `PAINT` は `(x,y)` から境界色 `color2`（省略時は `color1`）までを `color1` で塗りつぶす
- `Inkey$()` は窓の `WM_KEYDOWN` を 1 文字取り、無ければ `""`。`Input$(n)` は同じキーを `n` 文字そろうまで待つ。`#n88basic` / `#prompt` のときだけ使える

色番号（0..7、N88 8 色）:

| 値 | 色 |
|---|---|
| 0 | 黒 |
| 1 | 青 |
| 2 | 赤 |
| 3 | マゼンタ |
| 4 | 緑 |
| 5 | シアン |
| 6 | 黄 |
| 7 | 白（省略時） |

サンプル: `src/actba64/samples/n88_shapes.abp`

---

## 2. 型

| 型 | サイズ (32) | サイズ (64) | 備考 |
|---|---|---|---|
| `Byte` | 1 | 1 | |
| `Word` | 2 | 2 | |
| `Single` | 4 | 4 | サイズと格納。汎用 IEEE 演算は未（`Double` を使う） |
| `Long` / `DWord` / `Integer` | 4 | 4 | 別名あり |
| `Double` | 8 | **8** | IEEE 倍精度。加減乗除・比較・`Function As Double` / Double 仮引数は 64bit と `-actba32` の両方。32bit の値は `edx:eax`。配列要素と UDT フィールドの 8 バイト転送は 64bit のみ |
| `Enum` 名 | 4 | 4 | 列挙。メンバは整数定数（[§3.4](#34-enum)） |
| `HANDLE` / `HWND` 等 | 4 | **8** | 64bit は `VoidPtr` / `*T`（`HFILE` は 4 のまま） |
| `*T` | 4 | **8** | ポインタ |
| `String` | ポインタ相当 (4) | ポインタ相当 (**8**) | 長さプレフィックス付きバイト列（AB4.20 互換） |
| `Type` 名 | メンバ合計 | メンバ合計 | 自然整列 |

条件式は「0 以外が真」。

### 2.1 配列

```
Dim a(N) As T           ' 1D: 添字 0..N（要素数 N+1）
Dim a[N] As T           ' 同上（バッファ記法）
Dim a(N, M) As T        ' 2D: 添字 (0..N, 0..M)
Dim a[N, M] As T        ' 同上（バッファ記法）
Dim a(N, M, L) As T     ' 3 次元以上。最大 8 次元
```

境界は定数式可（例: `Dim Board(BOARD_SIZE - 1, BOARD_SIZE - 1) As Long`）。  
`ELM(n)` は要素数 `n` に対する上限で、値は `n - 1`。`Dim a[ELM(10)]` は `Dim a[9]` と同じ（添字 0..9）。  
要素型は `Byte` / `Long` / `Single` / `Double` / `String` / UDT。UDT 配列は添字 1 個（平坦な通し番号）だけ。

**レイアウト（first-index-fastest）:** 先頭添字が連続する。各次元の長さは上限+1。

```
flat = i0 + i1 * (N + 1)          ' Dim a(N, M) の a(i0, i1)
L0 = N + 1
L1 = M + 1
flat = i0 + i1 * L0 + i2 * L0 * L1   ' Dim a(N, M, L) の a(i0, i1, i2)
```

3 次元以上も同じで、k 番目の刻みはそれより前の長さの積。添字は括弧・角括弧とも可。個数は 1（平坦な通し番号）か、その配列の次元数。要素数は各長さの積。  
境界は `Dim` のときに決まり、実行中には変えない。`ReDim` は Visual Basic の機能で、ActiveBasic 4.20 にも ActBa64 にも無い。

回帰: `test/t_arr2d_rw.abp`、`test/t_arr2d_const.abp`、`test/t_arr3d_rw.abp`。サンプル: `samples/reversi.abp`。

### 2.2 ユーザ定義型

```
Type COFF_HEADER
    Machine As Word
    NumberOfSections As Word
    TimeDateStamp As DWord
End Type

TypeDef HWND = Long
TypeDef PBYTE = *Byte
TypeDef PADD = *Function(a As Long, b As Long) As Long
```

メンバ参照: `x.field` / `p->field` / `a(i)` / `a(i, j)` / `p[i]`（組み合わせ可）。  
関数ポインタ型（`*Function` / `*Sub`）は [§5.2.1](#521-関数ポインタ型)。

---

## 3. 宣言

### 3.1 Const / Dim

```
Const MAX_PATH = 260
Const GENERIC_READ = &H80000000
Const NEXT = GENERIC_READ Or 1
Const MSG = "ok"
Const INC(n) = n + 1

Dim a As Long
Dim b = 3 As Long
Dim c As Integer = 4
Dim s$
Dim t As String
Dim p As *Byte
Dim buf[259] As Byte
Dim xs(7) As Long
Dim board(7, 7) As Long   ' 2D（§2.1）
Dim h As COFF_HEADER
```

- `Const name = expr`: 整数式（リテラル、先に書いた `Const`、加減乗、整数除算、`Mod`、`And` / `Or` / `Xor` / `Not`、`<<` / `>>`、`^`、`As` の幅マスク）か文字列リテラル。`Double` は置けない
- `Const name(仮引数) = expr`: 使うたびに仮引数へ実引数の式を埋め込んで展開する（64 個まで、入れ子 16 段まで）
- `Dim name$`: `As String` 省略可（末尾 `$`）
- `Include\default` で組み込み定数を自動導入

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

- `ByRef` 対応。呼び出し側の `ByVal` は無視してよい。構造体引数は `ByRef` 必須（`ByVal` と指定なしはエラー）。フィールド代入は呼び出し元に残る
- 戻り値は `Function名 = 式`
- `Exit Sub` / `Exit Function`
- ネストした `Sub`/`Function` は不可
- `Declare Function|Sub ... Lib "dll" [Alias "..."]` 可（IAT。任意 DLL・自作可。拡張子省略時は `.dll`。詳細は [§8](#8-winapi--iat)）
- `Function Export Name` / `Sub Export Name` は DLL のエクスポート（[§8.4](#84-dll-を出力する)）

### 3.3 Class

```
Class Counter
    Public
    value As Long

    Sub Counter(v As Long)      ' コンストラクタ
        value = v
    End Sub

    Sub ~Counter()               ' デストラクタ
    End Sub

    Sub Add(n As Long)
        value = value + n
    End Sub

    Function GetValue() As Long
        GetValue = value
    End Function
End Class

Dim c As Counter(10)            ' スタック上で ctor
c.Add(32)
x = c.GetValue()

Dim p As *Counter
p = New Counter(10)             ' ヒープ。失敗時は 0 で ctor は呼ばない
p = New [3] Counter(10)         ' 同じ引数で 3 要素
Delete p                        ' dtor を逆順に呼び、塊を解放。Delete 0 は何もしない
```

- `Class` / `End Class`。メンバ変数は `Type` と同様のオフセット配置
- `Private` / `Public`（未指定は Private）。`Protected` は受理し Public 扱い
- メソッドは暗黙の第1引数 `This`（オブジェクトポインタ）。呼び出しは `obj.Method(args)`。メソッド内は `This.Method(args)`
- コンストラクタ `Sub ClassName(...)` → `Dim obj As ClassName(args)` で自動呼出
- デストラクタ `Sub ~ClassName()` → 局所は手続き末尾、モジュール大域は終了前に呼出
- ctor/dtor 省略時は空の無引数版を暗黙生成
- メソッドはマングル名（例: `Counter_Add`）の通常 `Sub`/`Function` として生成（64bit は `RCX=This`、32bit は stdcall の第1引数）
- `Inherits` / `Virtual` / vtable 呼び出しは **部分対応**（COM / D3D11 向け。本体なし `Virtual Function|Sub` と継承先へのスロットコピー）
- `p->Release()` のようにポインタ経由で仮想メソッドを呼べる
- `New Class[(args)]` / `New [count] Class[(args)]` はオブジェクト先頭へのポインタを返す。塊の先頭 8 バイトに要素数（`Long`）があり、返すポインタはその直後。個数を省略したときは 1。コンストラクタ引数は一度だけ評価し、各要素へ同じ値を渡す。確保に失敗したときは 0 を返し、コンストラクタは呼ばない
- `Delete` は変数のクラスポインタ型から `Class_Dtor` を逆順に呼び、ヘッダごと `HeapFree` する。クラスは使用箇所より前に定義する。ポインタのクラス型が取れない `Delete` はコンパイルエラー。`Delete 0` は何もしない

**未対応:** `Super.Method`、メンバ実体クラスの自動 ctor・dtor、アクセス制御の厳密検査

### 3.4 Enum

```
Enum Modes
    Off          ' 1
    On = 5       ' 5
    Max          ' 6（直前 + 1）
End Enum

Dim x As Modes   ' 4 バイト
x = On
```

- `Enum` … `End Enum`。メンバ名は整数定数になる
- 値を省略したメンバは直前の値 + 1。最初のメンバを省略したときは **1**
- `= 式` は定数式（例: `B = A Or 2`）
- `Dim x As EnumName` は 4 バイト

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

For i = 式 To 式 [Step 式]
    ...
Next

Do [While 式 | Until 式]
    ...
Loop [While 式 | Until 式]

Continue For | Continue While | Continue Do

With 式
    .field = ...
End With

Print 式
Print 式;
Print #番号, [式 [, ...]] [;]  ' ファイルへ。項目間はカンマ。`;` で改行抑制
Input 変数          ' String / Long / Byte / Single / Double。stdin から1行
Input #番号, 変数 [, ...]  ' ファイルからフィールド読み取り
Open パス [For Input|Output|Append] As [#]番号
Close [[#]番号]     ' 省略時は全クローズ
Field #番号, バイト長
Get #番号, レコード, 文字列変数
Put #番号, レコード, 式
Write [#番号,] [式 [, ...]] [;]  ' カンマ区切り。番号省略は標準出力
Sleep(ミリ秒)       ' 待ち中もウインドウメッセージを処理
Beep
Cls [n]             ' コンソールをクリア。省略時 n は 1。負なら何もしない
MsgBox hWnd, text$ [, title$ [, type [, ans]]]
DelWnd hWnd
Window hWnd, hOwner, x, y, w, h, title$, style [, class$ [, id [, proc [, exStyle]]]]
ChDir path$
MkDir path$
Kill path$
Exec path$ [, cmd$]
Delete p            ' クラスポインタ。§3.3
End
ExitProcess(式)
```

| 文 | 対応 |
|---|---|
| `If` / `ElseIf` / 単行 If | ○ |
| `Select Case` | ○ |
| `While` / `Wend` | ○ |
| `For ... To ... [Step] Next` | ○（負の Step 可） |
| `Do ... Loop` | ○（`While` / `Until` を先頭または末尾に可） |
| `With ... End With` | ○（ネスト可） |
| `Exit Do` / `Exit While` / `Exit For` | ○ |
| `Continue For` / `Continue While` / `Continue Do` | ○（ループ先頭へ） |
| `Print` | ○ |
| `Print #` | ○（`BasicFile.abp`。項目間カンマ。`;` で改行抑制） |
| `Input` | ○（プロンプト文字列可。数値は十進文字列 → IEEE。`Double`/`Single` は `ValDouble`、整数は `Val`） |
| `Open` / `Close` / `Input #` | ○（`BasicFile.abp`。番号 1..16） |
| `Field` / `Get #` / `Put #` | ○（ランダム。`Open ... As` + Field 長） |
| `Write` | ○（画面または `#番号`。カンマ区切り） |
| `Sleep(ms)` | ○（メッセージポンプ付き・default） |
| `InsMenu` | ○（内部で `InsertMenuA`） |
| `LINE` / `CIRCLE` / `LOCATE` / `PAINT`（N88 文） | ○（`#n88basic`） |
| `Beep` / `Cls` / `MsgBox` / `Window` / `DelWnd` | ○（`BasicCmd.abp`。`Cls` はコンソール。`Window` はメッセージループを作らない） |
| `ChDir` / `MkDir` / `Kill` / `Exec` | ○（`BasicCmd.abp`） |
| `Delete` | ○（クラスポインタ） |
| 行番号 | ○（文頭の整数。無くてもよい。`GoTo` / `GoSub` の飛び先だけラベル） |
| `*名前` | ○（文頭のラベル。`GoTo` / `GoSub` の飛び先だけ。大小は区別する） |
| `GoTo` / `GoSub` / `Return` | ○（行番号または `*名前`。`Return` は `GoSub` の復帰。`Exit Function` とは別） |
| `Date$` / `Time$` | ○（`yyyy/mm/dd` と `hh:mm:ss`。月日時刻は 2 桁） |
| `Inkey$` / `Input$(n)` | ○（関数。`#n88basic` のみ。窓の `WM_KEYDOWN`） |

命令の引数は同じ行のカンマ区切りで、次の文キーワードは引数にしない。

- `Cls` の `n` は受け取るが、グラフィック画面は無いので常にコンソールをクリアする
- `MsgBox` は `hWnd` と `text$` が必須。`title$` の省略は空、`type` の省略は 0。第 5 引数があるときだけ `MessageBoxA` の戻り値をその変数へ代入する
- `Window` の `hWnd` は `ByRef HWND`。`class$` を省略すると `ActBa64Wnd` を一度だけ登録する（ウィンドウ手続きは `DefWindowProc`）。`id` 以降の省略は 0。メッセージループは作らない。`proc` は `CreateWindowEx` の `lpParam` に渡す
- `Exec` の `cmd$` を省略すると空文字にする
- `Date$()` / `Time$()` は文ではなく関数（`BasicCmd.abp`）。それぞれ `yyyy/mm/dd` と `hh:mm:ss` で、月日と時刻は 2 桁。`Str$` の先頭空白は付けない

行番号は付けても付けなくてもよい。文の先頭の整数が行番号で、その行に文が無くてもエラーにしない。`100 PRINT A` は 100 の位置から `PRINT` へ落ちる。文の先頭の `*名前` も同じ位置のラベルで、`*start Print 1` は `start` から `Print` へ落ちる。改行して始まる `*名前` はラベルで、`_` で続けた行の `*` は掛け算のまま。同じ行番号や同じ名前が何度あっても、`GoTo` や `GoSub` の飛び先でなければエラーにしない。飛び先が無い、または二つ以上あるときはコンパイルエラー。名前の大小は区別する。`GoTo` と `GoSub` の飛び先は行番号か `*名前`。`GoSub` は戻る場所を覚えて移り、`Return` で戻る。`GoSub` していない `Return` は終了コード 1 でプロセスを終える。

---

## 5. 式

### 5.1 演算子

優先順位（高い順）: `As` キャスト → `^` → 単項 `-` → `* / \ Mod` → `+ - &` → `<< >>` → 関係 → `Not` → `And` → `Or` → `Xor`。  
`* / \` どうし、および `+ -` どうしは同優先で左から右へ評価。関係演算の値は真=`-1` / 偽=`0`。

| 演算 | 対応 |
|---|---|
| `+ - *`（整数） | ○ |
| `+ - * /`（`Double`） | ○（IEEE。64bit と `-actba32`） |
| 文字列 `+` / `&`（連結・同義） | ○ |
| 単項 `-` / `Not` | ○ |
| `= <> >< < > <= >=` | ○（値は -1/0。文字列は辞書順。`Double` 比較は 64bit と `-actba32`） |
| `And` / `Or` / `Xor` | ○（ビット。条件の And/Or は短絡） |
| `\` `/`（整数除算） | ○（Long では同義） |
| `Mod` | ○ |
| `<<` / `>>`（`>>` は符号付き） | ○ |
| `^`（整数累乗） | ○ |
| `expr As Type`（切捨てキャスト） | ○（String へ/からは不可） |
| `+= -= *= /= \= <<= >>=` / `Mod=` `And=` `Or=` `Xor=` | ○ |
| `++` / `--` | ○ |

文字列の関係演算は辞書順（`lstrcmpA`）。長さが違い途中まで一致したら短い方が小さい。  
`As` は例: `&H12345678 As Word` → `&H5678`。`#strict` 時は異なる型の変数代入、`Long` から `Byte` への代入（呼び出し結果を含む）、引数の `String`→`VoidPtr` と `VoidPtr`→`Long` が warning（`As` キャストで抑制）。

### 5.2 アドレス・サイズ・組込

```
VarPtr(左辺)
AddressOf(手続き名)
SizeOf(型名)
Len(文字列 | UDT変数)     ' 文字列長 or 構造体サイズ
Asc(s)
Left$(s, n) / Right$(s, n) / Mid$(s, start[, len])
Chr$(n) / Chr(n)
Str$(n)
Hex$(n) / Oct$(n)        ' 16進（小文字）と 8進。0 は "0"（StrUtils.abp）
ZeroString(n)            ' 長さ n のゼロ埋め。n が負なら空（StrUtils.abp）
StrD$(d)                 ' Double → 文字列（Include\default\DoubleStr.abp）
Date$() / Time$()        ' yyyy/mm/dd と hh:mm:ss（BasicCmd.abp）
Inkey$() / Input$(n)     ' #n88basic のみ（n88key.abp）
StrPtr(s)
MakeStr(p As *Byte)
RGB(r, g, b)
LOWORD(n)
ELM(n)                   ' 要素数 n の上限。値は n - 1
MakeIntResource(id)
```

### 5.2.1 関数ポインタ型

```
Dim p As *Function(a As Long, b As Long) As Long
Dim s As *Sub(n As Long)
TypeDef PADD = *Function(a As Long, b As Long) As Long
Dim q As PADD

p = AddressOf(Add)
r = p(1, 2)          ' 間接呼び出し（OP_CALL_RAX）
s = AddressOf(Show)
s(r)
```

- `AddressOf` で手続きアドレスを取得し、`*Function` / `*Sub`（またはその `TypeDef`）へ代入
- 呼び出しは通常の関数呼び出しと同じ構文。引数型の厳密照合は未（個数・ABI は通常の call と同じ）
- 戻り型はシグネチャの `As`（`Sub` は戻り値なし）

### 5.2.2 リソース埋め込み

```
#resource "assets\payload.bin"
```

- ソース相対パスのファイル全体を PE `.rsrc` に **RCDATA（型 10）ID=1** として埋め込む
- 実行時: `FindResourceA(GetModuleHandleA(0), MAKEINTRESOURCE(1), MAKEINTRESOURCE(10))`
- `#resource "file.rc"` は `actba64.exe` の隣にある `rc.exe`（`src/rc/rc.pj`）を起動する。対応するのは `#define 名前 数値` と `ICON` 文だけ。MENU / DIALOG / VERSIONINFO は未
- `.pj` の `#RESOURCE=` は当面無視

### 5.3 メモリ

```
p = malloc(n)
p = calloc(n)
p = realloc(p, n)
free(p)
memcpy(dst, src, n)
GetByte(p) / GetWord(p) / GetDWord(p) / GetSingle(p) / GetDouble(p)
SetByte(p, n) / SetWord(p, n) / SetDWord(p, n) / SetSingle(p, sng) / SetDouble(p, dbl)
```

（`memcpy` は `RtlMoveMemory`、`FillMemory` は `RtlFillMemory` へマップ）  
`realloc(p, n)` は `HeapReAlloc(GetProcessHeap(), 0, p, n)`。戻り値は新しい先頭ポインタ。失敗時は 0 で、元のブロックはそのまま残る。  
`Get*` / `Set*` は `Memory.abp`。ポインタが 0 のとき `Get` は 0、`Set` は何もしない。`GetSingle` / `SetSingle` は 4 バイト、`GetDouble` / `SetDouble` は 8 バイトの IEEE ビットをそのまま読む／書く。

---

## 6. 文字列

- 表現: ActiveBasic 4.20 互換。ヒープ／静的データの直前 4 バイトに長さ（dword）、ポインタはデータ先頭を指す
- `Len(s)` はその長さを返す（`lstrlen` ではない）。`Chr$(0)` は長さ 1
- 末尾に WinAPI 用の NUL を付けるが、データ中の埋め込み NUL も有効
- `StrPtr(s)` はデータ先頭（恒等）。`MakeStr(p)` は NUL 終端 `BytePtr` から長さ付き String を複製
- 連結・`Left$` / `Mid$` 等は都度ヒープ確保
- 内容比較は長さ付き辞書順（埋め込み NUL 対応）
- **actba64 の String ヒープ**はハイブリッド GC（代入時の自動 `StrFree` はしない）。設計・BSS レイアウト・セーフポイントは [string-gc.md](./string-gc.md):
  - **Precise**: `String` / `String` 配列のグローバル・ローカルスロットをコンパイル時に root 登録し、セーフポイントで無条件マーク
  - **Conservative**: ユーザ globals とスタックをポインタ幅刻み走査し、ヒープタグ付き登録ブロックのみマーク
  - 確保は `StrHeapAlloc`、回収は `StrCollect`（String を確保しうるループ頭・`Print`/`Input` 後・MAIN 終了前。関数エピローグでは走らない）
  - UDT 内の String メンバは型表で区別できないため precise root 未登録（conservative 走査に依存）
- `InStr` / `Lower$` などは **言語組み込みではなく** ライブラリ `.abp` として提供される場合がある

`Chr$` / `Right$` は組み込み。`Hex$` / `Oct$` / `ZeroString` / `Val` / `InStr` などはライブラリ側。`Oct$` は 32bit のビット列を 8 進にし、先頭の 0 は付けない。`ZeroString(n)` の `Len` は `n` で、中身は 0（埋め込み NUL）。`n` が負のときは空文字。

`_splitpath(path, drive, dir, fname, ext)` は `X:\` で始まる絶対パスを NUL 終端の各バッファへ分ける。`drive` は `"C:"`、`dir` は `"\dir1\dir2\"`、`fname` は拡張子を除いた名前、`ext` は `".txt"`（最後の `.` から）。出力ポインタが 0 の欄は書き込まない。`path` が 0、または `X:\` で始まらないときは何も書き込まない。2 バイト文字の先行バイトは区切りにしない。

---

## 7. プリプロセスと標準ヘッダ

### 7.1 行長上限

| 項目 | 値 |
|---|---|
| 定数 | `PP_LINE_MAX`（`Preproc.abp`） |
| 上限 | **1024 バイト / 行**（終端 NUL・改行は含まない） |
| 超過時 | コンパイル失敗。`error: …: too long line (実長 > 1024)` |

`#include` 展開・条件付きプリプロセス・`With` 書き換え後の行にも同じ上限がかかる。  
長い条件式は `_` 継続や括弧内改行で分割する（[§1.2](#12-行継続)）。

### 7.2 `#include`

```
#include "Utils.abp"
#include <default/Windows.sbp>
```

- `"path"` … ソースファイル相対。ドライブ付き／先頭 `\` `/` の絶対パスはそのまま。
- `<path>` … `Include\` 配下を検索（見つからなければ `path` そのもので再検索）。
- **同一パスは一度だけ展開**（2 回目以降はスキップ）。AB 4.20 は都度展開する点が異なる（[different.md](./different.md#制御プリプロセス)）。

循環・深さ超過はエラー。

### 7.3 自動 Include

`Include\default\default.idx`（`Windows.sbp` / `WinConsts.sbp` / `WinTypes.sbp`、`Math.abp`、`CvtNum.abp`、`Sleep.abp`、`Space.abp`、`DoubleStr.abp`、`BasicFile.abp`、`StringGc.abp`、`StrUtils.abp`、`SplitPath.abp`、`Memory.abp`、`BasicCmd.abp`）は **常時** 先頭へ挿入される。実体はリポジトリの [`src/Include`](../src/Include) 1 本。コンパイラは exe 隣 → 親〜3 階層上 → カレントの `Include\` を順に探す（詳細は [build.md](./build.md#include-の置き場所)）。  
続けて Preproc が `api.idx`（主要 Win32 の `Declare Lib`）と `UnicodeApi.sbp`（Unicode 版 API）を挿入する。  
加えてソースのディレクティブでプロファイルを挿入する:

| ディレクティブ | 挿入される idx |
|---|---|
| `#console` | `Include\console\console.idx` |
| `#n88basic` / `#prompt` | `Include\N88BASIC\n88basic.idx` |

`default.idx` 自体には **`Declare Lib` を載せない**（型・定数・ヘルパのみ。Declare は `api.idx` / `UnicodeApi.sbp`）。不足 API はソース側で `Declare Lib`。

### 7.4 Math（IEEE Double）

角度はラジアン（`Double`）。`Sin` / `Cos` はマクローリン展開。円周率は `MathPi()`、ネイピア数は `MathE()`（`Const` は整数と文字列だけで、`Double` は持てないため Function）。

```
Dim hpi As Double
hpi = MathPi() / 2
Print Sin(hpi)        ' ≒ 1
Print Cos(0)          ' = 1
Print SinDeg(30)      ' ≒ 0.5
Print Log(MathE())    ' ≒ 1
```

主な関数: `MathDiv` / `MathMod`（整数ヘルパ） / `Abs` / `Sgn` / `Min` / `Max` / `Sqr` /
`Sin` / `Cos` / `Tan` / `SinDeg` / `CosDeg` / `Atn` / `Exp` / `Log` / `Log10` /
`Fix` / `Int` / `Rnd` / `Randomize` / `DegToRad` / `RadToDeg`。
`CDbl` / `CSng` / `CInt` は `CvtNum.abp`（`CDbl` は Double、`CSng` は Single、`CInt` は四捨五入した Long。0.5 は 0 から遠い側）。

- 小数リテラル・`Function As Double` / Double 仮引数はすべて IEEE Double ビット
- N88 `CIRCLE` の角度・aspect も `Double`（内部の千分率表現は廃止）
- `Input` / `Input #` の `Double`/`Single` は十進文字列を `ValDouble` で IEEE 化（`Single` はその後 `cvtsd2ss`）
- `Rnd()` は `[0, 1)` の Double。`Abs` は Double 引数
- `-actba32` でもスカラーの Double 演算・`Math.abp`・`StrD$` は動く。`Print` の Double 自動変換と、配列要素・UDT フィールドの 8 バイト転送は 64bit のみ

`Space$(n)` は `Space.abp` から常時利用可。ネストした関数呼び出しは対応する。複雑な入れ子は一時変数経由が安全。

`StrD$(d As Double)` は `DoubleStr.abp` から常時利用可。`Print` が Double 式を表示するとき自動で呼ばれる（64bit）。

サンプル: `src/actba64/samples/math_test.abp` / テスト: `test/t_math_*.abp` / `test/t_double_lit*.abp` / `test/t_dbl_func.abp`

### 7.5 ファイル I/O（`BasicFile.abp`）

番号は **1..16**。実体は [`src/Include/default/BasicFile.abp`](../src/Include/default/BasicFile.abp)（`default.idx` で常時挿入）。

#### Open / Close

```
Open パス [For Input | Output | Append] As [#]番号
Close [[#]番号]          ' 省略時は 1..16 をすべて閉じる
```

| `For` | 動作 |
|---|---|
| （省略） | 読み書き（ランダム向け。`OPEN_ALWAYS`） |
| `Input` | 読み取り専用。内容をメモリバッファへ（`Input #` 用） |
| `Output` | 書き込み専用（新規作成） |
| `Append` | 追記（末尾へシーク） |

パス式の直後に文の `As` が続くため、パス側では **`As` キャストを解釈しない**（`Open path As 1` 可）。

#### Input #（順次）

```
Input #番号, 変数 [, 変数 ...]
```

カンマ／改行区切りの次フィールドを読む。変数は `String` / `Long` / `Byte` / `Single` / `Double`（数値は stdin `Input` と同じ変換）。

#### Field / Get # / Put #（ランダム）

```
Field #番号, フィールド長バイト
Get #番号, レコード番号, 文字列変数   ' レコードは 1 始まり
Put #番号, レコード番号, 式           ' 短い文字列は空白パディング、長い分は切り詰め
```

`Open ... As`（`For` 省略）で開いたうえで `Field` する。オフセットは `(レコード - 1) * フィールド長`。

#### Write / Print #

```
Write [#番号,] [式 [, 式 ...]] [;]
Print #番号, [式 [, 式 ...]] [;]
```

- `Write` で `#番号` なし → 標準出力。`Print #` は番号必須
- 値の区切りは **カンマ**（画面 `Print` の空白区切りとは異なる）
- 末尾 `;` なしなら CRLF を付ける
- 数値は `Str$` / `StrD$` で文字列化してから出力

#### Eof / Loc / Lof

```
Eof(番号)   ' 終端なら -1、それ以外 0
Loc(番号)   ' Input バッファ位置、またはランダムのレコード番号
Lof(番号)   ' Input バッファ長、またはファイルサイズ／レコード数
```

`BasicFile.abp` の関数（番号 1..16）。

#### 未対応

`Field` の割り当て変数形式（BasicHelp の拡張形）は未実装。

回帰テスト例: `src/actba64/test/t_open_close.abp`、`t_input_hash*.abp`、`t_field_get_put.abp`、`t_write_file.abp`、`t_print_file.abp`、`t_eof_loc_lof.abp`

### 7.6 カメラと射影（`dx_camera.sbp`）

`Include\d3d11\dx_camera.sbp`。`dx_graphics.sbp` が取り込む。D3D11 には固定機能の変換がないので、結果は行優先 4×4 の `g_dxProj` / `g_dxView`（`Single` 16 個、D3DX の `D3DMATRIX` と同じ並び）に入る。

```
dx_SetProjection(angle, aspect, nearclip, backclip)
dx_SetCamera(pEye, pAt, pUp)
dx_SetCullMode(CullMode)
```

- `angle` は視野角（ラジアン）。`aspect` はビュー空間の幅/高さ。`D3DX_PI` は `MathPi()` と同じ値
- 射影は `D3DXMatrixPerspectiveFovLH`、カメラは `D3DXMatrixLookAtLH`
- ポインタが 0 の `dx_SetCamera` は行列を変えない
- `dx_SetCullMode` は `D3DCULL_NONE` / `D3DCULL_CW` / `D3DCULL_CCW`。デバイスが無いときは何もしない。前面は時計回り（`D3DCULL_CCW` が背面カリング）
- シェーダの定数バッファへは `VarPtr(g_dxProj[0])` / `VarPtr(g_dxView[0])` を渡す

### 7.7 条件付きコンパイル

```
#define USE_FOO
#ifdef USE_FOO
    Print "on"
#else
    Print "off"
#endif

#ifndef _WIN64
#endif
```

- `#define 名前` はその名前を定義する（置換テキストは持たない）。無効な分岐の中では定義しない
- `#ifdef` / `#ifndef` / `#else` / `#endif`。ネストできる（深さ 32）
- 名前の比較は大小文字を無視する
- 自動定義は **`_AB_VER4`** と **`_ACTBA64`**。64bit のときだけ **`_WIN64`**（`-actba32` では定義しない）。**`_DEBUG` は自動定義しない**

---

## 8. WinAPI / IAT

`api.idx` / `UnicodeApi.sbp` の `Declare`（およびソース側 Declare）で認識した API はインポートテーブル（IAT）に載る。  
`Lib` は **任意の DLL 名**（システム DLL に限らない。自作・C/C++ 製も可）。拡張子省略時は `.dll` を付与（`Lib "mydll"` → `mydll.dll`）。

解決は **起動時の IAT**（静的インポート）。`LoadLibrary` / `GetProcAddress` による実行時ロードは別途 API を `Declare` して自分で呼ぶ。

### 8.1 自作 DLL（C/C++）

```basic
Declare Function MyAdd Lib "mydll" Alias "MyAdd" (ByVal a As Long, ByVal b As Long) As Long
```

| 注意 | 内容 |
|---|---|
| 呼び出し規約 | 既定（64bit）は Microsoft x64、`-actba32` は stdcall。DLL 側も合わせる |
| C++ 名前 | `extern "C"` でエクスポートするか、マングル名を `Alias` に書く |
| 配置 | 実行時に OS の DLL 検索パスで見つかること（通常は exe と同ディレクトリ） |
| 回帰 | `t_decl_any_lib.abp`（任意 Lib 登録）、`t_decl_lib_norm.abp`（拡張子正規化） |

### 8.2 共通でよく使うもの（kernel32）

`ExitProcess`, `GetCommandLineA`, `lstrlenA`, `lstrcpyA`, `lstrcatA`,  
`CreateFileA`, `ReadFile`, `WriteFile`, `CloseHandle`, `GetFileSize`, `SetFilePointer`,  
`GetFileAttributesA`, `GetProcessHeap`, `HeapAlloc`, `HeapFree`, `GetStdHandle`

### 8.3 `api.idx` に既にあるもの / ソースで足すもの

`GetModuleFileNameA`, `CreateProcessA`, `WaitForSingleObject`, `GetTickCount`,  
user32（`MessageBoxA` 等）、gdi32（`CreatePen` / `Ellipse` / `BitBlt` 等）、  
`PeekMessageA` / `MsgWaitForMultipleObjects` などは `api.idx` の Declare で解決する。

不足 API・自作 DLL はソース側で `Declare Lib`。未登録かつ未 `Declare` の呼び出しはコンパイルエラーです。

### 8.4 DLL を出力する

`.pj` の `#MODULETYPE=1` で PE DLL を出します。`#MODULETYPE=0` と省略時は EXE です。

```
Function Export SampleFuncName() As Long
    SampleFuncName = 123456
End Function

Sub Export Init()
End Sub
```

`Export` を付けた `Function` / `Sub` だけがエクスポートされます。名前はソースの綴りのまま、名前表はバイト順の昇順です。上限は 64 個です。戻り値のある `Function Export` は、通常の `Function` と同じく値を返します。

入口は名前が `DllMain` の手続きです（大小無視。無いと `error: DLL requires Function Export DllMain`）。先頭の `JMP` がそこへ飛ぶので、ローダーが渡した引数はそのまま届きます。64bit は `RCX` / `RDX` / `R8`、32bit は stdcall のスタックです。サンプルの形は次のとおりです。

```
Function Export DllMain(hinstDLL As HINSTANCE, fdwReason As DWord, lpvReserved As VoidPtr) As Long
    Select Case fdwReason
        Case DLL_PROCESS_ATTACH
            _System_StartupProgram()
            DllMain = 1
    End Select
End Function
```

`DLL_PROCESS_ATTACH`（1）/ `DLL_PROCESS_DETACH`（0）/ `DLL_THREAD_ATTACH`（2）/ `DLL_THREAD_DETACH`（3）は `WinConsts.sbp` にあります。`PROCESS_ATTACH` では 0 以外を返します。0 だとローダーは DLL をアンロードします。

`_System_StartupProgram` をソースが定義していなければ、コンパイラが合成します。中身は EXE の main と同じ GC 初期化とモジュール文で、`ExitProcess` は呼ばず戻ります。ソースに同名の手続きがあるときは、それを使います。

優先イメージベースは EXE（64bit `0x140000000`、32bit `0x400000`）と重ならないよう、64bit DLL は `0x180000000`、32bit（`-actba32`）は `0x10000000` です。再配置（`.reloc`）は出しません。このベースが空いていればロードできます。

`src\actba64` からの例です。`-o` は `#OUTPUT_RELEASE` があるので省略できます。

```text
actba64 samples\dllcall\dllsample\dllsample.pj
actba64 samples\dllcall\dllcall\dllcall.pj
```

`dllsample.dll` は `dllcall.exe` と同じディレクトリに置きます（出力先はそれぞれの `.pj` フォルダです）。回帰は `test/t_dll_host.abp`（`' Prebuild:` で DLL を先に出します）。

---

## 9. 32bit / 64bit ターゲット

同じ言語・同じパーサです。切替は CLI の `-actba32` のみ。

| 観点 | 既定（64bit） | `-actba32` |
|---|---|---|
| 出力 | PE32+ / AMD64 | PE32 / i386 |
| ポインタ / `String` / `HANDLE` | 8 バイト | 4 バイト |
| `Long` | 4 | 4（LP64 ではない） |
| 呼び出し | Microsoft x64（RCX/RDX/R8/R9 + シャドウスペース） | stdcall（`[esp+i*4]`、呼び出し後は callee が pop） |
| `Declare Lib` | ○ | ○ |
| DLL 優先ベース | `0x180000000` | `0x10000000` |
| `Double` 演算 | ○（SSE。`rax`） | ○（SSE2。値は `edx:eax`。配列要素・UDT フィールドは未） |
| N88 `LINE`/`CIRCLE` 文 | ○ | ○ |
| `SizeOf`（ポインタを含む UDT） | ポインタ 8 バイト込み | ポインタ 4 バイト込み（期待サイズを 64bit 決め打ちしない） |

`#PLATFORM=32` は AB4.20 の stage0 ホスト用で、この切替とは無関係です。

---

## 10. 非対応（意図的）

- ActiveBasic 全互換、イベント駆動。`Class` は [§3.3](#33-class)（`Inherits` / `Virtual` は部分対応。`New` / `Delete` は対応。`Super` は未対応）
- `Single` の汎用演算。`Double` の演算・`Math.abp`・小数リテラル・N88 `CIRCLE` 角度は IEEE Double（64bit と `-actba32`。32bit の配列要素・UDT フィールド転送と、`Print` の Double 変換は未）
- ネスト手続き
- `#resource` の MENU / DIALOG / VERSIONINFO（ICON 文は隣の `rc.exe`。ファイル全体の RCDATA 埋め込みは対応）
- 高度な最適化

---

## 11. 最小例

```
#console

Dim s As String
Open "data.txt" For Input As 1
Input #1, s
Close 1
Print s
ExitProcess(0)
```

```
#console

Dim buf As String
Open "read.txt" As #1
Open "write.txt" As #2
Field #1, 10
Field #2, 10
Get #1, 1, buf
Put #2, 1, buf
Close
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

```
#N88BASIC

Line(40, 40)-(180, 140), 7, B
Circle(320, 90), 50, 5
Sleep(300)
End
```

---

## 関連

- ドキュメント一覧: [index.md](./index.md)
- ビルド: [build.md](./build.md)
- ActiveBasic との相違: [different.md](./different.md)
- 未実装メモ: [todo.md](./todo.md)
- エディタ向け actba64 リファレンス: [src/projecteditor/help/actba64_ref.html](../src/projecteditor/help/actba64_ref.html)（ヘルプメニュー / F1）
- N88 図形サンプル: [src/actba64/samples/n88_shapes.abp](../src/actba64/samples/n88_shapes.abp)
- Math サンプル: [src/actba64/samples/math_test.abp](../src/actba64/samples/math_test.abp)
- 回帰テスト: `src/actba64/test/`（`' Target: actba64`。`run_test2.ps1` / `-Actba32`）。GUI 系は既定 SKIP（`-IncludeGui`）。詳細は [build.md](./build.md)
