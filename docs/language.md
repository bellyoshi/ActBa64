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
- 小数リテラル（N88 等）: `1.5` → 千分率 `1500`（`TK_FLOAT`）
- 文字列リテラル: `"..."`（`""` で `"`）
- 大小文字は区別しない
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
| `#strict` | 無視 |
| `#include "path"` | ファイル挿入（深さ上限あり） |
| その他 `#...` | 字句レベルで行スキップ、または実装依存で無視 |

`Include\default\default.idx`（Win32 型・定数・`Math.abp`・`Sleep.abp`・`Space.abp`）は **常時** 先頭へ挿入される（[`src/Include`](../src/Include)）。  
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

- 角度はラジアン（小数可。内部は千分率。`3.14` → 3140）。省略または `start=end` で全周
- 負の角度は絶対値で円弧し、中心から半径線を引く（扇形）
- `aspect` は 垂直半径/水平半径（省略時 1.0）
- `F` で塗りつぶし（タイルストリングは未対応）
- 実行後 LP は円の中心へ移動

N88 `LOCATE` / `PAINT`:

```text
LOCATE x, y                 ' または Locate(x, y) — 桁 x, 行 y（0 始まり。本家 N88 の 行,桁 1 始まりとは異なる）
PAINT (x, y), color1 [, color2]
```

- `LOCATE` 後の `Print` は窓上の文字位置へ描画（`;` なしなら次行へ）
- 数値の `Print` は `Str$` 相当で文字列化してから描画
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
| `Single` | 4 | 4 | サイズと格納。演算は千分率経由が中心 |
| `Long` / `DWord` / `Integer` | 4 | 4 | 別名あり |
| `Double` | 8 | **8** | IEEE 倍精度。64bit は加減乗除・比較。`-actba32` は SSE 未実装 |
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
| `Input` | ○（プロンプト文字列なし。数値は十進変換） |
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
`As` は例: `&H12345678 As Word` → `&H5678`。`#strict` 自体は未実装（警告なし）。

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
StrPtr(s)
MakeStr(p As *Byte)
RGB(r, g, b)
LOWORD(n)
MakeIntResource(id)
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

- 表現: ActiveBasic 4.20 互換。ヒープ／静的データの直前 4 バイトに長さ（dword）、ポインタはデータ先頭を指す
- `Len(s)` はその長さを返す（`lstrlen` ではない）。`Chr$(0)` は長さ 1
- 末尾に WinAPI 用の NUL を付けるが、データ中の埋め込み NUL も有効
- `StrPtr(s)` はデータ先頭（恒等）。`MakeStr(p)` は NUL 終端 `BytePtr` から長さ付き String を複製
- 連結・`Left$` / `Mid$` 等は都度ヒープ確保
- 内容比較は長さ付き辞書順（埋め込み NUL 対応）
- **actba64 の String ヒープ**はハイブリッド GC（代入時の自動 `StrFree` はしない）:
  - **Precise**: `String` / `String` 配列のグローバル・ローカルスロットをコンパイル時に root 登録し、セーフポイントで無条件マーク
  - **Conservative**: ユーザ globals とスタックをポインタ幅刻み走査し、ヒープタグ付き登録ブロックのみマーク
  - 確保は `StrHeapAlloc`、回収は `StrCollect`（ループ頭・`Print`/`Input` 後・関数終了前など）
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

`Include\default\default.idx`（Win32 型・定数・`Math.abp`・`Sleep.abp`・`Space.abp`）は **常時** 先頭へ挿入される。実体はリポジトリの [`src/Include`](../src/Include) 1 本。コンパイラは exe 隣、その親、カレントの `Include\` を順に探す。  
`UnicodeApi.sbp`（Unicode 版 API の `Declare Lib`）は Preproc が別途挿入する。  
加えてソースのディレクティブでプロファイルを挿入する:

| ディレクティブ | 挿入される idx |
|---|---|
| `#console` | `Include\console\console.idx` |
| `#n88basic` / `#prompt` | `Include\N88BASIC\n88basic.idx` |

**`Declare Lib` 群は載せない**（IAT 解決）。

### 7.3 Math（固定小数点・千分率）

`1.0 = 1000`。角度はラジアン千分率（`MATH_PI = 3142`）。`Sin` / `Cos` はマクローリン展開。

```
Print Sin(MATH_HPI)   ' ≒ 1000
Print Cos(0)          ' = 1000
Print SinDeg(30)      ' ≒ 500
```

主な関数: `MathDiv` / `MathMod` / `Abs` / `Sgn` / `Min` / `Max` / `Sqr` /
`Sin` / `Cos` / `Tan` / `SinDeg` / `CosDeg` / `Atn` / `Exp` /
`DegToRad` / `RadToDeg`

`Space$(n)` は `Space.abp` から常時利用可。ネストした関数呼び出しは対応する。複雑な入れ子は一時変数経由が安全。

サンプル: `src/actba64/samples/math_test.abp`

---

## 8. WinAPI / IAT

コンパイラが名前を認識した API はインポートテーブルに載る。

### 8.1 共通でよく使うもの（kernel32）

`ExitProcess`, `GetCommandLineA`, `lstrlenA`, `lstrcpyA`, `lstrcatA`,  
`CreateFileA`, `ReadFile`, `WriteFile`, `CloseHandle`, `GetFileSize`,  
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

`#PLATFORM=32` は AB4.20 の stage0 ホスト用で、この切替とは無関係です。

---

## 10. 非対応（意図的）

- ActiveBasic 全互換、イベント駆動。`Class` は [§3.3](#33-class)（`Inherits` / `Virtual` は部分対応。`New` / `Delete` / `Super` は未対応）
- `Single` の汎用演算。`Double` の演算は **64bit のみ**（`-actba32` は SSE 未実装）。N88 角度・`Math.abp` は千分率
- `GoTo` / `GoSub` / `Continue` / `ReDim` / `Enum`
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
- 回帰テスト: `src/actba64/test/`（`' Target: actba64`。`run_test2.ps1` と `run_test2.ps1 -Actba32`）
