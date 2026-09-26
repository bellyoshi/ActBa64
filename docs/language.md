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
- 小数リテラル: `1.5` / `1.12345` など（符号・小数点付き十進）。字句テキストを保持し、**AST 上で IEEE 754 Double ビット**（64bit: `num`=下位32 / `left`=上位32）に変換する。科学記法（`1.0e10`）は未対応。コード生成は `movabs rax, imm64`
- 文字列リテラル: `"..."`（`""` で `"`）
- 識別子の大小文字: **定数・変数・Sub/Function・Type/Class 名は区別する**（AB 4.20 同様。`Foo` と `foo` は別）。**言語キーワード**（`If` / `Then` / `Dim` 等）と **組み込みランタイム名**（`FillMemory` / `malloc` 等）の認識のみ大小無視
- 文の区切りは改行。同一行の `:` 連結可（`a = 1: b = 2`）

行の継続:

```
Print a +_
    b +_
    c
```

行末の `_`（直後の空白・`'注釈` 可）で次行と 1 文に結合する。  
`( )` / `[ ]` 内では、`(` `[` `,` の直後や閉じ括弧前など、パラメータ単位の改行も可（改行は空白扱い）。

### 1.3 ディレクティブ行

| 行 | 意味 |
|---|---|
| `#console` | `Include\console\console.idx` を自動挿入 |
| `#n88basic` / `#N88BASIC` / `#prompt` | N88BASIC 互換モード（[§1.6](#16-n88basic-モード)）。`#prompt` は完全別名 |
| `#USEWINDOW=0\|1` | 0=CUI / 1=GUI。ソース・`.pj` どちらでも可。`#n88basic` / `#prompt` は GUI を強制 |
| `#strict` | 変数代入の型不一致を warning（`As` で抑制） |
| `#include "path"` | ファイル挿入（深さ上限あり） |
| その他 `#...` | 字句レベルで行スキップ、または実装依存で無視 |

`Include\default\default.idx`（Win32 型・定数・`Math.abp`・`Sleep.abp`・`Space.abp`・`DoubleStr.abp`・`BasicFile.abp`）は **常時** 先頭へ挿入される（[`src/Include`](../src/Include)）。  
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
| `#OUTPUT_RELEASE` | AB4.20 の stage0 出力パス。`actba64` の CLI は常に `-o` |
| `#USEWINDOW` | サブシステム（既定 CUI。`#n88basic` で GUI） |
| `#PLATFORM` | AB4.20 用。`actba64` は読まない（対象は `-actba32`） |
| その他 | 無視 |

`#SOURCE` のソースはテキスト結合して **1 コンパイル単位** になる。

### 1.5 CLI

```text
actba64 <src.abp|.pj> [-actba32] -o <out.exe>
```

`-o` は必須。`-actba32` は引数のどこでも可。省略時は PE32+。

エントリは結合後ソースのトップレベル文。終了は `ExitProcess(n)` または `End`（終了コード 0）。  
`#n88basic` 時の `End` は窓を出して閉じるまで待つ（actba64）。

### 1.6 N88BASIC モード

`#n88basic` / `#N88BASIC` / `#prompt` で `Include\N88BASIC\n88basic.idx`（実体は `n88graph.abp`）を挿入する。  
`#prompt` は ActiveBasic 互換の別名で、`#n88basic` と全く同じ動作。

| | 既定（64bit） | `-actba32` |
|---|---|---|
| ライブラリ挿入 | ○ | ○ |
| `LINE` / `CIRCLE` / `LOCATE` / `PAINT` 文 | ○（パーサ） | ○（同じパーサ） |
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
| `Double` | 8 | **8** | IEEE 倍精度。64bit は加減乗除・比較・`Function As Double` / Double 仮引数。`-actba32` は SSE 未実装 |
| `HANDLE` / `HWND` 等 | 4 | **8** | 64bit は `VoidPtr` / `*T`（`HFILE` は 4 のまま） |
| `*T` | 4 | **8** | ポインタ |
| `String` | ポインタ相当 (4) | ポインタ相当 (**8**) | 長さプレフィックス付きバイト列（AB4.20 互換） |
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
TypeDef PADD = *Function(a As Long, b As Long) As Long
```

メンバ参照: `x.field` / `p->field` / `a(i)` / `p[i]`（組み合わせ可）。  
関数ポインタ型（`*Function` / `*Sub`）は [§5.2.1](#521-関数ポインタ型)。

---

## 3. 宣言

### 3.1 Const / Dim

```
Const MAX_PATH = 260
Const GENERIC_READ = &H80000000

Dim a As Long
Dim b = 3 As Long
Dim c As Integer = 4
Dim s$
Dim t As String
Dim p As *Byte
Dim buf[259] As Byte
Dim xs(7) As Long
Dim h As COFF_HEADER
```

- `Const`: 整数リテラル（符号付き）中心。複雑な定数式は制限あり
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

- `ByRef` 対応。呼び出し側の `ByVal` は無視してよい
- 戻り値は `Function名 = 式`
- `Exit Sub` / `Exit Function`
- ネストした `Sub`/`Function` は不可
- `Declare Function|Sub ... Lib "dll" [Alias "..."]` 可（IAT に載せる）

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

Dim c As Counter(10)            ' 領域確保 + ctor 呼出
c.Add(32)
x = c.GetValue()
```

- `Class` / `End Class`。メンバ変数は `Type` と同様のオフセット配置
- `Private` / `Public`（未指定は Private）。`Protected` は受理し Public 扱い
- メソッドは暗黙の第1引数 `Me`（オブジェクトポインタ）。呼び出しは `obj.Method(args)`
- コンストラクタ `Sub ClassName(...)` → `Dim obj As ClassName(args)` で自動呼出
- デストラクタ `Sub ~ClassName()` → 局所は手続き末尾、モジュール大域は終了前に呼出
- ctor/dtor 省略時は空の無引数版を暗黙生成
- メソッドはマングル名（例: `Counter_Add`）の通常 `Sub`/`Function` として生成（64bit は `RCX=Me`、32bit は stdcall の第1引数）
- `Inherits` / `Virtual` / vtable 呼び出しは **部分対応**（COM / D3D11 向け。本体なし `Virtual Function|Sub` と継承先へのスロットコピー）
- `p->Release()` のようにポインタ経由で仮想メソッドを呼べる

**未対応:** `New` / `Delete` 演算子、`Super.Method`、メンバ実体クラスの自動 ctor・dtor、アクセス制御の厳密検査

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

With 式
    .field = ...
End With

Print 式
Print 式;
Input 変数          ' String / Long / Byte / Single / Double。stdin から1行
Input #番号, 変数 [, ...]  ' ファイルからフィールド読み取り
Open パス [For Input|Output|Append] As [#]番号
Close [[#]番号]     ' 省略時は全クローズ
Field #番号, バイト長
Get #番号, レコード, 文字列変数
Put #番号, レコード, 式
Write [#番号,] [式 [, ...]] [;]  ' カンマ区切り。番号省略は標準出力
Sleep(ミリ秒)       ' 待ち中もウインドウメッセージを処理
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
| `Print` | ○ |
| `Input` | ○（プロンプト文字列可。数値は十進文字列 → IEEE。`Double`/`Single` は `ValDouble`、整数は `Val`） |
| `Open` / `Close` / `Input #` | ○（`BasicFile.abp`。番号 1..16） |
| `Field` / `Get #` / `Put #` | ○（ランダム。`Open ... As` + Field 長） |
| `Write` | ○（画面または `#番号`。カンマ区切り） |
| `Sleep(ms)` | ○（メッセージポンプ付き・default） |
| `InsMenu` | ○（内部で `InsertMenuA`） |
| `LINE` / `CIRCLE` / `LOCATE` / `PAINT`（N88 文） | ○（`#n88basic`） |

---

## 5. 式

### 5.1 演算子

優先順位（高い順）: `As` キャスト → `^` → 単項 `-` → `* / \ Mod` → `+ - &` → `<< >>` → 関係 → `Not` → `And` → `Or` → `Xor`。  
`* / \` どうし、および `+ -` どうしは同優先で左から右へ評価。関係演算の値は真=`-1` / 偽=`0`。

| 演算 | 対応 |
|---|---|
| `+ - *`（整数） | ○ |
| `+ - * /`（`Double`、64bit） | ○（IEEE。`-actba32` は SSE 未実装） |
| 文字列 `+` / `&`（連結・同義） | ○ |
| 単項 `-` / `Not` | ○ |
| `= <> >< < > <= >=` | ○（値は -1/0。文字列は辞書順。`Double` 比較は 64bit） |
| `And` / `Or` / `Xor` | ○（ビット。条件の And/Or は短絡） |
| `\` `/`（整数除算） | ○（Long では同義） |
| `Mod` | ○ |
| `<<` / `>>`（`>>` は符号付き） | ○ |
| `^`（整数累乗） | ○ |
| `expr As Type`（切捨てキャスト） | ○（String へ/からは不可） |
| `+= -= *= /= \= <<= >>=` / `Mod=` `And=` `Or=` `Xor=` | ○ |
| `++` / `--` | ○ |

文字列の関係演算は辞書順（`lstrcmpA`）。長さが違い途中まで一致したら短い方が小さい。  
`As` は例: `&H12345678 As Word` → `&H5678`。`#strict` 時は異なる型の変数代入が warning（`As` キャストで抑制）。

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
StrD$(d)                 ' Double → 文字列（Include\default\DoubleStr.abp）
StrPtr(s)
MakeStr(p As *Byte)
RGB(r, g, b)
LOWORD(n)
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
- `.rc` はそのままでは不可（`rc.exe` で `.res` 等へ落としてから指定）。ICON/MENU 型リソースは未
- `.pj` の `#RESOURCE=0` は当面無視

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

`Chr$` / `Right$` は組み込み。`Hex$` / `Val` / `InStr` などはライブラリ側。

---

## 7. プリプロセスと標準ヘッダ

### 7.1 `#include`

```
#include "Utils.abp"
```

パスはソース相対（または実装が解決するパス）。循環・深さ超過はエラー。

### 7.2 自動 Include

`Include\default\default.idx`（Win32 型・定数・`Math.abp`・`Sleep.abp`・`Space.abp`・`DoubleStr.abp`・`BasicFile.abp`）は **常時** 先頭へ挿入される。実体はリポジトリの [`src/Include`](../src/Include) 1 本。コンパイラは exe 隣、その親、カレントの `Include\` を順に探す。  
`UnicodeApi.sbp`（Unicode 版 API の `Declare Lib`）は Preproc が別途挿入する。  
加えてソースのディレクティブでプロファイルを挿入する:

| ディレクティブ | 挿入される idx |
|---|---|
| `#console` | `Include\console\console.idx` |
| `#n88basic` / `#prompt` | `Include\N88BASIC\n88basic.idx` |

**`Declare Lib` 群は載せない**（IAT 解決）。

### 7.3 Math（IEEE Double）

角度はラジアン（`Double`）。`Sin` / `Cos` はマクローリン展開。円周率は `MathPi()`、ネイピア数は `MathE()`（`Const` は整数のみのため Function）。

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
`Fix` / `Int` / `Rnd` / `Randomize` / `DegToRad` / `RadToDeg`

- 小数リテラル・`Function As Double` / Double 仮引数はすべて IEEE Double ビット
- N88 `CIRCLE` の角度・aspect も `Double`（内部の千分率表現は廃止）
- `Input` / `Input #` の `Double`/`Single` は十進文字列を `ValDouble` で IEEE 化（`Single` はその後 `cvtsd2ss`）
- `Rnd()` は `[0, 1)` の Double。`Abs` は Double 引数
- `-actba32` では SSE 未実装のため Double 演算テストはスキップ

`Space$(n)` は `Space.abp` から常時利用可。ネストした関数呼び出しは対応する。複雑な入れ子は一時変数経由が安全。

`StrD$(d As Double)` は `DoubleStr.abp` から常時利用可。`Print` が Double 式を表示するとき自動で呼ばれる（64bit）。

サンプル: `src/actba64/samples/math_test.abp` / テスト: `test/t_math_*.abp` / `test/t_double_lit*.abp` / `test/t_dbl_func.abp`

### 7.4 ファイル I/O（`BasicFile.abp`）

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

#### Write

```
Write [#番号,] [式 [, 式 ...]] [;]
```

- `#番号` なし → 標準出力
- 値の区切りは **カンマ**（`Print` とは異なる）
- 末尾 `;` なしなら CRLF を付ける
- 数値は `Str$` / `StrD$` で文字列化してから出力

#### 未対応

`Print #`、`Eof` / `Loc` / `Lof`、`Field` の割り当て変数形式（BasicHelp の拡張形）は未実装。

回帰テスト例: `src/actba64/test/t_open_close.abp`、`t_input_hash*.abp`、`t_field_get_put.abp`、`t_write_file.abp`

---

## 8. WinAPI / IAT

コンパイラが名前を認識した API はインポートテーブルに載る。

### 8.1 共通でよく使うもの（kernel32）

`ExitProcess`, `GetCommandLineA`, `lstrlenA`, `lstrcpyA`, `lstrcatA`,  
`CreateFileA`, `ReadFile`, `WriteFile`, `CloseHandle`, `GetFileSize`, `SetFilePointer`,  
`GetFileAttributesA`, `GetProcessHeap`, `HeapAlloc`, `HeapFree`, `GetStdHandle`

### 8.2 `Declare` やマップで足しやすいもの

`GetModuleFileNameA`, `DeleteFileA`, `CreateProcessA`, `WaitForSingleObject`, `GetTickCount`,  
一部 user32（`MessageBoxA` 等）

未登録かつ未 `Declare` の呼び出しはコンパイルエラーです。

N88 / `Sleep` 向けに gdi32（`CreatePen` / `Ellipse` / `Arc` / `Pie` / `BitBlt` 等）と `PeekMessageA` / `MsgWaitForMultipleObjects` もマップされる。

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
| `Double` 演算 | ○（SSE） | 未（テストはスキップ） |
| N88 `LINE`/`CIRCLE` 文 | ○ | ○ |
| `SizeOf`（ポインタを含む UDT） | ポインタ 8 バイト込み | ポインタ 4 バイト込み（期待サイズを 64bit 決め打ちしない） |

`#PLATFORM=32` は AB4.20 の stage0 ホスト用で、この切替とは無関係です。

---

## 10. 非対応（意図的）

- ActiveBasic 全互換、イベント駆動。`Class` は [§3.3](#33-class)（`Inherits` / `Virtual` は部分対応。`New` / `Delete` / `Super` は未対応）
- `Single` の汎用演算。`Double` の演算・`Math.abp`・小数リテラル・N88 `CIRCLE` 角度は **64bit IEEE Double**（`-actba32` は SSE 未実装）
- `GoTo` / `GoSub` / `ReDim`
- ネスト手続き
- `#resource` の `.rc` 直接コンパイル、ICON/MENU など型付きリソース（ファイル全体の RCDATA 埋め込みは対応）
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
