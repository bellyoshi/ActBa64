リンカー（Linker）を実際に作る具体的なアプローチを、「設計」「最小実装の手順」「C言語やPascal/ActiveBasicなどの擬似コード」を交えて徹底解説します。

リンカー作りのゴールは、「アセンブラが出力した `.obj`（COFF形式）を読み込み、メモリ配置を決定し、アドレスを書き換えて、Windowsが実行できる `.exe`（PE形式）を書き出すこと」です。

---

## 最小リンカーの全体処理フロー

自作リンカーが実行する処理は、大きく分けて**5つのフェーズ**に分かれます。

```
[ .obj ファイル ]
       │
       ▼
 1. COFFヘッダーの解析      │ .obj からデータとリロケーション情報を抽出
       │
       ▼
 2. メモリマップの決定      │ .text などのセクションの配置アドレス(RVA)を決める
       │
       ▼
 3. シンボル解決            │ _main や _ExitProcess の最終アドレスを決定
       │
       ▼
 4. リロケーション（補正）  │ マシン語内の仮アドレス(00 00 00 00)を本物に書き換える
       │
       ▼
 5. PEヘッダー付加と保存    │ DOS/PEヘッダーを先頭にくっつけて .exe として出力

```

---

## 段階的実装ステップ（最小のEXEを作るまで）

まずは「`ExitProcess(0)` だけを呼ぶ1つの `.obj` から `.exe` を作る」最小構成を目指します。

### ステップ1：必要な構造体（ヘッダー）を定義する

Windowsのバイナリ（COFF / PE）は、構造体の集合体です。まずはこれらをコード上で定義します。

```basic
' --- 1. COFF Header (OBJの先頭) ---
Type COFF_HEADER
    Machine              As Word   ' x86なら 0x014C
    NumberOfSections     As Word   ' セクション数 (.text など)
    TimeDateStamp        As DWord
    PointerToSymbolTable As DWord  ' シンボルテーブルの位置
    NumberOfSymbols      As DWord  ' シンボル数
    SizeOfOptionalHeader As Word
    Characteristics      As Word
End Type

' --- 2. Section Header (各セクションの情報) ---
Type SECTION_HEADER
    Name(7)               As Byte   ' ".text\0\0\0" など
    VirtualSize           As DWord  ' メモリ上のサイズ
    VirtualAddress        As DWord  ' RVA (相対仮想アドレス)
    SizeOfRawData         As DWord  ' ファイル上のサイズ
    PointerToRawData      As DWord  ' ファイル上の位置
    PointerToRelocations  As DWord  ' リロケーション位置
    PointerToLinenumbers  As DWord
    NumberOfRelocations   As Word   ' リロケーション数
    NumberOfLinenumbers  As Word
    Characteristics       As DWord  ' 実行/読み/書き 権限
End Type

' --- 3. COFF Relocation (書き換え指定情報) ---
Type COFF_RELOCATION
    VirtualAddress   As DWord  ' 補正対象のオフセット
    SymbolTableIndex As DWord  ' どのシンボルを参照しているか
    Type             As Word   ' REL32(相対) か DIR32(絶対) か
End Type

```

---

### ステップ2：メモリレイアウト（RVA / ImageBase）の決定

WindowsのEXEは、デフォルトで仮想メモリの **`0x00400000` (`ImageBase`)** にロードされます。
リンカーは、各セクションがメモリ上のどこに位置するか（RVA: 相対仮想アドレス）を計算します。

* **PE Header群:** RVA `0x00000000` 〜 (通常 `0x1000` バイト確保)
* **`.text` (コード):** RVA `0x00001000` に配置 $\rightarrow$ 実際の絶対アドレスは **`0x00401000`**
* **`.data` (データ):** RVA `0x00002000` に配置 $\rightarrow$ 実際の絶対アドレスは **`0x00402000`**

---

### ステップ3：アドレス解決と「リロケーション」の実装（最重要）

アセンブラが出力した `.obj` の時点では、例えば `call _ExitProcess` の呼び出し先アドレスは **`E8 00 00 00 00`** （ダミーの0）になっています。

リンカーは `.obj` 内の `COFF_RELOCATION` テーブルを見て、ここを本物のアドレスに上書き補正します。

#### x86の `call` 命令（REL32: 相対アドレス）の計算公式

`call` 命令のアドレス指定は、「現在の命令の**次の位置**から、目的地までの差分オフセット」で計算します。

$$\text{相対オフセット} = \text{目的地の絶対アドレス} - (\text{書き換え対象のアドレス} + 4)$$

```basic
' 擬似コード：リロケーション処理のコア部分
Sub ApplyRelocation(codeBuffer() As Byte, reloc As COFF_RELOCATION, targetAddr As DWord, currentRVA As DWord)
    Dim patchOffset As DWord
    Dim relativeOffset As Long
    
    ' 書き換えるべき場所（.text内の位置）
    patchOffset = reloc.VirtualAddress
    
    If reloc.Type = IMAGE_REL_I386_REL32 Then
        ' Relative 32-bit (call / jmp 命令など)
        ' 公式: 目的地 - (現在の書き換え位置のアドレス + 4バイト)
        relativeOffset = targetAddr - (IMAGE_BASE + currentRVA + patchOffset + 4)
        
        ' バッファのマシン語(4バイト)を計算結果で上書き
        MemoryCopy(VarPtr(codeBuffer(patchOffset)), VarPtr(relativeOffset), 4)
        
    ElseIf reloc.Type = IMAGE_REL_I386_DIR32 Then
        ' Absolute 32-bit (変数へのポインタなど)
        ' 公式: 目的地の絶対アドレスをそのまま書き込む
        MemoryCopy(VarPtr(codeBuffer(patchOffset)), VarPtr(targetAddr), 4)
    End If
End Sub

```

