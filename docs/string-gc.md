# actba64 の String GC

コンパイラが実行ファイルへ埋め込む **文字列専用のハイブリッド GC** の設計と実装。言語仕様側の要約は [language.md §6](./language.md) を参照。

対象ソース:

| 役割 | ファイル |
|---|---|
| 確保・マーク・掃き出しの本体 | [`src/actba64/StrGcRt.abp`](../src/actba64/StrGcRt.abp) |
| ルート登録・セーフポイント・文字列ランタイム | [`src/actba64/AstLower.abp`](../src/actba64/AstLower.abp) |
| `cmp rcx,rax` / `mov rax, gs:[8]` | [`src/actba64/IR.abp`](../src/actba64/IR.abp) / [`Emiter.abp`](../src/actba64/Emiter.abp) / [`CodeGen.abp`](../src/actba64/CodeGen.abp) |

C ランタイムや別 DLL は使わない。`HeapAlloc` / `HeapFree`（`kernel32`）だけを呼び、マーク表は PE の BSS（グローバル領域の末尾）に置く。

---

## 1. なぜ GC か

ActiveBasic 4.20 互換の `String` は **代入のたびに新しいヒープ塊を指すポインタ** になる。連結・`Mid$`・`Str$` は毎回確保する。参照カウントも、代入時の `StrFree` も行わない。

代入時に旧値をすぐ `HeapFree` すると、別名（同じ塊を指す別変数）や、関数の戻り値をまだ rax に載せる前に潰す事故が起きる。そこで **生きているポインタから到達できる塊だけ残し、残りをまとめて解放** する。

コンパクション（塊の引っ越し）はしない。一度確保したアドレスは、解放されるまで変わらない。`StrPtr` で取った内部ポインタも、親 `String` がマークされていれば有効なまま。

---

## 2. 文字列のメモリ表現

ActiveBasic と同じレイアウト。

```
  HeapAlloc が返す base
  ┌─────────────┬──────────────────┬────┐
  │ dword ヘッダ  │  バイト列（len）   │ NUL│
  └─────────────┴──────────────────┴────┘
         ▲                    ▲
         │                    └─ ユーザが見る String / StrPtr
         │                       （base + 4）
         └─ bit31 = ヒープ印（0x80000000）
            bit30..0 = 長さ（埋め込み NUL を含む）
```

- 確保サイズは `len + 5`（ヘッダ 4 + データ + 終端 NUL）。
- `Len(s)` は `[ptr-4] & 0x7FFFFFFF`。`lstrlenA` ではない。
- 静的リテラル（`OP_LEA_RAX_STR`）も直前 4 バイトに長さを持つが、**ヒープ印は付けない**。GC の `blocks[]` にも載らない。
- `MakeStr(p)` は `lstrlenA` で長さを取り、上記レイアウトへ複製する。

ヒープ印の意味:

- **precise マーク**では使わない（登録済み塊なら無条件にマーク）。
- **conservative マーク**では必須。ヘッダに印が無い塊はスキップする（確保直後でまだヘッダを書いていない窓、および「たまたまアドレス範囲に入った整数」への耐性の一部）。
- 旧 `StrFree` も印がある塊だけ `HeapFree(base)` していた。代入経路からは呼ばれなくなっている（本体生成は `g_rtStrFreeLab` が確保されたときだけ）。

---

## 3. 全体像

```
  Cat / Mid$ / Str$ / Chr$ / Input / MakeStr
            │
            ▼
     StrHeapAlloc(size)     ← HeapAlloc + blocks[] へ登録
            │
            ▼
     ヘッダに (len | 0x80000000) を書く
     rax = base + 4
            │
            ▼
     代入はポインタ格納のみ（旧値は即解放しない）
            │
            ▼
     セーフポイント
       1. ローカル precise ルートを marks[] に付ける
       2. StrCollect
            グローバル precise ルート
            ユーザ BSS の conservative 走査
            スタックの conservative 走査
            未マーク塊を HeapFree + swap-remove
            marks[] を 0 クリア
```

GC は **String ヒープだけ** を見る。`malloc` したバッファは対象外。UDT や `*Byte` もルートとしては登録しない。

---

## 4. BSS 上の GC 領域

モジュール `Dim` をグローバルへ割り当てたあと、その末尾に固定サイズの領域を足す。

```
g_gcBaseOff = g_gSize
g_gSize     = g_gSize + GC_REGION_SIZE   ' 38928
```

