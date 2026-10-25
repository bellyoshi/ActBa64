# 既知の問題（AB 4.20 仕様をそのまま踏襲）

ActBa64 の不具合ではなく、**ActiveBasic 4.20 と同じ挙動**として把握しておく項目。

言語の正本は [language.md](./language.md)。ActiveBasic と結果がずれる点は [different.md](./different.md)。

### 定数 `TRUE` (=1) と関係演算の真 (-1) が一致しない

- **定数** `TRUE` / `FALSE` は **1 / 0**（Win32 慣習・BasicHelp）。
- **関係演算**（`=` など）の**式の値**は、真 **-1**、偽 **0**。
- そのため `(TRUE = TRUE)` は **-1** になるが、`(-1 = TRUE)` は **`-1 = 1` で偽**になり、連鎖比較 `(TRUE = TRUE) = TRUE` は直感とずれる（AB 4.20 も **`False`**）。

```basic
#console
If (TRUE = TRUE) = TRUE Then
    Print "True"
Else
    Print "False"    ' AB 4.20 / ActBa64 ともこちら
End If

If (-1 = -1) = -1 Then
    Print "True"     ' こちらは真
Else
    Print "False"
End If
```

比較結果そのものを扱うときは **`-1` / `0` リテラル**や中間変数を使う。回帰: `test/t_true_chain.abp`。

### 小文字 `true` / `false`

AB 4.20 では **`true` / `false` は識別子として無効**。ActBa64 も **`TRUE` / `FALSE`（大文字）のみ**組み込み。小文字は未定義変数としてエラーになる。

### 識別子の大小区別（AB 4.20 同様）

**定数・変数・Sub/Function・Declare 名・Type/Class 名**は定義どおりの綴りで参照する（`TRUE` ≠ `true`、`Foo` ≠ `foo`）。**言語キーワード**、**組み込みランタイム**（`FillMemory` / `memcpy` / `malloc` 等）だけ大小無視。Win32 API は `api.idx` の Declare 名（および Alias の裸名）と一致させる。