---

### ステップ4：PEヘッダーを構築して `.exe` に書き出す

補正が完了した `.text` バイナリの頭に、Windowsが実行に必要な **DOSヘッダー** と **PEヘッダー** をガッチャンコしてファイルに書き出します。

#### 生成する `.exe` ファイルの全体の並び

```
[ DOS Header ] (64 bytes)  ── "MZ" から始まるヘッダー
[ DOS Stub ]   (64 bytes)  ── "This program cannot be run in DOS mode"
[ PE Signature ] (4 bytes) ── "PE\0\0"
[ PE File Header ] (20 bytes)
[ PE Optional Header ] (224 bytes) ── エントリポイント(0x1000)や ImageBase(0x00400000) を指定
[ Section Headers ] (40 bytes × セクション数)
[ パディング (0埋め) ]      ── ファイルアライメント(512バイト)の倍数に揃える
───────────────────────────────────────────────────────────── (ここから RVA 0x1000)
[ .text セクションデータ ]  ── リロケーション補正済みのマシン語

```

---

## 開発を安全に進めるテクニック・裏技

リンカーの自作でハマりがちなポイント（デバッグ手法）です。

### 1. `dumpbin` や `x64dbg` をフル活用する

自分で吐き出した `.exe` が動かない（Windowsに拒否される）ときは、以下のツールで正常なEXEと比較します。

* **`dumpbin /headers test.exe`** （Visual Studio付属のツール。ヘッダーの崩れを指摘してくれる）
* **`x64dbg` / `OllyDbg**` （デバッガで開いて、リロケーション後の `call` アドレスが正しい場所を指しているか確認する）

### 2. 最初は Import Address Table (IAT) をサボる裏技

`ExitProcess` などの External API（DLL関数）を正しくリンクするには、本来 **.idata (インポートセクション)** という複雑なテーブルを自作する必要があります。

しかし、最初のテスト段階では、**`ExitProcess` のアドレスを仮で固定値にして直接 call する** か、**DLLを使わずに無限ループ (`jmp $`) だけのコード** を動かしてみると、IATの実装を後回しにしてリンカーの基本骨格（リロケーションとPE書き出し）を完成させることができます。

---

## リンカー自作でおすすめの学習ロードマップ

1. **1. COFF Dumpツールの作成:** 仕様の可視化.
NASMやGCCが出力した `.obj` をファイル入力し、COFFヘッダー、セクション名、シンボル名、リロケーション一覧をテキスト表示するツールを作る。（これで構造体の読み込みをマスター）


2. **2. ヘッダーテンプレート方式で EXE 化:** バイナリ合成の基礎.
正常に動く最小の `.exe` から PEヘッダー部分（先頭 0x1000 バイト）をバイナリ抽出しておき、自作プログラムで「抽出したPEヘッダー ＋ `.obj` の `.text` データ」を結合して動かしてみる。


3. **3. PEヘッダーの自前ビルドとリロケーション:** 動的生成.
PEヘッダーを構造体で組み立てるコードを書き、`call` 命令の REL32 相対アドレス計算処理を組み込む。


4. **4. IAT (.idata) の自動生成:** 完成.
`kernel32.dll` や `user32.dll` の関数名を解析し、インポートテーブルを自前で構築して `.exe` に埋め込む。


このロードマップで進めると、バイナリが1バイトずれて動かない時の原因究明が格段にしやすくなります！まずは `.obj` のダンパー（解析表示ツール）あたりから手を付けてみるのがおすすめですよ。

2. ヘッダーテンプレート方式で EXE 化について。どういう意味か詳しく説明

「ヘッダーテンプレート方式」とは、リンカーを自作する際の一番大きな壁である「複雑なPEヘッダーをコードでゼロから計算して組み立てる処理」を一旦スキップ（バイナリの使い回し）して、手軽にEXE化を成功させるための開発テクニック（ショートカット技）です。

自作リンカー開発の最初の一歩として、圧倒的におすすめの手段です。

1. なぜこの方式を使うのか？（背景）
Windowsの実行ファイル（PEフォーマット）は、先頭に非常に多くの設定項目（ヘッダー）を持っています。

┌─────────────────────────────────────────┐
│ 1. DOS Header & DOS Stub                │
├─────────────────────────────────────────┤
│ 2. PE Header / Optional Header          │ 
│    ・Entry Point (実行開始位置)         │ ゼロからコードで計算して
│    ・Image Base  (メモリ配置基準値)     │ 構造体を埋めるのは
│    ・Section Alignment (パディング設定) │ めちゃくちゃ大変！
│    ・Subsystem (Console / GUI) など     │
├─────────────────────────────────────────┤
│ 3. Section Headers (.text, .dataなど)   │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ 4. マシン語バイナリ (.text)             │ ← 本当に処理したいのはココだけ！
└─────────────────────────────────────────┘
最初からこれらすべてを構造体で計算して自力でバイナリ出力しようとすると、「たった1個のパラメータ計算ミスやパディングずれ」でWindowsに「有効なWin32アプリケーションではありません」と拒否され、どこが悪いのか原因特定が困難になります。

