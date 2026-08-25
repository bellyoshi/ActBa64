# ActiveBasic との相違点

## 対応しないこと

### 行番号

- **行番号非対応**
  - 言語仕様をシンプルに保つため、`10 PRINT ...` のような行番号付き記述には対応しない。
  - 将来的に、エディター側で「行番号 → ラベル」へ自動変換してからコンパイルできるようにする可能性はあるが、言語仕様として行番号を導入する予定はない。

## 改良点

### コマンドラインからのコンパイラ実行

- **CLI ベースのコンパイル**
  - ActiveBasic が主に GUI ベースであるのに対し、本処理系ではコンパイラをコマンドラインから直接実行できる。
  - これにより、AI ツールやスクリプト、CI 環境などからの自動ビルド・自動テストが容易になり、開発速度・開発効率の向上が期待できる。

### 64bit 対応

- **64bit を正式サポート**
  - ActiveBasic ver 4.20 には 64bit 対応機能が存在するものの、バグにより実質的にコンパイル・実行が困難。
  - ActiveBasic ver 5 はリリース候補版のまま開発が停止しており、64bit が正式機能として確立していない。
  - 本処理系では 64bit 環境でのコンパイルおよび実行を前提とした設計とし、64bit 対応を正式にサポートする。



## 今後対応していくもの（現時点では未対応）

### 文字列
ActiveBasic 4.20 
Chr$(0)も有効な文字列。

1 = Len(Chr$(0)) 
現状null文字で終了の文字コード
0 = Len(Chr$(0))

"Hello" + Chr$(0) + "World"
→HELLO\0World

### Ex文字列

### RAD機能
Project Editor の機能拡充

### 関数ポインタ

### 要確認 ByRef

### rcファイルの取り込み

### #strictディレクティブ

### #define

### GoSub Return 
関数の中のReturnとどう折り合いをつけるか。

### Enum

### Let

### SetDouble,SetWord

### TypeDef

### With

### OpenOpen filename$ [For Access] As number
Close [number]
 
### Print # Input #
### Field Get Put
### Input 
Input "文字列", variableに対応していない。
現状 Input variableのみ。
### Write
### Cls
### 要確認Window,DelWindow
### MsgBox
MessageBoxは動く
### Beep
### ChDir
### Exec
### Kill
### MkDir
### Randomize,Rnd()
### CDbl,CInt,CSng
### GetDouble,GetSingle,GetDWord
### StrPtr
### Abs
### 要確認ATn,Tan,Exp,Log,Fix,Int,Sqr
### Sgn
### HIBYTE HIWORD  LOBYTE  LOWORD MAKELONG MAKEWORD
### 要確認Asc Chr$
### Date$
### Hex$
### Inkey$
### Input$(Length)
### 要確認Left$,Len,Oct$,Right$
### Str$
### String$
### Time$
### Val
### ZeroString
### Eof(filenumber)
### Loc,Lof
### calloc,realloc
### AddressOf
### ELM
### RGB
### SizeOf
### InStr
### ハンドル  
### Win32API

### DirectX
当時はDirect9
現在は最新12
簡単なほうで11
### `Include` ライブラリの拡充

- **標準ライブラリの強化**
  - `include` によって利用可能な標準ライブラリを拡充し、ユーティリティ関数や共通モジュールを手軽に再利用できるようにしていく。

### `Class` 宣言

- **オブジェクト指向機能の導入**
  - フェーズ1（メンバ・メソッド・ctor/dtor・`Dim As Class(args)`）は実装済み。詳細は [language.md §3.3](./language.md#33-classフェーズ1)。
  - 今後: `Inherits` / `Virtual` / `New`/`Delete` など。
