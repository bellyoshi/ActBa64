# AB4 のコードを ActBa64 へ移すときの直し方

ActiveBasic 4.20 / 4.24 では動いていても（あるいは動いているように見えても）、ActBa64 では壊れる書き方と、その直し方です。違いの一覧は [different.md](./different.md)、言語の仕様は [language.md](./language.md) にあります。

例には、Arduino 経由でスーパーファミコンのカートリッジを吸い出すツール（RGBA_CRT 氏の HongKongArduinoClone）にある書き方を使います。

| 書き方 | ActBa64 で起きること | 直し方 |
|---|---|---|
| 宣言だけの `Virtual` の vtable を自分で埋める | vtable が無い（NULL）ので書き込んだ時点で落ちる。埋めても引数が 1 つずれる | [中身のある `Virtual` と `Override`](#1-vtable-を自分で埋めるコード--virtual-と-override) |
| 引数の数が関数ポインタの型と合わないコールバック | `-actba32` でスタックの片付けがずれる。余分な引数にはごみが入る | [`cdecl` と、引数の数を合わせる](#2-引数の数が合わないコールバック--cdecl) |

---

## 1. vtable を自分で埋めるコード → `Virtual` と `Override`

### AB4 の書き方

AB4.24 の Class には、中身のある `Virtual` も `Override` もありません。`Virtual Sub Init(...)` の後ろに `End Sub` を書くとエラーになり、子で同じ名前の `Sub` を書いても基底のポインタからは呼ばれません（空の vtable を呼んで落ちます）。そのため AB4 では、次のように「宣言だけの `Virtual` を持つ基底」の vtable へ、子のメソッドのアドレスを自分で書き込んでいました。

```basic
Class ProgressCallback
Public
    virtual Sub Init(Max AS DWord)
    virtual Sub Step(step AS Long, snesReadAdr As DWord)
    virtual Sub Final()
End Class

Type ProgressCallback_Vtable
    Init As VoidPtr
    Step As VoidPtr
    Final As VoidPtr
End Type

Class DumpRomProgressCallBack
    Inherits ProgressCallback
Public
    ' AB4 の COM 風の呼び出しは This を ECX とスタックの両方へ渡すので、スタックの方を受ける捨て引数
    Sub Init(_this As VoidPtr, Max AS DWord)
        ...
    End Sub
    Sub Step(_this As VoidPtr, step AS Long, snesReadAdr As DWord)
        ...
    End Sub
    Sub Final(_this As VoidPtr)
        ...
    End Sub
End Class

Function new_DumpRomProgressCallBack() As *DumpRomProgressCallBack
    Dim ret As *DumpRomProgressCallBack, vtable As *ProgressCallback_Vtable
    ret = new DumpRomProgressCallBack
    vtable = GetDWord(ret) As VoidPtr           ' オブジェクトの先頭の vtable
    vtable->Init  = AddressOf(ret->Init)
    vtable->Step  = AddressOf(ret->Step)
    vtable->Final = AddressOf(ret->Final)
    new_DumpRomProgressCallBack = ret
End Function
```

### ActBa64 で起きること

- ActBa64 では、vtable をプログラムが書き換えることを想定していません。宣言だけの `Virtual` の Class は COM インターフェースとして扱い、それを継承した Class の先頭（`__vptr`）は NULL のままです。`vtable->Init = ...` はアドレス 0 への書き込みになり、そこで落ちます。
- `This` はメソッドの第 1 引数で 1 回だけ渡します（[different.md](./different.md) の「メソッドの `This` の渡し方」）。vtable を自分で用意して埋めても、`_this` に `Max` の値が入り、`Max` にはごみが入ります。

### 直し方

1. 基底の `Virtual` に中身を書く（何もしないなら空でよい。`Function` は既定の戻り値を入れる）
2. 子のメソッドに `Override` を付け、捨て引数 `_this` を消す
3. vtable の `Type` と、vtable を埋める `new_...` 関数を消す。作るのは `New`、消すのは `Delete` だけにする

```basic
Class ProgressCallback
Public
    Virtual Sub Init(Max As DWord)
    End Sub
    Virtual Function isCancel() As BOOL
        isCancel = FALSE
    End Function
    Virtual Sub Step(stepN As Long, snesReadAdr As DWord)
    End Sub
    Virtual Sub Final()
    End Sub
End Class

Class DumpRomProgressCallBack
    Inherits ProgressCallback
Public
    Override Sub Init(Max As DWord)
        ...
    End Sub
    Override Sub Step(stepN As Long, snesReadAdr As DWord)
        ...
    End Sub
    Override Sub Final()
        ...
    End Sub
End Class

Dim pc As *DumpRomProgressCallBack
pc = New DumpRomProgressCallBack
DumpRom2(hCOM, rom, size, VarPtr(mmap), pc)     ' 仮引数は progress As *ProgressCallback のまま
Delete pc
```

- 基底のポインタ（`progress As *ProgressCallback`）から呼んでも、子の `Override` へ行きます。基底の ctor の中から呼んでも同じです（[language.md §3.3](./language.md#33-class)）。
- 子に同じ名前の `Sub` を `Override` 無しで書くと、コンパイルエラーになります。`Override` の付け忘れに気づけます。
- 引数の名前がフィールドやメソッドと大小違いで同じにならないようにしてください（`step` と `Step` は同じ名前です）。上の例では仮引数を `stepN` にしています。
- 回帰テスト: `src/actba64/test/t_class_override_cb.abp`

### AB4 と ActBa64 の両方でビルドしたいとき

この書き方は AB4.24 では通りません。両方で使うソースは、`_ACTBA64`（ActBa64 だけが定義する）で分けます。

```basic
#ifdef _ACTBA64
Class ProgressCallback
    ...                ' 中身のある Virtual
End Class
#else
Class ProgressCallback
    ...                ' AB4 の宣言だけの virtual と vtable を埋める関数
End Class
#endif
```

---

## 2. 引数の数が合わないコールバック → `cdecl`

### AB4 の書き方

関数ポインタの型より引数の多い関数を入れて呼ぶ書き方です。

```basic
Typedef SfcMmcInitFunc = *Function(hCOM AS HANDLE) As BOOL
Typedef SfcMmcExitFunc = *Function(hCOM AS HANDLE, romBuffer As BytePtr)

Function SDD1_init(hSerial AS HANDLE, info As *SFC_CART_INFO) As BOOL    ' 型より 1 つ多い
    ...
End Function

Function SA1_SRAM_WRITE_exit(hCOM AS HANDLE, info As *SFC_CART_INFO, romBuffer As BytePtr)
    SA1_SramExit(hCOM, romBuffer)       ' romBuffer は 3 番目。呼ぶ側は 2 つしか渡さない
End Function

model->rom.init_cb = AddressOf(SDD1_init)
model->rom.init_cb(hSerial)             ' 引数 1 つで呼ぶ
```

### ActBa64 で起きること

- `-actba32` の既定の呼び方は stdcall で、呼ばれた側が自分の引数の分（ここでは 8 バイト）だけスタックを戻します。呼んだ側は 4 バイトしか積んでいないので、ずれます。
- 型に無い引数（`info` や 3 番目の `romBuffer`）には、スタックにたまたまあった値が入ります。`romBuffer[0]` を読むと落ちることがあります。

### 直し方

**まず、引数の数を型と合わせてください。** ごみの入る引数を使っているなら、それは移植と関係のないバグです。上の例なら `SA1_SRAM_WRITE_exit(hCOM, romBuffer)` にし、使っていない `info` は消します。

引数の数を合わせられないとき（C のライブラリへ渡すコールバックなど）は、手続きと型に `cdecl` を書きます。

```basic
Typedef SfcMmcInitFunc = *Function cdecl(hCOM AS HANDLE) As BOOL

Function SDD1_init cdecl(hSerial AS HANDLE, info As *SFC_CART_INFO) As BOOL
    ...
End Function
```

| 書く場所 | 意味（`-actba32`） |
|---|---|
| `Function 名前 cdecl(...)` / `Sub 名前 cdecl(...)` | 呼ばれた側は引数を片付けずに `ret` で戻り、呼んだ側が片付ける。直接呼んでも `AddressOf` で渡しても同じ |
| `*Function cdecl(...)` / `*Sub cdecl(...)`（`Typedef` / `Dim`） | 関数ポインタの型の印。どの関数ポインタの呼び出しも、呼んだ後に `esp` を呼ぶ前の位置へ戻すので、stdcall の関数も cdecl の関数も呼べる |
| `stdcall` | 書いても書かなくても同じ（既定） |

- 64bit では cdecl と stdcall は同じ呼び方なので、書いても変わりません。
- C ランタイムの `qsort` のように、C の関数へ渡す比較関数は `cdecl` にします（`Declare Sub qsort cdecl Lib "msvcrt.dll" ...`、比較関数は `Function CmpLong cdecl(a As *Long, b As *Long) As Long`）。
- `cdecl` を付けても、余分な引数の中身はごみのままです。片付けのずれが無くなるだけです。
- AB4.24 には手続きの `cdecl` も関数ポインタの `cdecl` もありません（コンパイルエラー）。両方でビルドするなら [§1](#ab4-と-actba64-の両方でビルドしたいとき) と同じく `#ifdef _ACTBA64` で分けます。
- 回帰テスト: `src/actba64/test/t_cdecl_func.abp`