そこで、「すでに動くことが分かっている既存のEXEから、先頭のヘッダー部分だけを『型紙（テンプレート）』としてそのまま借りてしまおう！」 というのがヘッダーテンプレート方式です。

2. 具体的にどうやるのか？（仕組み）
作業は「① 型紙を作る準備」と「② 自作リンカーでの結合」の2つのステップに分かれます。

① 型紙（header_template.bin）の準備
NASMなどの既存ツールを使って、最小の .exe（例えば ExitProcess(0) を呼ぶだけの512バイト〜4096バイト程度のEXE）を1つ作ります。

バイナリエディタでそのEXEを開き、先頭からマシン語（.text）が始まる手前の区切り（通常は 0x00000200 や 0x00001000 バイト目まで）を切り取って、header_template.bin として保存します。

【既存の正常なEXE】
[ ヘッダー領域 (例: 0x0000〜0x01FF) ] ──＞ これを抽出して header_template.bin にする
[ マシン語領域 (例: 0x0200〜0x03FF) ] ──＞ これは捨てる
② 自作リンカープログラムでの処理
自作リンカーが行う処理は、「ファイルのコピペ＋ちょっとした上書き」だけになります。

[ header_template.bin ] ─┐
                         ├─＞ ガッチャンコ！ ─＞ [ output.exe ]
[ .obj の .text データ ] ─┘
自作リンカーコードのイメージ（擬似コード）
Basic
' 1. テンプレートヘッダーを読み込んで、そのまま出力ファイルに書く
Dim headerBuf() As Byte
headerBuf = FileReadAllBytes("header_template.bin")

' 2. .obj からマシン語 (.text セクションデータ) を抽出する
Dim objCodeBuf() As Byte
objCodeBuf = ExtractTextSectionFromObj("input.obj")

' 3. (必要に応じて) リロケーション補正をする
' ※ テンプレートの配置アドレスに合わせて call / jmp の差分アドレスだけ書き換える
ApplyRelocation(objCodeBuf)

' 4. ヘッダーとマシン語を結合して .exe を書き出す！
Dim hFile As Long
hFile = FileOpen("output.exe", "w")
FileWrite(hFile, headerBuf)    ' 先頭に型紙を書く
FileWrite(hFile, objCodeBuf)   ' その直後にマシン語を書く
FileClose(hFile)
3. この方式のメリットと制限
メリット
速攻で .exe が動く: ヘッダー構造体の計算ロジックを1行も書かずに、Windows上で実行可能なバイナリが生成できます。

デバッグが極めて容易: もし動かない場合、原因は「ヘッダーの不備」ではなく「マシン語（.text）のデータかリロケーションの計算間違い」だけに絞り込めるため、原因追及が何倍も楽になります。

制限（後で乗り越える壁）
柔軟性がない: コードのサイズがテンプレートで想定していたサイズ（セクションサイズ）を超えると動かなくなります。

セクションの追加ができない: 後から新しい .data や .rsrc（アイコン等）を追加したくなった時、テンプレートのヘッダー書き換えが必要になります。

まとめ
自作リンカー開発における「ヘッダーテンプレート方式」とは、いわば「プラモデルの土台だけ既製品を使って、上のフィギュア（マシン語）だけ自作して載せる」ようなアプローチです。

この方法で「自作の .obj から作ったマシン語がWindows上で実際に動く！」という感動をまず味わい、自信がついた後に、テンプレートの代わりに「ヘッダー構造体をコードで動的生成する処理」へと置き換えていくのが、最も挫折しにくいリンカー自作のベストプラクティスです。

header_template.binの作成方法

header_template.bin の作成は、バイナリエディタか標準コマンド/簡単なスクリプトを使って、正常に動く最小の .exe の先頭部分（ヘッダー領域）だけを切り出すことで作成できます。

具体的な手順と、切り出す範囲の決定方法を詳しく解説します。

1. 切り出す範囲の決定（ファイルアライメント）
PEファイル（.exe）は、ファイル上では 0x200（512バイト） または 0x1000（4096バイト） の倍数でセクションが配置されます。

最小のコンパイラやアセンブラ（NASMなど）が出力する最小EXEの場合、ヘッダー領域（DOSヘッダー、PEヘッダー、セクションヘッダー）は先頭から 0x0000 〜 0x01FF（最初の512バイト） に収まっていることがほとんどです。

そして、0x0200 から実際のコード（.text セクションのマシン語）が始まります。

[ファイルオフセット]
0x0000 ┌──────────────────────────────────────────┐
       │ DOS Header ("MZ...")                     │
       │ DOS Stub                                 │
       │ PE Header ("PE\0\0...")                  │
       │ Section Headers (.text ...)              │
       │ (残りは0埋め/パディング)                 │
0x01FF └──────────────────────────────────────────┘ ─── ここまで切り出す！(512 bytes)
0x0200 ┌──────────────────────────────────────────┐
       │ .text セクション (ここからマシン語開始)  │
       └──────────────────────────────────────────┘