オフセットは `AstLower.abp` 先頭の定数。塊ポインタ枠は **32/64 どちらも 8 バイト刻み**（`SHL_ECX_3`）。32bit では下位 4 バイトだけ使う。

| オフセット | 定数 | 内容 |
|---|---|---|
| 0 | `GC_HDR_COUNT` | 登録数（ポインタ幅ストア、値は 0..4096） |
| 8 | `GC_HDR_BLOCKS` | `blocks[4096]` — `HeapAlloc` の **base** |
| 32776 | `GC_HDR_MARKS` | `marks[4096]` — 1 バイト/塊 |
| 36872 | `GC_HDR_PRECISE_COUNT` | グローバル precise ルート数 |
| 36880 | `GC_HDR_PRECISE_ROOTS` | ルートの BSS オフセット（各 4 バイト、最大 512） |
| 38928 | `GC_REGION_SIZE` | 領域全体 |

`blocks[i]` が指すのはユーザポインタではなく **ヘッダ先頭**。マーク時に `user = base+4`、`end = user+len` を計算する。

上限 `GC_MAX_BLOCKS = 4096` を超えると、`StrHeapAlloc` は確保したポインタを返すだけで **表に載せない**。その塊は二度と回収されない（リーク）。解放済みポインタを使う UAF にはならない。

---

## 5. 確保: `StrHeapAlloc`

[`LowEmitRtStrHeapAllocBody`](../src/actba64/StrGcRt.abp)（ラベル `g_rtStrHeapAllocLab`）。

1. `GetProcessHeap` → `HeapAlloc(heap, 0, rcx)`。`rcx` は呼び出し側が渡したバイト数。
2. 失敗なら rax = 0 で戻る。
3. `count < 4096` なら `blocks[count] = base`、`count++`。
4. rax = base を返す（ユーザポインタへの `+4` は Cat 等が行う）。

呼び出し側（いずれも `AstLower.abp`）:

- `Cat` / `Mid$` / `Str$` / `MakeStr` / `Input` ランタイム
- 式中の `Chr$`（6 バイト確保、ヘッダ `&H80000001`）

---

## 6. マーク

### 6.1 共通本体

[`LowEmitRtStrGcMarkBody`](../src/actba64/StrGcRt.abp) を 2 ラベルで出す。

| ラベル | `requireTag` | 用途 |
|---|---|---|
| `g_rtStrGcPreciseLab` | 0 | コンパイラが「ここは String ポインタ」と知っているスロット |
| `g_rtStrGcConsLab` | 1 | スタック / ユーザ BSS の生ワード |

入力は rcx = 候補ポインタ。

```
if ptr == 0: return
for i in 0 .. count-1:
    base = blocks[i]
    if base == 0: continue
    len  = [base] & 0x7FFFFFFF
    user = base + 4
    end  = user + len
    if ptr < user: continue          ' 符号なし
    if ptr > end:  continue          ' 符号なし（NUL 位置まで含む）
    if requireTag && ([base] & 0x80000000) == 0: continue
    marks[i] = 1
    return                           ' 最初に当たった塊で終了
```

範囲は閉区間 `[user, end]`。`String` 変数そのもの（`user`）も、`StrPtr` でデータ内部を指したポインタも、親塊をマークできる。

**x64 ではポインタ比較に `cmp rcx, rax`（`OP_CMP_RCX_RAX` = `48 39 C1`）と `JB` / `JA` / `JAE` を使う。** `cmp ecx, eax` + `JL` / `JG` だと、ヒープが `0x000001xxxxxxxx` のように下位 32bit が `0x80000000` を跨いだとき、生きている塊が未マークのまま `HeapFree` される。32bit 出力では同じ IR を `cmp ecx, eax` に落とす。

ループ変数 `i` と `count` の比較は 32bit 符号付きのまま（値は 0..4096）。

### 6.2 Precise: グローバル

MAIN 先頭で [`LowEmitGcPreciseRootsInit`](../src/actba64/AstLower.abp) が、コンパイル時に集めた BSS オフセットを `precise_roots[]` へ書き、個数を `precise_count` に入れる。

`StrCollect` は各オフセットについて:

```
p = *(globals + precise_roots[i])   ' LOAD_PTR
StrGcMarkPrecise(p)
```

対象はモジュールの `Dim s As String` と `Dim a(n) As String` の各要素。**UDT メンバの String は型表で区別できないため入れない。**

### 6.3 Precise: ローカル

