とても簡単なコンパイラーをつくる。

abpファイル

MessageBox(NULL, "HelloWorld", "", MB_OK)



文字列定数は可変。

先ほどのasmのコードにコンパイル

.abp というオリジナル拡張子の独自言語（仮に ABP と呼びましょう！）から、先ほどのアセンブリ言語（NASM形式）を出力する超シンプル・コンパイラですね！

MessageBox(NULL, "HelloWorld", "", MB_OK) のような高レベルの関数呼び出し構文を読み込み、文字列定数を自動抽出して .data セクションへ配備し、.text セクションへ push や call を展開する処理を実装します。

1. コンパイラが行う変換の全体イメージ
コンパイラは入力ファイルを1行ずつ読み、以下のように構文を展開します。

[ 入力: main.abp ]
  MessageBox(NULL, "HelloWorld", "", MB_OK)
       │
       ▼ コンパイラ（字句解析・データ抽出・コード生成）
[ 出力: main.asm ]
  section .data
      str_0 db "HelloWorld", 0
      str_1 db "", 0

  section .text
      ...
      push 0           ; MB_OK
      push str_1       ; lpCaption
      push str_0       ; lpText
      push 0           ; NULL
      call _MessageBoxA@16
2. .abp から .asm への変換ルール
コンパイラ内部で適用する変換ルールは以下の3点だけです。

① 文字列定数の自動ナンバリング
コード中に "..." が登場したら、.data セクションに str_0, str_1 というラベル名で定義を生成します。

"HelloWorld" → str_0 db "HelloWorld", 0

"" → str_1 db "", 0

② 定数（NULL / MB_OK）の置換
Windowsの定数値をアセンブリ用の数値（0）に置き換えます。

NULL → 0

MB_OK → 0

③ 引数の逆順 push （stdcall 呼び出し規約）
MessageBox(hWnd, lpText, lpCaption, uType) の4つの引数を解析し、右から左（第4引数 → 第1引数）の順番で push を出力します。

3. コンパイラの処理アルゴリズム（擬似コード）
コンパイラの基本骨格（文字列処理とコード生成）の実装手順です。

Python
# コンパイラの基本処理フロー

# 1. 出力バッファの準備
data_section = ["section .data"]
text_section = [
    "bits 32",
    "extern _MessageBoxA@16",
    "extern _ExitProcess@4",
    "section .text",
    "global _main",
    "_main:"
]

string_count = 0

# 2. .abp ファイルを1行ずつパース
for line in abp_file:
    line = line.strip()
    
    # MessageBox 関数の呼び出しを検出
    if line.startswith("MessageBox("):
        # カッコ内の引数テキストを取り出す -> 'NULL, "HelloWorld", "", MB_OK'
        args_text = line[line.find("(")+1 : line.rfind(")")]
        args = parse_csv_args(args_text) # 引数を4つに分割
        
        # 各引数をアセンブリ用トークンに変換
        asm_args = []
        for arg in args:
            arg = arg.strip()
            if arg.startswith('"'):
                # 文字列定数の場合：.data に登録してラベル化
                label_name = f"str_{string_count}"
                data_section.append(f"    {label_name} db {arg}, 0")
                asm_args.append(label_name)
                string_count += 1
            elif arg == "NULL" or arg == "MB_OK":
                asm_args.append("0")
            else:
                asm_args.append(arg)
                
        # 3. 引数を逆順（右から左）に push するコードを生成
        for arg in reversed(asm_args):
            text_section.append(f"    push    {arg}")
            
        # 4. API呼び出しコードを追加
        text_section.append("    call    _MessageBoxA@16")

# 5. プログラム終了処理を追加
text_section.append("    push    0")
text_section.append("    call    _ExitProcess@4")

# 6. .data と .text を結合して .asm ファイルへ書き出し
output_asm = "\n".join(data_section) + "\n\n" + "\n".join(text_section)
4. 実際に生成される .asm コード
例えば、.abp ファイルに以下のように書いたとします。

Plaintext
MessageBox(NULL, "Hello ABP World!", "My App", MB_OK)
これを自作コンパイラに通すと、以下のNASMコードが全自動で吐き出されます！

コード スニペット
section .data
    str_0 db "Hello ABP World!", 0
    str_1 db "My App", 0

bits 32

extern _MessageBoxA@16
extern _ExitProcess@4

section .text
    global _main

_main:
    push    0               ; MB_OK (第4引数)
    push    str_1           ; "My App" (第3引数)
    push    str_0           ; "Hello ABP World!" (第2引数)
    push    0               ; NULL (第1引数)
    call    _MessageBoxA@16

    push    0               ; ExitCode
    call    _ExitProcess@4
開発の流れ（ビルドパイプラインの完成！）
これでついに、高言語から実行ファイルまでの完全な自作パイプラインの全貌がつながりました！

1
1. .abp → .asm 変換
コンパイラ（自作）
main.abp を読み込み、構文木を作らずに直接 .asm アセンブリテキストを出力。

2
2. .asm → .obj 変換
アセンブラ（自作）
.asm を1行ずつ読み、マシン語バイナリとCOFFヘッダーを構築して main.obj を出力。

3
3. .obj → .exe 変換
リンカー（自作）
main.obj にPEヘッダーと .idata (Import Table) を付与して main.exe を生成。


最初は文字列の切出しや引数分離（カンマ区切り）を行うだけの簡単な文字列処理スクリプトとしてコンパイラを作り始めるのがおすすめです！