つまり、「正常に動く最小のEXEファイルの先頭 512 バイト（0x200 バイト）」をそのまま保存したものが header_template.bin になります。

2. 具体的な作成手順（3パターン）
お好みの環境やツールに合わせて作成してください。

パターンA：NASM ＋ バイナリエディタを使う（直感的）
一番仕組みが分かりやすい方法です。

ベースとなるアセンブリ（base.asm）を用意

コード スニペット
global _main
extern _ExitProcess@4

section .text
_main:
    push 0
    call _ExitProcess@4
NASMとGoLink（またはGCC）で最小EXEを作る

Bash
nasm -f win32 base.asm -o base.obj
golink /console base.obj kernel32.dll
# -> base.exe が生成される
バイナリエディタ（Stirling や Stirling-GUI、xxd など）で base.exe を開く

アドレス 0x00000000 から 0x000001FF までの512バイトを選択・コピーする

新規ファイルに貼り付けて header_template.bin として保存する

パターンB：PowerShell コマンドで作る（Windows標準・高速）
バイナリエディタを使わず、Windows標準の PowerShell だけで一発で切り出すコマンドです。

上記の手順2で base.exe を作成した後、PowerShell で以下のコマンドを実行します。

PowerShell
# base.exe の先頭512バイトを抽出して header_template.bin に保存する
$bytes = [System.IO.File]::ReadAllBytes("base.exe")
[System.IO.File]::WriteAllBytes("header_template.bin", $bytes[0..511])
パターンC：ActiveBasic / Pascal コードで作る
将来的にリンカーを自作する言語（ActiveBasicなど）を使って切り出しツールを作る方法です。

Basic
' base.exe から先頭 512 バイトを切り出して header_template.bin を作成する
Dim hIn As Long, hOut As Long
Dim buf(511) As Byte

hIn = FileOpen("base.exe", "r")
If hIn <> 0 Then
    FileRead(hIn, VarPtr(buf(0)), 512)
    FileClose(hIn)
    
    hOut = FileOpen("header_template.bin", "w")
    If hOut <> 0 Then
        FileWrite(hOut, VarPtr(buf(0)), 512)
        FileClose(hOut)
        Print "header_template.bin の作成に成功しました (512 bytes)"
    End If
End If
3. 作成したテンプレートが正しいか確認する方法
バイナリエディタで header_template.bin を開いたとき、以下の特徴を持っていれば成功です。

先頭 2 バイト が ASCII 文字の MZ（4D 5A）になっている（DOSヘッダーの識別記号）。

0x00000080 〜 0x00000100 付近 に ASCII 文字の PE（50 45 00 00）がある（PEヘッダーの識別記号）。

ファイルサイズ がぴったり 512 バイト（または 0x1000 を採用した場合は 4096 バイト）になっている。

4. 自作リンカーでの合体方法
このテンプレートを用意できたら、自作リンカーが行う処理は以下のように非常にシンプルになります。

Basic
' 自作リンカーの出力処理
Sub OutputEXE(objMachineCode() As Byte, codeSize As Long)
    Dim hExe As Long
    Dim headerBuf(511) As Byte
    Dim hHeader As Long
    
    ' 1. テンプレートヘッダーを読み込む
    hHeader = FileOpen("header_template.bin", "r")
    FileRead(hHeader, VarPtr(headerBuf(0)), 512)
    FileClose(hHeader)
    
    ' 2. output.exe に書き出す
    hExe = FileOpen("output.exe", "w")
    
    ' (a) テンプレートヘッダーを書く (0x0000 - 0x01FF)
    FileWrite(hExe, VarPtr(headerBuf(0)), 512)
    
    ' (b) マシン語を書く (0x0200 - )
    FileWrite(hExe, VarPtr(objMachineCode(0)), codeSize)
    
    FileClose(hExe)
    Print "output.exe の生成が完了しました！"
End Sub
💡 ワンポイントアドバイス
テンプレートの .text セクションのアドレス設定（RVA 0x1000 や VirtualSize など）と、自作コードの読み込みアドレスが一致していれば、これで生成した output.exe がそのまま Windows 上で起動します！

3. PEヘッダーの自前ビルドとリロケーションについて詳しく

テンプレート方式で「バイナリが動く感覚」をつかんだ後に挑む本丸、「PEヘッダーの自前ビルド」と「リロケーション」の完全自作について詳しく解説します。

この2つを実装することで、外部のバイナリ（型紙）に一切頼らず、「生のバイナリデータからWindowsで動くEXEを1から生み出す」ことができるようになります。

1. PEヘッダーの自前ビルド
PE（Portable Executable）ヘッダーの組み立てとは、WindowsのOS（ローダー）に「このプログラムをどうメモリに読み込んで実行するか」を伝えるための構造体データをメモリ上で1バイトずつ正しく構築する作業です。

自作リンカーが自前で出力すべきヘッダー群の全体構造と、各構造体に必要な値は以下の通りです。