関数ごとに `g_fnPreciseRoots[]`（フレームオフセット）を持つ。セーフポイント直前の [`LowEmitPreciseLocalMarks`](../src/actba64/AstLower.abp) が、Collect の **前** に:

```
LOAD_LOCAL off
CALL StrGcMarkPrecise
```

をルート数だけ出す。ここが marks[] を付ける唯一の「今のフレーム」経路。Collect 側はローカルオフセットを知らない。

登録タイミング:

- `LowAddSym` で `ty = TY_STRING` かつ ByVal（`isByRef = 0`）
- `TY_STRING_ARR` は要素ごとにオフセットを足す
- 関数の戻り値スロットも通常のローカルと同じ（名前は関数名）
- **ByRef String 引数は登録しない**（スロットはポインタのポインタ）

x64 の第 5 引数以降は `LowAddSym` 時点の負オフセットから、実在の `[rbp+0x30+(i-4)*8]` へ [`LowRetargetFnPreciseRoot`](../src/actba64/AstLower.abp) で付け替える。付け替えないと、存在しないスタックスロットをマークして戻り String を落とす。

非引数ローカルは関数入口で 0 初期化。未初期化のゴミを String ポインタとしてマークしないため。

### 6.4 Conservative: ユーザ BSS

`offset = 0` から `g_gcBaseOff` 直前まで、ポインタ幅刻みで `LOAD_PTR` → `StrGcMarkConservative`。GC 領域自身は走査しない。

ここに UDT 内 String、`*Byte` に残ったユーザポインタ、誤って載った整数が混ざる。ヒープ印と範囲判定で、登録塊に当たらない値は無視される。

### 6.5 Conservative: スタック

Collect フレーム内の RSP から、TEB の **StackBase**（x64: `gs:[8]`、`OP_MOV_RAX_GS8`）の直前まで、ポインタ幅刻み。

- 走査するのは **メモリ上のスタック** だけ。rax / rcx / rsi などレジスタは見ない。
- Collect 自身のフレームも含む（候補ポインタが一時的に積まれていれば拾える）。
- 呼び出し元のフレームも、まだ return していなければ範囲に入る。

---

## 7. 掃き出しと marks クリア

[`LowEmitRtStrCollectBody`](../src/actba64/StrGcRt.abp) の後半。`i = count-1` から 0 方向へ:

```
if marks[i] != 0:
    i--
    continue
HeapFree(blocks[i])          ' GetProcessHeap + HeapFree。POP の過不足に注意
last = count - 1
blocks[i] = blocks[last]
marks[i]  = marks[last]
count--
' i は据え置き（移動してきた要素を再判定）
```

据え置きを忘れると、末尾から移した未マーク塊が残る。以前は `HeapFree` のあとに POP が余り、2 回目の解放でスタックが壊れた。

**marks[] のゼロクリアは掃き出しの後**（`labSweepDone` のあと）。以前は Collect の先頭で消しており、呼ぶ直前の `LowEmitPreciseLocalMarks` が全部無効になっていた。ローカル String の生存が conservative スタック走査だけに依存し、レジスタに残った戻り値や、スタックに載らなかった一時値が UAF になった。

BSS の marks は起動時 0。次サイクルは「ローカル precise マーク → Collect」から始まる。

---

## 8. セーフポイント（いつ集めるか）

[`LowEmitStrCollectSafepoint`](../src/actba64/AstLower.abp):

```
LowEmitPreciseLocalMarks(ctx)
CALL StrCollect
```

`g_rtStrCollectLab < 0` なら何もしない（その翻訳単位で String ヒープ確保が一度も出ていないとき）。一度でも `StrHeapAlloc` を出すと 4 ラベル（alloc / precise / cons / collect）が確保される。

挿入箇所:

| 地点 | 理由 |
|---|---|
| `For` / `While` / `Do` のループ先頭 | **MAIN** では毎回。関数内は本体または条件が Cat / `Mid$` / `Chr$` 等を含むときだけ。`GetLinePrefix$` のような関数呼び出しでは出さない（描画 While で行末の String を落とすため） |
| `Print` / `Input` のあと | 一時 String を回収 |
| モジュール MAIN 終了直前 | プロセス終了前の掃除（その後すぐ `ExitProcess`） |

関数エピローグでは Collect しない。`Mid$` や `Hl_Lower$` のような入れ子の終了時に、呼び出し元の `String` が conservative 走査から漏れて `HeapFree` されるのを避けるため。GUI ではメッセージループ（MAIN の `Do`）の先頭で回収する。関数内の一時値は、その関数自身が Cat / `Mid$` を含むループを持つか、MAIN に戻ったあとで回収する。

