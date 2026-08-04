# Abassembler compilation error
_Exported on 7/27/2026 at 07:56:49 GMT+9 from Cursor (3.13.10)_

---

**User**

./abpc .\abassembler.pj ./out/abassembler.exe
project: .\abassembler.pj
  sources: 6
    abassembler.abp
    Utils.abp
    Common.abp
    FileIO.abp
    StringBuffer.abp
    coff.abp
  output: ./out/abassembler.exe
abpc: .\abassembler_combined.abp -> ./out/abassembler.exe
>> C:\Users\bellm\source\repos\bellyoshi\ActiveBa6\2026\prototype3\abc.exe .\abassembler_combined.abp .\abassembler_combined.asm
loaded bytes=79030
too many Const
abc fail: .\abassembler_combined.asm

---

**Cursor**

`too many Const` で失敗しているので、定数の上限と現状の使用量をコード側から調べます。

原因は Const 上限が `MAX_VARS`(128) に紐づいていることです。使用数と配列の扱いを確認します。

Const が 132 + 組み込み約10で上限128を超えています。Const 専用の上限を上げて、関連箇所を直します。

Const 上限を分離して上げ、`abc` を再ビルドしてから `abassembler` を通します。