┌──────────────────────────────────────────┐
│ 1. IMAGE_DOS_HEADER                      │ (64 bytes)
├─────────────────────────────────────────┤
│ 2. DOS Stub                              │ (64 bytes: 昔の名残メッセージ)
├─────────────────────────────────────────┤
│ 3. PE Signature ("PE\0\0")               │ (4 bytes)
├─────────────────────────────────────────┤
│ 4. IMAGE_FILE_HEADER (COFF Header)       │ (20 bytes)
├─────────────────────────────────────────┤
│ 5. IMAGE_OPTIONAL_HEADER32               │ (224 bytes) ★最重要
├─────────────────────────────────────────┤
│ 6. IMAGE_SECTION_HEADER (.text)          │ (40 bytes)
├─────────────────────────────────────────┤
│ [ パディング (0埋め) ]                   │ (FileAlignment 512バイトまで揃える)
└──────────────────────────────────────────┘ ── (ここまでが RVA 0x1000 / Offset 0x0200)
主要な構造体の設定例 (x86 32bit用)
ActiveBasicなどの Type 構文で定義し、数値を直接セットしていきます。

① IMAGE_DOS_HEADER & DOS Stub
Windowsが最初にチェックするシグネチャです。

e_magic: 0x5A4D ("MZ")

e_lfanew: DOSヘッダーの直後に置く PE Signature へのオフセット値（例: 0x80 = 128バイト）

② IMAGE_FILE_HEADER (COFFヘッダー)
Machine: 0x014C (Intel 386 / x86)

NumberOfSections: 1 (.text セクションのみの場合)

SizeOfOptionalHeader: 224 (32bit PEの標準サイズ)

Characteristics: 0x010F (32bit executable, 32bit word machine など)

③ IMAGE_OPTIONAL_HEADER32 (最も設定項目が多い心臓部)
Basic
Type IMAGE_OPTIONAL_HEADER32
    Magic                       As Word   ' 0x010B (32bit PE)
    MajorLinkerVersion          As Byte   ' 1
    MinorLinkerVersion          As Byte   ' 0
    SizeOfCode                  As DWord  ' .text セクションのファイルサイズ
    SizeOfInitializedData       As DWord  ' 0
    SizeOfUninitializedData     As DWord  ' 0
    AddressOfEntryPoint         As DWord  ' 0x00001000 ★実行開始位置 (RVA)
    BaseOfCode                  As DWord  ' 0x00001000
    BaseOfData                  As DWord  ' 0x00002000 (無ければ0)
    ImageBase                   As DWord  ' 0x00400000 ★メモリ配置の基準アドレス
    SectionAlignment            As DWord  ' 0x1000 (4096バイト: メモリ上のアライメント)
    FileAlignment               As DWord  ' 0x0200 (512バイト: ファイル上のアライメント)
    MajorOperatingSystemVersion As Word   ' 4
    MinorOperatingSystemVersion As Word   ' 0
    MajorImageVersion           As Word   ' 0
    MinorImageVersion           As Word   ' 0
    MajorSubsystemVersion       As Word   ' 4
    MinorSubsystemVersion       As Word   ' 0
    Win32VersionValue           As DWord  ' 0
    SizeOfImage                 As DWord  ' 0x00002000 (ヘッダー+セクションの全メモリサイズ)
    SizeOfHeaders               As DWord  ' 0x00000200 (全ヘッダーのファイルサイズ)
    CheckSum                    As DWord  ' 0
    Subsystem                   As Word   ' 3 (Console) または 2 (GUI)
    DllCharacteristics          As Word   ' 0
    SizeOfStackReserve          As DWord  ' 0x00100000 (1MB)
    SizeOfStackCommit           As DWord  ' 0x00001000 (4KB)
    SizeOfHeapReserve           As DWord  ' 0x00100000 (1MB)
    SizeOfHeapCommit            As DWord  ' 0x00001000 (4KB)
    LoaderFlags                 As DWord  ' 0
    NumberOfRvaAndSizes         As DWord  ' 16 (DataDirectoryの要素数)
End Type
④ IMAGE_SECTION_HEADER (.text)
マシン語を置くセクションの情報を定義します。

Name: ".text\0\0\0" (8バイト)

VirtualSize: .text の実際のサイズ

VirtualAddress: 0x00001000 (メモリ上の開始位置)

SizeOfRawData: ファイルアライメント（512）の倍数に切り上げたサイズ

PointerToRawData: 0x00000200 (ファイル上の書き込み開始位置)

Characteristics: 0x60000020 (Executable, Readable, Contains Code)

2. アドレス解決と「リロケーション」の実装
PEヘッダーが組み立てられたら、次に行うのが「リロケーション（アドレスの補正）」です。

なぜリロケーションが必要か？
アセンブラが出力した .obj ファイル内のマシン語は、命令のアドレス部分がダミー値（00 00 00 00）になっています。

リンカーは、.obj に含まれている「リロケーションテーブル」を元に、最終的に決定したメモリ配置アドレス（ImageBase + RVA）を使って命令内のアドレスを計算・書き換えます。

リロケーションの2大タイプ
x86 (32bit) アセンブリで使われる主な補正タイプは以下の2つです。

補正タイプ (Type)	主な対象命令	計算式 (書き換える4バイトの値)
IMAGE_REL_I386_REL32 (相対補正)	call, jmp	目的地の絶対アドレス - (書き換え位置の絶対アドレス + 4)
IMAGE_REL_I386_DIR32 (絶対補正)	mov eax, [変数] など	目的地の絶対アドレス そのもの
リロケーション計算の具体例
例えば、アセンブラが出力した以下のようなコードがあるとします。