---

## 9. コンパイラ側のルート表

コンパイル中のメモリ（実行ファイルには出ない）:

| 表 | 内容 |
|---|---|
| `g_preciseRoots[]` / `g_preciseRootCount` | グローバル String の BSS オフセット。MAIN で BSS へコピー |
| `g_fnPreciseRoots[]` / `g_fnPreciseRootCount` | 現在の関数のフレームオフセット。関数ごとにリセット |

上限はどちらも `GC_MAX_PRECISE = 512`。溢れた分は precise に乗らず、conservative 頼みになる。

---

## 10. ランタイムの出る順

`AstToIr` 末尾で、使ったラベルだけ本体を出す。GC 関連は文字列ランタイムのあと:

```
Cat / Mid / Str$ / Print / Input / Val / ...
MakeStr / StrCmp / StrFree（呼ばれたとき）
StrHeapAlloc / StrGcPrecise / StrGcCons / StrCollect
```

IR は通常の `OP_ENTER` / `OP_CALL_LAB` / `OP_CALL_API` で、専用の GC 命令セットは無い。ポインタ比較と TEB 読み出しだけ専用オペコード。

---

## 11. 制約と既知の落とし穴

生きたポインタが次のどれにも無いと、次のセーフポイントで塊は解放される。

1. **レジスタ専用の一時値**  
   ループ先頭の Collect の直前に、結果が rax だけ、スタックにも precise スロットにも無い。

2. **UDT の String メンバ**  
   precise 未登録。その UDT がグローバルか、スタック上のワードとして conservative に見える必要がある。

3. **ByRef String**  
   実体スロットは呼び出し元側。呼び出し先のフレームオフセットはルートにならない。

4. **ヒープ印の無い塊**  
   conservative はスキップ。precise ならマークする。確保とヘッダ書き込みの間にセーフポイントは挿入していない。

5. **`malloc` と String の混同**  
   `MakeStr` は複製する。元バッファは GC 対象外。`free` は手動。

6. **4096 塊を超える確保**  
   リーク。エディタのように一時文字列が多いループでは、ループ先頭の Collect が効いている前提。

7. **関数ラベル ID と戻り型の衝突（修正済）**  
   `AST_FUNC.extra` をラベルで上書きすると `TY_STRING` と衝突し、戻りが precise から外れた。extra は Parser の戻り型のまま。

これらが重なると、解放済みポインタを `TextOut` / `lstrlenA` に渡し、画面のゴミ・白画面・アクセス違反になりうる。x64 では故障アドレスがヒープの下位 32bit だけに見えることがある（昔の符号付き 32bit 比較の名残、または既に unmap された下位アドレス）。

---

## 12. テスト

`src/actba64/test/` のうち GC を直接狙うもの:

| ファイル | 見ていること |
|---|---|
| `t_str_gc.abp` | `For` 内の大量 Cat のあと、先に入れたグローバル `keep` が残る |
| `t_gc_while.abp` | `While` 内 Cat でも同様 |
| `t_gc_nested.abp` | `While`+`Mid$` の内側で確保しない `For` が走っても元の行が残る |
| `t_str_ret.abp` | String 戻りが、先行する Cat で有効になった Collect に潰されない |
| `t_malloc_makestr.abp` | UDT の `*Byte` + `malloc` + `MakeStr`。ヒープが高位でも複製が残る |

CUI で `Expect: 0`。GUI の描画ループまではカバーしない。

---

## 13. 実装を追うときのチェックリスト

コードを変えるとき、次が同時に成り立っているか。

- [ ] ローカル precise マークは **Collect より前**。marks クリアは **掃き出しより後**。
- [ ] ポインタの大小比較は 64bit 符号なし（`CMP_RCX_RAX` + `JB`/`JA`/`JAE`）。
- [ ] インデックス vs `count` は 32bit のままでよい。
- [ ] 関数エピローグは Collect のあとで戻り値をロードする。
- [ ] x64 の第 5 引数以降の String は precise オフセットを付け替える。
- [ ] `blocks[]` の添字は常に `i * 8`。`HeapFree` 前後でスタックの PUSH/POP が対になる。
- [ ] 掃き出しは swap-remove で `i` を進めない。
- [ ] 静的リテラルを `blocks[]` に載せない、ヒープ印も付けない。
