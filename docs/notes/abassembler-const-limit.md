# abassembler: `too many Const`

Cursor チャットからの記録（2026-07-27）。`abassembler` 結合時に abc が定数上限で失敗した件。

## 症状

```text
abpc: .\abassembler_combined.abp -> ./out/abassembler.exe
>> ...\abc.exe .\abassembler_combined.abp .\abassembler_combined.asm
loaded bytes=79030
too many Const
abc fail: .\abassembler_combined.asm
```

## 原因

`Const` の上限が `MAX_VARS`（128）に紐づいていた。  
実使用は Const 132 + 組み込み約 10 で、上限 128 を超過。

## 対処

Const 専用の上限を分離して引き上げ、関連箇所を修正したうえで `abc` を再ビルドし、`abassembler` を通す。