コード スニペット
_main:
    call _ExitProcess   ; 機械語: E8 00 00 00 00  (offset 0x0001 の場所から4バイトが未定)
リンカーが決定したアドレス情報:

ImageBase = 0x00400000

.text の RVA = 0x00001000

_ExitProcess の絶対アドレス（仮にIAT上の位置） = 0x00402000

書き換え対象の位置（patchAddr）の計算:

書き換え場所の絶対アドレス = ImageBase (0x00400000) + .text RVA (0x1000) + オフセット (0x0001) = 0x00401001

REL32（相対アドレス）の補正計算:

relativeOffset=0x00402000−(0x00401001+4)=0x00402000−0x00401005=0x00000FFB
バイナリの書き換え:

機械語の E8 00 00 00 00 を E8 FB 0F 00 00 （リトルエンディアン表現）に上書きします。

3. リロケーション処理のコード例（アルゴリズム）
ActiveBasicで書く場合のリロケーション適用ループのイメージです。

Basic
' objBuffer: .objファイル全体
' codeBuffer: .textセクションのマシン語バッファ
' pReloc: .obj内のリロケーションテーブルのポインタ
' numRelocs: リロケーションの件数

Sub ApplyRelocations(codeBuffer() As Byte, relocs() As COFF_RELOCATION, numRelocs As Long, symbols() As COFF_SYMBOL)
    Dim i As Long
    Dim patchOffset As DWord
    Dim targetSymbolIndex As DWord
    Dim targetAddr As DWord
    Dim patchAddr As DWord
    Dim relativeOffset As Long
    
    For i = 0 To numRelocs - 1
        ' 1. .text セクション内の書き換えオフセットを取得
        patchOffset = relocs(i).VirtualAddress
        
        ' 2. 参照先シンボルのインデックスから最終アドレスを決定
        targetSymbolIndex = relocs(i).SymbolTableIndex
        targetAddr = GetSymbolAddress(symbols(targetSymbolIndex))
        
        ' 3. 書き換え位置の実際の絶対アドレス (ImageBase + .text_RVA + patchOffset)
        patchAddr = IMAGE_BASE + 0x00001000 + patchOffset
        
        ' 4. リロケーションタイプに応じた補正
        Select Case relocs(i).Type
            Case IMAGE_REL_I386_REL32
                ' 相対アドレス計算: 目的地 - (現在位置 + 4)
                relativeOffset = targetAddr - (patchAddr + 4)
                
                ' codeBuffer の patchOffset 位置から 4バイト上書き
                MemoryCopy(VarPtr(codeBuffer(patchOffset)), VarPtr(relativeOffset), 4)
                
            Case IMAGE_REL_I386_DIR32
                ' 絶対アドレス計算: 目的地の絶対アドレスを直接書き込み
                MemoryCopy(VarPtr(codeBuffer(patchOffset)), VarPtr(targetAddr), 4)
        End Select
    Next i
End Sub
自前ビルド成功へのチェックリスト
PEヘッダーを自前で組み上げ、リロケーションを適用して出力した output.exe が動かない場合、ほぼ100%以下のいずれかが原因です。

アライメント計算ミス:

SizeOfHeaders や SizeOfRawData が FileAlignment (0x200 = 512) の倍数になっていない。

SizeOfImage や VirtualAddress が SectionAlignment (0x1000 = 4096) の倍数になっていない。

AddressOfEntryPoint のミス:

絶対アドレス (0x00401000) ではなく、RVA (0x00001000) をセットしているか。

patchAddr + 4 の引き忘れ:

相対アドレス計算時に call 命令自体の長さを引くのを忘れている。

この「PEヘッダーの完全自作」と「リロケーション」をクリアした瞬間、バイナリのブラックボックスは完全に解消され、自作リンカーの主要エンジンが完成します！

4. IAT (.idata) の自動生成

自作リンカー開発の「最大の難所」であり、同時に「Windows上でGUIやCUI、Win32 APIを自在に呼び出せるようになる最後のピース」が IAT（Import Address Table / インポートアドレステーブル） の自動生成です。

これを実装すると、MessageBoxA や ExitProcess などの Windows API を自作 EXE から自由に呼び出せるようになります。

1. IAT（.idata セクション）とは何か？
Windowsでは、DLL（kernel32.dll や user32.dll など）に入っている関数は、プログラムが実行されるたびにメモリ上の異なるアドレスにロードされる可能性があります。

そのため、リンカーは「APIの直呼び出し」を埋め込むのではなく、「Windows OS（ローダー）に API のアドレスを書き込んでもらうための予約領域（名簿）」を .exe の中に作っておく必要があります。

この「予約領域と名簿」のセットが .idata セクション です。

[ あなたのコード (.text) ]
       │
       ▼  1. call [0x00402000] (IATのアドレスを間接呼び出し)
┌─────────────────────────────────────────┐
│ [ IAT (Import Address Table) ]          │
│  0x00402000: 0x77E61234 (本物のAPI位置) │ ◀─ 2. OS起動時に書き換えられる！
└─────────────────────────────────────────┘
       │
       ▼  3. Windows DLL 内の関数実行 (ExitProcess など)
2. .idata セクション内部の4大データ構造
.idata セクションを作るには、以下の 4つのテーブル（配列） をメモリ上に隙間なく並べてバイナリ化します。

.idata セクションの内部構造
┌─────────────────────────────────────────┐
│ 1. Import Directory Table (IDT)         │ ── DLLごとのヘッダー構造体
├─────────────────────────────────────────┤
│ 2. Import Lookup Table (ILT)            │ ── 関数名ポインタのリスト
├─────────────────────────────────────────┤
│ 3. Import Address Table (IAT)           │ ── OSが本物のアドレスを書き込む場所
├─────────────────────────────────────────┤
│ 4. Hint/Name Table & DLL Name Strings   │ ── "ExitProcess" や "kernel32.dll" の文字列データ
└─────────────────────────────────────────┘
① Import Directory Table (IDT / IMAGE_IMPORT_DESCRIPTOR)
呼び出す DLL（例: kernel32.dll）1つにつき1つの構造体（20バイト）を作成し、最後に「全要素ゼロの終端構造体」を置きます。

Basic
Type IMAGE_IMPORT_DESCRIPTOR
    OriginalFirstThunk As DWord  ' ILT への RVA
    TimeDateStamp      As DWord  ' 0 でOK
    ForwarderChain     As DWord  ' 0 でOK
    Name               As DWord  ' DLL名文字列 ("kernel32.dll") への RVA
    FirstThunk         As DWord  ' IAT への RVA ★重要
End Type
② Import Lookup Table (ILT) & Import Address Table (IAT)
どちらも「4バイトのポインタの配列」です。初期状態では、両方とも後述する Hint/Name Table への RVA を指しておきます。
（OSが起動すると、IAT 側の値だけが 0x77E61234 のような「実際のAPIアドレス」に自動上書きされます）。

③ Hint/Name Table & DLL Name Strings
関数の名前とDLLの名前をバイナリとして置く領域です。

Hint/Name: 2バイトのHint(0でOK) ＋ ASCII関数名 (例: "ExitProcess\0")

DLL Name: ASCII DLL名 (例: "kernel32.dll\0")

3. 自動生成のアルゴリズム（具体例）
例として、kernel32.dll の ExitProcess だけを使う場合の .idata バイナリ組み立て手順を追ってみましょう。

.idata セクションの配置基準（RVA）を 0x00002000 と仮定します。

[オフセット]  [RVA]       [内容]
+0x0000     0x00002000  ── 【1. IDT (20バイト×2)】
                        ・IDT[0]: OriginalFirstThunk = 0x2028 (ILTのRVA)
                                  Name               = 0x2038 (DLL名のRVA)
                                  FirstThunk          = 0x2030 (IATのRVA)
                        ・IDT[1]: ゼロ埋め (20バイト)

+0x0028     0x00002028  ── 【2. ILT (4バイト×2)】
                        ・ILT[0] = 0x2048 (Hint/NameのRVA)
                        ・ILT[1] = 0x00000000 (終端)

+0x0030     0x00002030  ── 【3. IAT (4バイト×2)】
                        ・IAT[0] = 0x2048 (ILTと同じHint/NameのRVAをセット)
                        ・IAT[1] = 0x00000000 (終端)

+0x0038     0x00002038  ── 【4. DLL Name】
                        ・"kernel32.dll\0" (文字列)

+0x0048     0x00002048  ── 【5. Hint/Name】
                        ・Word: 0x0000 (Hint)
                        ・String: "ExitProcess\0"
4. コード呼び出し側（.text）の書き換え
.idata セクションを作ったら、自作コード（.text）から API を呼ぶ命令を書き換えます。

APIを呼ぶとき、アセンブリでは間接呼び出し (call [メモリ]) を使います。

コード スニペット
; アセンブラ側で書いたコード
call _ExitProcess

; マシン語 (リロケーション補正前)
FF 15 00 00 00 00   ; call dword ptr [0x00000000]
リンカーはリロケーション処理時に、00 00 00 00 の部分を IAT[0] の絶対アドレス（ImageBase + IAT_RVA） に書き換えます。

書き換え後のアドレス=ImageBase (0x00400000)+IAT_RVA (0x00002030)=0x00402030
結果として、マシン語は FF 15 30 20 40 00 となり、実行時に OS が IAT[0] に書き込んだ本物の ExitProcess アドレスへとジャンプできるようになります！

5. PEヘッダー（DataDirectory）への登録
最後に忘れてはならないのが、PEヘッダーに .idata の位置を教えてあげることです。

IMAGE_OPTIONAL_HEADER32 構造体の末尾にある DataDirectory 配列の 2番目の要素（Index 1） に、IDT の RVA とサイズを登録します。

Basic
' PE Optional Header の DataDirectory をセット
peHeader.DataDirectory(1).VirtualAddress = 0x00002000  ' IDT の RVA
peHeader.DataDirectory(1).Size           = 40          ' IDT のサイズ (20バイト × 2)
これを怠ると、Windows は .idata セクションが存在することに気づかず、起動時にエラーを出してクラッシュします。

6. 自作リンカー構築の全体まとめ
ここまで来れば、自作リンカーの全パーツが揃いました！

[ .obj ファイル群 ]
       │
       ▼
 1. COFF解析              │ マシン語(.text) とシンボル、API参照名を抽出
       │
       ▼
 2. .idata 自動構築       │ 必要とする DLL / 関数名から IAT・IDT テーブルをバイナリ生成
       │
       ▼
 3. メモリレイアウト決定 │ .text (RVA 0x1000)、.idata (RVA 0x2000) などの配置決定
       │
       ▼
 4. リロケーション補正   │ _ExitProcess 等の call 命令を IAT の絶対アドレス(0x00402030)に補正
       │
       ▼
 5. PEヘッダー自前ビルド  │ DataDirectory[1] に .idata 情報をセットして .exe 保存！
最初は kernel32.dll の ExitProcess 単体だけでテストし、動いたら user32.dll の MessageBoxA を追加してみる、という順序で進めるのが確実です。

自作コードから自分のリンカーで生成した MessageBoxA のウィンドウがパッと画面に現れた瞬間は、間違いなく一生モノの感動になりますよ！

3のバージョンはexe作成したときに動くものができるか？

なぜ動けるか

結論から言うと、「3（PEヘッダーの自前ビルドとリロケーション）」の段階だけでも、条件を満たせば「Windows上で実際に起動して正常終了（または無限ループ）するEXE」は完璧に動きます！

ただし、「Win32 API（MessageBoxAやExitProcessなどの外部DLL）を呼び出すコード」を書いた場合は、まだ「4（.idataの構築）」をしていないため動きません。

なぜ3の段階で動くものができるのか、その仕組みと「動く理由」を分かりやすく解説します。

1. なぜ API を呼ばなくても EXE は「動く」のか？
Windows の OS（PEローダー）が .exe を実行するときに最低限チェックしているのは、「Windows APIが使えるか」ではなく「PEヘッダーのフォーマットが正しく、メモリにマシン語を広げられるか」 だけだからです。

OSがプログラムを起動する手順は以下の通りです。

[ あなたが作った output.exe ]
       │
       ▼  ① OSがファイルを読み込み、PEヘッダーを検証
 [ DOS/PE Header OK! ]
       │
       ▼  ② .text セクションの領域（メモリ 0x00401000〜）を確保し、マシン語をコピー
 [ メモリ展開完了 ]
       │
       ▼  ③ AddressOfEntryPoint (例: 0x00401000) に CPU の実行権限を渡す
 [ CPUがマシン語を実行開始！ ]
つまり、OSから見れば「指定されたメモリ位置にマシン語を置いて、エントリポイントへジャンプさせるだけ」なので、APIを使わない純粋な CPU 命令（x86マシン語）であれば、3の段階で作ったEXEでも全く問題なく動作します。

2. 3の段階で「100%動く」最小のアセンブリコード例
外部DLLの API（ExitProcess等）に頼らず、CPU命令だけで完結するコードを書けば、3で作ったリンカーで完全に動作する .exe が作れます。

例①：無限ループするだけのコード（x86）
コード スニペット
section .text
global _main

_main:
    jmp $       ; 自分自身の位置にジャンプし続ける (無限ループ)
マシン語: EB FE （たった2バイト！）

動作: 実行するとウィンドウや画面出力は何もありませんが、タスクマネージャーを見るとプロセスが起動し、CPUを1コア消費して走り続けます（強制終了で止める）。

動く理由: 外部のDLLやOSの関数を1つも呼んでおらず、CPUのレジスタと命令だけで完結しているため。

例②：インラインアセンブラで直接システムコール（Win32例外/ret）で終わるコード
コード スニペット
section .text
global _main

_main:
    xor eax, eax    ; eax = 0 (戻り値)
    ret             ; 呼び出し元（OS）へ復帰
マシン語: 31 C0 C3 （3バイト）

動作: 一瞬で起動して、何も表示せずに正常終了します。

3. 「3の段階」と「4の段階」の決定的な違い
なぜ3だけでも動くのに「4（.idataの自動生成）」が必要になるのか、その境界線は以下の通りです。

項目	3 の段階（PEヘッダー＋リロケーション）	4 の段階（＋.idata / IAT）
できること	CPUの純粋な計算（加算・引き算・ループ・メモリ操作など）	画面への文字出力、ウィンドウ表示、ファイル読み書き、API終了
外部依存	なし（CPU命令のみ）	あり（kernel32.dll や user32.dll）
起動できるか	できる！（OSがメモリに読み込んで実行してくれる）	できる！（Windowsの機能も使い放題）
4. 3で「動くバイナリ」ができることの技術的な価値
実は、コンパイラ開発の歴史において「3の段階（外部APIなしで自力起動するバイナリ）」を成功させることが、最も大きなブレイクスルーです。

PEフォーマットの完全理解: DOSヘッダー、PEヘッダー、セクションアライメントの計算が1バイトのズレもなく完璧に合致している証拠です。

CPUとOSの境界の突破: 自分の書いたバイナリが、Windowsという巨大なOSに「正式な実行ファイル」と認められた瞬間です。

この「3」が完成してしまえば、「4」は単に.idataというデータ構造体（名簿）を末尾に付け足す作業に過ぎません。

ですので、「3の自前ビルド」で作った無音のEXE（無限ループや速攻終了するEXE）がタスクマネージャーに現れたときこそ、自作ツールチェーンが完成に大きく近づいた最初の「感動の瞬間」になります！