# リリースノート

## v0.2.0（v0.1.9 からの変更点）

Windows の API を UTF-8 にそろえた更新です。日本語や CP932 にない文字（𠮷 など）のパス・ファイル名・窓の文字列が化けなくなりました。あわせて 64bit の exe に例外の巻き戻し情報を出し、ProjectEditor にツールバーを足しました。パスや文字列を返す API の戻り値の数え方が変わるので、下の **互換性** を見てください。

### 文字化け

A 版の API をそのまま公開していて、日本語のパスや文字列が CP932 になっていた API を UTF-8 にそろえました（[unicode-api.md](./unicode-api.md)）。

- `CopyFile` / `MoveFile` / `DeleteFile` / `CreateDirectory` / `RemoveDirectory` / `SetCurrentDirectory` / `SetFileAttributes` / `LoadLibrary` は、UTF-8 のパスをワイド文字 API に渡します。CP932 にない文字（𠮷 など）のパスも扱えます。
- `GetCurrentDirectory` / `GetTempPath` / `GetWindowsDirectory` / `GetSystemDirectory` / `GetFullPathName` / `FindFirstFile` / `FindNextFile` は、パスやファイル名を UTF-8 で返します。
- `GetCommandLine` と `GetCmd` は UTF-8 を返します。`CreateProcess` は UTF-8 のコマンドラインをワイド文字 API に渡します。
- `GetEnvironmentVariable` / `SetEnvironmentVariable` / `GetComputerName` / `GetUserName` / `DragQueryFile` は UTF-8 で読み書きします。`OutputDebugString` も UTF-8 を渡せます。
- `FormatMessage` は、差し込みを使わないとき UTF-8 で返します。日本語の Windows のエラー文が `Print` で化けなくなりました。
- abdbg は、日本語のフォルダーにある exe もデバッグできます（パスを UTF-8 で受け、ワイド文字 API で起動します）。
- 無印の `GetMessage` / `PeekMessage` / `DispatchMessage` / `PostMessage` / `CallWindowProc` / `SetWindowLong(Ptr)` / `GetWindowLong` / `Get/SetClassLong` を W 版にしました。窓は Unicode なので、IME で入れた CP932 にない文字（𠮷 など）も `WM_CHAR` でそのまま届きます。`GWL_WNDPROC` で付けた手続きが受ける `WM_SETTEXT` などの文字列はワイド文字列になり、前の手続きへは無印の `CallWindowProc` で渡します。
- `MessageBox`（`MsgBox`）が CP932 にない文字（𠮷 など）も出せるようになりました。
- レジストリ（`RegOpenKeyEx` / `RegCreateKeyEx` / `RegSetValueEx` / `RegQueryValueEx` / `RegDeleteValue` / `RegDeleteKey`）が、キー・値の名前と文字列の値を UTF-8 で扱います。
- `SHBrowseForFolder` / `SHGetPathFromIDList` / `SHFileOperation` / `FindWindow` / `ShellAbout` / `PlaySound` / `GetDriveType` / `GetDiskFreeSpace(Ex)` / `ExtractIcon(Ex)` / `LoadCursorFromFile` を W 版にしました。
- ファイルを開く／保存ダイアログ（`GetOpenFileName` / `GetSaveFileName`）を W 版にしました。CP932 にない文字のファイル名も選べます。
- フォントのダイアログ（`ChooseFont`）を W 版にし、`GetObject` で読んだフォント名も UTF-8 で返します（以前は CP932）。
- `lstrcmpi` / `CompareString` / `CharUpper` / `CharLower` が、日本語や全角の英字を含む UTF-8 の文字列を正しく比べ・変えます。
- `RegisterWindowMessage` / `RegisterClipboardFormat` / `GetClipboardFormatName` / `SetComputerName` / `GetFileTitle` / `GetCompressedFileSize` / `CreateMailslot` / `ExtractAssociatedIcon` / `mciGetErrorString` を W 版にしました。
- 印刷（`PrintDlg` / `PageSetupDlg` / `CreateDC` / `ResetDC`）を W 版にしました。日本語の名前のプリンターも開けます。`hDevMode` / `hDevNames` の中身はこれまでどおり A 版の形で、名前は UTF-8 です。
- `mciSendCommand` が、日本語や CP932 にない文字の入ったファイル名の音・動画も開けるようになりました（`MCI_OPEN` / `MCI_LOAD` / `MCI_SAVE` のファイル名と `MCI_INFO` / `MCI_SYSINFO` の答えが UTF-8）。
- 検索ダイアログ（`FindText`）を W 版にしました。日本語や CP932 にない文字（𠮷 など）の検索語も、呼び出し側のバッファへ UTF-8 で届きます。通知の `lParam` は呼び出し側の `FINDREPLACE` のままです。
- WinINet（`InternetOpen` / `InternetConnect` / `FtpGetFile` / `FtpSetCurrentDirectory` / `FtpGetCurrentDirectory` / `FtpFindFirstFile` / `InternetFindNextFile`）を W 版にしました。日本語のファイル名・フォルダ名を UTF-8 で扱えます。`FtpGetCurrentDirectory` の 3 つ目の引数は `*DWord`（`VarPtr` で渡す）です。
- 受け皿に入らない文字列を UTF-8 で切って書くとき、最後の文字が欠けていなくても 1 文字多く落としていたのを直しました。

**互換性**: パスや文字列を返す API の戻り値と書き戻す値は、文字数ではなく UTF-8 のバイト数になります。サブクラスの手続きで `CallWindowProcA` を自分で Declare して使っているときは、無印の `CallWindowProc` に替えてください。CP932 のバイト列が返ると決めて自分で UTF-8 に直しているプログラムは、そのまま動きます（妥当な UTF-8 は直さない作りなら）。

### コンパイラ

- 64bit の Windows の exe / DLL に例外の巻き戻し情報（`.pdata`）を出します。OS が例外を配るときや `RtlCaptureStackBackTrace` で呼び出し履歴をたどれるようになり、NULL の参照などはデバッガー無しでも c0000005 で終わります。これまでは新しい Windows で c0000409 の fail fast になることがありました（[different.md](./different.md)）。`-actba32` と `-linux` は出しません。
- `Input` / `Input #` の読み先に配列の要素（`a[i]` / `a(i)` / `a[i, j]`）を書けるようにしました。
- 仮引数の `DWordPtr` などのポインタの別名（TypeDef の `*DWord` など）を `*T` として読み、添字で読み書きできるようにしました。
- 実数（Double）を `Long` / `Word` / `Byte` の配列の要素へ代入すると、切り捨てて入れます。

不具合の修正:

- `As String` の Type メンバ（`sa.name`・`p->name`・Class のメンバ）を `Print` すると、文字列ではなく数（文字列のポインタ）が出ていたのを直しました。連結（`sa.name + sa.name`）と比較も文字列として扱います。

### デバッガー

- ProjectEditor で、動いていないときに F10 / F11 を押すとデバッグ実行を始め、ソースの最初の文で止まります（abdbg の `n` / `s` を `r` の前に使ったときも同じ）。ステップで止まるのはユーザーのソースの文だけで、ライブラリの中のトップレベルの文では止まりません。
- abdbg: `Debug` 文でない `int3`（OS の中のものなど）では止めずに続けます。
- abdbg: 止めた例外を続けた後に c0000409 の fail fast が来たときは、プログラムを元の例外のコードで終わらせます（同じ例外で二度止まっていました）。

### ProjectEditor

- メニューの下にツールバーを足しました（Windows 版）。新規・開く・上書き保存 / 切り取り・コピー・貼り付け / 元に戻す・やり直し / 検索 / コンパイル・実行 / デバッグ実行・停止・ステップ オーバー・ステップ イン があります。ヒントはメニューの見出しと同じです。
- ファイル メニューの一番下に **終了** を足しました（閉じるボタンと同じく保存を尋ねます）。
- Basic メニューの「_DEBUG を定義」を外しました。`_DEBUG` はデバッグ実行（F5）で `-debug` を付けて訳すときに定義されます。

### ドキュメント

- [unicode-api.md](./unicode-api.md) を足しました（文字コードを扱う API の説明）。
- README の現状から、対応済みの `Int64` / `QWord`・指数表記のリテラル・`Single` の演算を外しました。
- 初期の試作を [bellyoshi/Actba64-prototype](https://github.com/bellyoshi/Actba64-prototype) に移したことを README と [index.md](./index.md) に書きました。
- リファレンスの LP64 に「Long and Pointer 64-bit」を添えました。

### テスト

- UTF-8 の API のユニットテスト `FileUtf8Test`・`SysUtf8Test`・`MsgWideTest`・`RegUtf8Test`・`ShellUtf8Test`・`MiscUtf8Test` を足しました。
- コンパイラのテスト `t_unwind_null`・`t_unwind_walk`・`t_input_elem`・`t_dwordptr_param_dbl_store`・`t_udt_str_print` を足しました。
- abdbg のテスト `step_start`・`brk_foreign`・`failfast` を足しました。
- CI のブートストラップのコンパイラを v0.1.9 に上げました。

## v0.1.9（v0.1.8 からの変更点）

デバッガーを足した更新です。ProjectEditor でブレークポイントを置き、1 行ずつ進め、変数の値を見られます。デバッガー本体の `abdbg.exe` も ActBa64 で書いています（[debugger.md](./debugger.md)）。

### デバッガー

ProjectEditor（[projecteditor.md §7.3](./projecteditor.md#73-デバッグ実行)）:

- メニュー バーに **デバッグ** を足しました。デバッグ実行 / 続行（F5）・デバッグの停止（Shift+F5）・ステップ オーバー（F10）・ステップ イン（F11）・ステップ アウト（Shift+F11）・ブレークポイントの設定 / 解除（F9）・条件付きブレークポイントがあります。
- 行番号の余白をクリックするか F9 でブレークポイントを付け外しします（赤い四角）。**条件付きブレークポイント**（例: `i = 5`、`s <> ""`）は橙の四角で、条件が成り立つときだけ止まります。行を足したり消したりすると、印もいっしょにずれます。
- F5 は `-debug` を付けて訳し、デバッガーで動かします。止まった行を黄色にし、メッセージウィンドウに止まった理由（ブレークポイント・ステップ・`Debug` 文・例外）を出します。
- **デバッグの窓**を足しました。上は呼び出し履歴で、段を選ぶとその行へ移ります。下は AB4 と同じく **グローバル / ローカル** のタブと変数のツリーで、Type・配列・Type へのポインタは + で開けます。整数は `65535(&HFFFF)` のように 16 進も出します。
- プログラムが落ちたときは、例外のコードと落ちた行で止まります（API の中で落ちたときは、その API を呼んだ行）。
- 64bit と 32bit（`-actba32`）の Windows の exe で使えます。Linux 版のエディタと Linux の exe ではまだ使えません。

abdbg.exe（デバッガー本体。リリースの `abdbg.exe`）:

- コマンドラインでも使えます（`abdbg [-console] prog.exe`）。標準入力のコマンドでブレークポイント（条件付きも）・続行・ステップ・呼び出し履歴・変数の値（`p a.x`、`p arr(2)`、`p pp->y` など）を扱い、答えを 1 行ずつ出します。

`Debug` 文:

- AB4 と同じく、デバッガーの下で動いているときにその行で止まります。デバッガー無しで動かしたときと、`-debug` を付けずに訳したときは何もしません。

### コンパイラ

- `-debug` を付けると、exe の隣にデバッグ情報 `.abdbg`（行の表・手続き・変数・Type）を書きます。exe の中身は `_DEBUG` の部分と `Debug` 文のほかは変わりません（`-linux` では書きません）。
- HANDLE / HWND / WPARAM / LPARAM / LONG_PTR / ULONG_PTR / SIZE_T / DWORD_PTR などを、ポインタ幅（64bit 出力では 64bit）の整数にしました。配列の要素の間隔もポインタ幅です。SIZE_T / DWORD_PTR の配列の要素を読むとコンパイルが止まっていたのも直しました。
- VoidPtr / LPSTR の配列・Type のメンバ・関数の戻り値の計算と、Print・Str$・Double への変換で、64bit の値が切れていたのを直しました（AB4.20 のサンプル SystemWatcher の物理メモリが負の値で出ていた件）。

### ProjectEditor

- プロジェクトのツリーにアイコンを出し、フォルダーのノードはフォルダーの絵にしました（Windows 版）。

### ドキュメント

- [debugger.md](./debugger.md) を足しました（デバッガーの作り、`.abdbg` の形式、abdbg のコマンドと答え）。
- README と [index.md](./index.md) に、ActiveBasic との互換性についての注意書きを入れました。

### テスト

- abdbg のテスト `src\abdbg\run_test.ps1`（12 本。64bit と 32bit）と、デバッガーのユニットテスト `src\dbgtest`（ProjectEditor と abdbg の窓を使わない部分）を足しました。CI と `check.ps1 unit` で回します。
- コンパイラのテスト `t_debug_info`・`t_voidptr_wide`・`t_handle_wide`・`t_sizet_wide` を足しました。
- Linux のテスト `lx_so_ret_cb` の期待値を、Double の有効 15 桁（`1.4142135623731`）に合わせました。

## v0.1.8（v0.1.7 からの変更点）

ProjectEditor のプロジェクトビューからソースを足す・外すことができるようになり、「プロジェクトを閉じる」を足した更新です。

### ProjectEditor

プロジェクトビュー（[projecteditor.md §6](./projecteditor.md#6-プロジェクト)）:

- 右クリックでメニューが出ます。Linux 版のリストでも同じです。
  - ルート（`.pj`）: **ファイルを挿入** — 選んだファイルを `.pj` のフォルダーからの相対パス（`sub\a.sbp`、`..\common\b.sbp` など。ドライブが違えばフルパス）で `#SOURCE` の最後に足します。もうプロジェクトにあるファイルは足しません。
  - ファイル: **プロジェクトから削除** — `#SOURCE` からその行を消します（ファイルそのものは消しません）。`#SOURCE` で最初の `.abp`（プロジェクトのメインファイル）なら「このファイルはプロジェクトのメインファイルです。」と出して確かめます。
  - ファイル: **プロパティ** — プロジェクト内のパス・フルパス・サイズを出します。
  - `.pj` は元の文字コードと改行のまま書き換えます。
- **ファイル → プロジェクトを閉じる** を足しました（ルートの右クリックにもあります）。プロジェクトの文書（`#SOURCE` と `.wnd`）を、保存していなければ「保存しますか」と尋ねながら閉じてから、プロジェクトを閉じます。キャンセルすると開いたままです。プロジェクトウィンドウの × も同じです。
- 開けるプロジェクトは 1 つだけにしました。別の `.pj` を開くときと、AB4プロジェクトを新しく作るときは、先に今のプロジェクトを閉じます（上と同じく保存を尋ねます）。これまでは一覧が差し替わるだけで、前のプロジェクトの文書は開いたまま残りました。

AB4プロジェクト作成:

- 「EXE - DOS プロンプト ベース」も作れるようにしました。N88 プロンプト ベースと同じ 4 つのファイルで、`<名前>.abp` に `#N88BASIC` ではなく `#console` を置きます。AB 4.20 で作ったものとバイト単位で同じです。コマンドラインでは `ProjectCmd -createPj <名前> -dos` です（[projecteditor.md §7.2](./projecteditor.md#72-ab4-プロジェクト作成と-projectcmd)）。

不具合の修正:

- 64bit 版で、プロジェクトを読み直すたびにプロジェクトツリーのノードが増えていきました（前の一覧が消えずに残っていました）。読み直すときに一覧を正しく消すようにしました。

### N88BASIC

- `n88graph.abp` を `#strict` で読んだときの暗黙の変換の警告を、`As` で明示して消しました。動きは変わりません。

### テスト

- ユニットテスト `ProjTreeTest` に相対パスの作り方と同じパスの比べ方を、`EditorNewFormTest` に `#SOURCE` から行を消す確かめを足しました。
- ユニットテスト `AB4ProjTest` に DOS プロンプト ベースの確かめを足しました。

## v0.1.7（v0.1.6 からの変更点）

手続きの `cdecl`、`*QWord` / `*Int64` のポインタ、Double の 15 桁の表示を足し、AB4 のコードを移すときの直し方をまとめた更新です。

### コンパイラ

- `Function 名前 cdecl(...)` / `Sub 名前 cdecl(...)` と、関数ポインタの `*Function cdecl(...)` / `*Sub cdecl(...)` を書けます（ActBa64 だけの書き方です）。`-actba32` では cdecl の手続きは引数を片付けずに戻り、呼んだ側が片付けます。C の `qsort` へ比較関数を渡せます。
- `*QWord` / `*Int64` のポインタ（変数・仮引数）を、添字で 8 バイトの整数を読み書きするポインタとして読みます。これまでは 64bit 出力でも `*DWord` / `*Long` として読み、警告 1102 を出して下位 32 ビットしか扱えませんでした。`QWord` の要素は符号なし、`Int64` は符号つきです。`-actba32` と Type メンバの `As *QWord` はまだ 32bit です。
- `Print` / `Str$` の Double を ActiveBasic と同じ有効 15 桁で書きます（`Print Sqr(5)` は `2.23606797749979`）。これまでは小数 6 桁に丸めていました。10^15 以上と 10^-4 未満は `1.5E+20` / `1.234E-5` の形です。
  - このため、誤差の残る計算の結果が `0` などのきれいな数にならないことがあります（`1` から `0.1` を 10 回引くと `1.38777878078145E-16` のような値）。

不具合の修正:

- `-actba32` で `Declare ... cdecl` の関数（`wsprintf` など）を呼んだ後、呼んだ側が引数を片付けます。これまでは `cdecl` を読み飛ばして stdcall と同じに呼んでいたので、繰り返し呼ぶとスタックが積み残しで溢れました。64bit 出力は元から同じ呼び方なので変わりません。
- `-actba32` の関数ポインタの呼び出しは、呼んだ後に `esp` を呼ぶ前の位置へ戻します。これまでは、型より引数の多い stdcall の関数を呼ぶとスタックがずれました。

### ProjectEditor

AB4プロジェクト作成:

- 「EXE - N88 プロンプト ベース」も作れるようにしました。`#N88BASIC` の `<名前>.abp` と `.idx`・`.pj`・`.wrk` の 4 つを書き、AB 4.20 で作ったものとバイト単位で同じです。コマンドラインでは `ProjectCmd -createPj <名前> -n88` です（[projecteditor.md §7.2](./projecteditor.md#72-ab4-プロジェクト作成と-projectcmd)）。

### ドキュメント

- AB4 のコードを移すときの直し方を [migrate-ab4.md](./migrate-ab4.md) にまとめました。宣言だけの `Virtual` の vtable を自分で埋めるコードは `Virtual` と `Override` に、引数の数が合わないコールバックは `cdecl` に書き換えます。

### テスト

- 回帰テスト `t_cdecl_func`、`t_cdecl32`、`t_class_override_cb`、`t_qword`、`t_qword_ptr`、`t_str_double15` を足しました。`t_for_double` は 15 桁の表示に合わせて直しました。
- ユニットテスト `AB4ProjTest` に N88 プロンプト ベースの確かめを足しました。

## v0.1.6（v0.1.5 からの変更点）

AB4デザイナーのイベント処理ダイアログを AB 4.20 に近づけた、小さな更新です。

### コンパイラ

- 式の中の `x As QWord` / `x As Int64` を 64bit への変換として読みます。`-actba32` でも 64bit です。`Long` は符号で、`DWord` は 0 で広げ、64bit どうしはそのままです。`-actba32` ではこれまで `As DWord` / `As Long` として読んでいたので、`lo Or (hi As QWord) << 32` のような書き方（RGBALib の `lengthQWord` など）で上位 32 ビットが消えていました。

### RAD（#USEWINDOW=1）

- TrackBar のイベント `OutOfMemory`、`ReleasedCapture`、`CustomDraw`（`NM_*`）を、AB 4.20 と同じく `WM_NOTIFY` で受けるようにしました。`ProjectCmd -regen` が作る `Callback.wbp` にも入ります（[projecteditor.md](./projecteditor.md#71-ab4-互換の-radusewindow1)）。

### ProjectEditor

AB4デザイナーのイベント処理ダイアログ:

- TreeView と ListView のイベントを AB 4.20 と同じ並びと概要で出します。ダイアログには `CustomDraw` と `ReleasedCapture` を出さず、ListView は `NM_` のものを先に、`LVN_` のものを後に並べます。
- TrackBar のイベント（上の RAD）を出します。
- HScrollBar / VScrollBar などのイベントの無い部品でも、音を鳴らすだけにせず、AB 4.20 と同じく空の一覧でダイアログを出します。
- ラベルのイベントの概要を「スタティック テキストが…」にしました。

不具合の修正:

- プロジェクトツリーで、選んだままのノード（文書をすべて閉じた後の `.wnd` など）をクリックしても開けませんでした。ダブルクリックでも開くようにしました（開いていれば前に出すだけです）。

### テスト

- 回帰テスト `t_int64_cast` を足しました。
- ユニットテスト `Ab4DesignTest` と `RadGenTest` に、TreeView / ListView / TrackBar / ラベルのイベントの確かめを足しました。

## v0.1.5（v0.1.4 からの変更点）

### ハイライト

- **ProjectEditor に AB4デザイナーが付きました。** AB 4.20 のウィンドウ定義ファイル（`.wnd`）を開くと、窓と部品を絵で出します。部品を道具箱から足す・動かす・大きさを変える・消すことができ、ID・キャプション・スタイル・窓のフォントなどのプロパティも変えられます。部品を右クリックすると、AB 4.20 と同じイベント処理のダイアログからイベントの `Sub` をソースに足せます。詳しくは [projecteditor.md の AB4デザイナー](./projecteditor.md#ab4デザイナー) を見てください（Windows 版。Linux 版は一部だけ）。
- **AB 4.20 と同じ形のプロジェクトを作れます。** ファイル → AB4プロジェクト作成 で「EXE - ノーマル ウィンドウ ベース」のプロジェクトを作ります。できる 8 つのファイルは AB 4.20 で作ったものとバイト単位で同じです。作成と RAD の生成は、新しいコマンドラインの `ProjectCmd` が受け持ちます（[projecteditor.md §7.2](./projecteditor.md#72-ab4-プロジェクト作成と-projectcmd)）。
- **`-actba32` でも `Int64` / `QWord` が 64bit の整数になりました。** これまで 32bit 出力では `Long` / `DWord` として読んでいました。
- **コンパイルが速くなりました。** コードの出力が出力の大きさの 2 乗の時間をかけていたのを直し、セルフコンパイルが 16 秒から 2 秒になりました。

### コンパイラ

- `-debug` を足しました。`_DEBUG` を定義し、`-o` が無ければ `.pj` の `#OUTPUT_DEBUG` へ出します（無ければ `#OUTPUT_RELEASE`）。AB4 のデバッグ実行で入る `#IFDEF _DEBUG` の部分を入れるためのもので、**デバッガーは付きません**（[build.md](./build.md)）。
- `-actba32` の `Int64` / `QWord`:
  - 変数・仮引数・`ByRef`・戻り値（`Function` / メソッド / `Declare`）で 64bit のまま扱います。算術・比較・シフト・`Double` との変換も 64bit です。`\` と `Mod` は ntdll の `_alldiv` などを呼びます。
  - 64bit のリテラルを読み、`_INT64` を定義します。
  - 配列・`Type` のメンバ・`Declare` と関数ポインタの仮引数はまだ 32bit で、警告 1102 を出します。
  - `Print` / `Print #` / `Write #` は AB 4.20 と同じく `QWord` を符号付きで出します（`Str$` は符号なし）。
- 2^63 以上の十進の整数（18446744073709551615 まで）を `QWord` のリテラルとして読みます。これまでは `Double` で読んでいたので、`QWord` へ入れると 0 になっていました。`Const` も同じです。
- 64bit 整数の警告に元の型名を出します（「QWord は DWord（32 ビット）として扱います」）。
- `Input` の先がポインタの変数なら、整数として読みます（AB4 と同じ）。
- メソッドの中で `a->b->M()`（`*Class` のフィールドの先の `*Class` のフィールドのメソッド）を呼べます。
- `BytePtr` の配列の要素の先を添字で読めます（`LBL[i * 2][0]`）。これまでは「コード生成に失敗しました」になっていました。
- この 3 つで、AB4 用の FT-GBDumper と FT-GBADumper をソースを変えずにコンパイルできるようになりました。

不具合の修正:

- `For` の制御変数が `ByRef` の仮引数のとき、64bit でも `-actba32` でも実行中に落ちていました。引数の場所ではなく、指す先を宣言の幅で読み書きするようにしました。

### Include

- `d3d11.sbp` の `ID3D11Device` を `IUnknown` の直下に戻しました。`ID3D11DeviceChild` を継承していたため vtable が 4 つずれ、`dx_Init` が「CreateRenderTargetView failed.」で止まっていました。DirectX のサンプルがまた動きます。
- `d3d11/dx_shader.sbp` を足しました（`dx_graphics.sbp` から読みます）。シェーダーのコンパイルと作成（`dx_CompileShader`、`dx_CreateShaders`）、位置＋色の頂点のシェーダーと入力レイアウト（`dx_PosColorHlsl$`、`dx_CreatePosColorLayout`）、バッファ（`dx_CreateBuffer`）、解放（`dx_ReleaseCom`）、失敗の表示（`dx_FailStep`）があります。

### RAD（#USEWINDOW=1）

- `.wnd` の部品の種類 13 を VScrollBar、14 を UpDown として読みます（逆に読んでいました）。UpDown には AB 4.20 と同じく `WM_SETFONT` を送りません。全種類の部品を置いた `.wnd` で、`Callback.wbp` / `MakeWindow.wbp` が AB 4.20 の出力とバイト単位で同じになりました。
- 生成はエディタから `ProjectCmd -regen <.pj>` に移りました。ProjectEditor はコンパイルの前にこれを呼びます。

### ProjectEditor

- AB4デザイナー（上のハイライト）。文書のタブは「コード」「デザイナー」「AB4デザイナー」の 3 つになり、`.wnd` は開くと初めから AB4デザイナーで出ます。F12 でコードと切り替えます。
- ファイル → AB4プロジェクト作成（上のハイライト。Windows 版だけ）。
- プロジェクト ウィンドウをツリーにしました。ルートは `.pj` のファイル名で、`..\common` などのフォルダーごとにまとめます。日本語のファイル名もそのまま出ます。`<名前>.wnd` は `<名前>.abp` の下に出ます（Linux 版はこれまでのリスト）。
- 「表示」メニューを足し、「プロジェクトビュー」でプロジェクトの窓を出したり隠したりできます。隠してもプロジェクトは閉じません。
- Basic メニューに「_DEBUG を定義・デバッガーなし(-debug)」を足しました。
- 検索などのダイアログの共通部分をまとめました（動きは変わりません）。

### 配布

- `ProjectCmd.exe` を同梱します（`release_build.ps1` / `.sh` で作ります）。ProjectEditor の RAD の生成と AB4 プロジェクト作成に使います。

### サンプル

- DirectX の 5 つのサンプル（dxcube、dxcube2、dxsample、dxvertexcolor、dxxform）を `dx_shader.sbp` を使う形にし、合わせて約 670 行減らしました。64bit と `-actba32` の両方で動くことを確かめています。
- dxsample の出力を 64bit にしました。
- dxcube2 の `Callback.wbp` / `MakeWindow.wbp` を `.wnd` から作り直しました。Esc で窓を閉じる処理は無くなりました。

### テスト

- 回帰テスト `t_int64_32`、`t_for_byref`、`t_input_ptr`、`t_class_ptrfield_chain`、`t_byteptr_arr_elem_idx`、`t_ifdef_debug`、`t_ifdef_nodebug` を足しました。`t_int64_arith` / `fix` / `ret` / `unsigned` は `-actba32` でも動かします。
- ユニットテスト `Ab4DesignTest`、`AB4ProjTest`、`ProjTreeTest` を足しました。

## v0.1.4（v0.1.3 からの変更点）

### ハイライト

- **255 バイトを超える文字列リテラルを書けます。** これまでは 255 バイトで切れていました。`"..."`、`ex"..."`、`Const`、`Len`、連結のどれでも全体の長さになります。
- **AB 4.20 の RAD で作ったウィンドウのプロジェクトをそのままコンパイルできます。** `#USEWINDOW=1` の `.pj` の隣に `<名前>.wnd` があれば、ProjectEditor はコンパイルの前にそこから `Callback.wbp` と `MakeWindow.wbp` を作り直します。AB 4.20 の Samples などで、AB 4.20 の出力とバイト単位で一致することを確かめています。詳しくは [projecteditor.md §7.1](./projecteditor.md#71-ab4-互換の-radusewindow1) を見てください。

### コンパイラ

AB 4 が通していた書き方を読むようにしました。

- `Const X = 32 As DWord` のように、値の後ろに `As 型` を書けます。
- `If i = > n`、`If i = < n`（`=` と `>` / `<` の間の空白）を `>=` / `<=` と読みます。
- `& HC` のように `&` と `H` の間に空白がある 16 進を読みます（`If & HC ...` のようにキーワードの後ろでも）。直前が値なら、これまでどおり連結の `&` です。
- `Else 条件 Then` の行はただの `Else` として読み、警告を出します。`ElseIf` と書いてください。
- `If x Then Continue` の次の行の `For` / `Do` / `While` を、`Continue For` などと読まなくなりました。
- `Sub F(a As Long, )` のように、仮引数の最後のカンマを読み飛ばします。
- 配列の初期化子の要素に `As` を付けられます（`[&H3031 As BytePtr, "Nintendo", ...] As BytePtr`）。
- `*Function(...)` の `As` を省くと、`Function` と同じく `Double` を返す関数ポインタになります。
- `TypeDef X = *` で行が終わる型を、`VoidPtr` と同じ型の無いポインタとして読みます。
- 配列でも関数ポインタでもない変数に `()` を付けた `v()` は、`v` の値です。
- 小文字の `this` を `This` と同じに扱います。
- メソッドの中で、フィールドと同じ名前の仮引数があれば、仮引数を先に読みます（`Sub Init(Max As DWord)` の中の `Max`）。

ポインタと関数ポインタ:

- `Dim a[n] As *T`（`*Long`、`*Type`、関数ポインタの `TypeDef` も）は、要素がポインタ幅の配列です。`a[i]->x` で `T` のメンバを読み書きできます。
- `a[i]->x = v`、`a[i].f[j] = v` のように、配列の要素から続く左辺に代入できます。
- `*Type` のフィールドの先を読み書きできます: `info->pkh->com_size`、メソッドの中の `tbl[i].hash` / `tbl->size`。これまではフィールドがクラスを指すときだけでした。後ろで定義する `Type` を指すフィールドにも使えます。
- `Type` / `Class` のフィールドにある関数ポインタを呼べます: `p->rom.init_cb(h)`、`obj->fp(x)`。戻り値は `Long` の幅として読みます。
- `TypeDef F = *Function(...)` を後ろに書いても、前の手続きの仮引数 `f As F` を `f(...)` と呼べます。

不具合の修正:

- 関数ポインタの `TypeDef` 型のフィールドを持つ `Type` の大域変数があると、`-actba32` でコンパイラが落ちることがありました（落ちないこともありました）。関数ポインタの型が仮引数の情報をフィールドの欄に入れていたためで、別の欄に分けました。
- `Beep(周波数, ミリ秒)` を kernel32 の `Beep` API の呼び出しとして読みます。引数の無い `Beep` 文はこれまでどおりです。
- 中身の無い `#include` ファイルを「開けません」にせず、空のファイルとして読みます。

### ActiveBasic との違い

- 関数のアドレスやポインタを `DWord` で持つ 32bit 前提のソースは64bit で作ると起動の後に落ちるので、`-actba32` で作ってください。
- AB 4 の vtable を書き換えるプログラムは、メソッドの先頭に `This` を受ける捨て引数 `_this As VoidPtr` を置いています。ActBa64 は `This` の渡し方が違うので、そのままでは引数が 1 つずれます。捨て引数を消してください（[different.md](./different.md#動作が異なるもの)）。

### Include

- `api_user32.sbp` に `IsDialogMessage`（`IsDialogMessageA` / `IsDialogMessageW`）を足しました。`IsDialogMessage` は `W` です。
- `ab_listview.sbp` に `LVN_KEYDOWN` を足しました。

### ProjectEditor

- `#USEWINDOW=1` のプロジェクトで、`.wnd` から `Callback.wbp` / `MakeWindow.wbp` を作ります（上のハイライト）。
- 開いた文書とプロジェクトのパスを UTF-8 にそろえました。CP932 のパスが、保存の確認などで化けていました。

### サンプル

- `src/actba64/samples/viewer` に、PDF の表示に使う `pdfium.dll` を入れました。

### テスト

- 回帰テスト `test/t_ab4_hkac.abp`、`test/t_ab4_lspk.abp`、`test/t_long_string_lit.abp` と、ユニットテスト `RadGenTest` を足しました。

## v0.1.3（v0.1.2 からの変更点）

### ハイライト

- **COM インターフェースを継承して中身を書く Class を作れます。** 中身の無い `Virtual` だけの Class を `Inherits` し、本体のある `Sub` / `Function` を書くと実体の Class になります（先頭に `__vptr`）。vtable は `AddressOf(obj->Method)` を並べてプログラムが作ります。AB4 のサンプルのように、1 つのポインタ変数で違うクラスのメソッドを呼べます。
- **基底クラスのポインタで `Delete` しても、`New` した実体のクラスの Dtor が呼ばれます。**
- **サンプルを 2 つ足しました。** 2 台目のモニターに画像と PDF を映すビューアー（`src/actba64/samples/viewer`）と、二人で指す将棋（`src/actba64/samples/shogi`）です。

### コンパイラ

- `Class A : Inherits B` と 1 行に書けるようにしました。
- `AddressOf(obj->Method)` / `AddressOf(obj.Method)` で、`obj` のクラス（か継承元）のメソッドの番地を取れます。
- `SizeOf(*型)`（`SizeOf(*Function)` も）はポインタの幅（64bit は 8、`-actba32` は 4）になります。
- 中身の無い `Virtual` の Class を継承して本体のある `Sub` / `Function` を書いた Class は、COM インターフェースでなく実体の Class にします。これまでは空の ctor が付かず、`New` が `missing ctor` になっていました。
- `New` の塊の頭を 8 バイトから 24 バイト（要素の大きさ・Dtor の番地・要素数）にしました。`Delete` は頭の Dtor を呼ぶので、基底クラスや COM インターフェースのポインタで消しても実体の Dtor が呼ばれます。Dtor の見つからない `Delete` の `missing dtor` のエラーは無くなりました。
- ポインタ越しに呼ぶメソッドの `Long` の引数へ `Double` の式を渡すと 0 が渡っていたのを直しました。
- `arr[i] = udt.rc` のように、入れ子のメンバーから配列の要素へ構造体を代入すると違う値が写っていたのを直しました。

### ActiveBasic との違い

- AB4 はメソッドの `This` を ECX で渡し、宣言だけの `Virtual`（COM）の呼び出しでは `This` をスタックの第1引数にも積みます。ActBa64 は `This` を第1引数で渡します。AB4 で vtable に入れるメソッドの先頭に `This` を受けるための捨て引数（`dummy As Long`）を置いていたソースは、捨て引数を消してください。vtable やオブジェクトの先頭を `DWord` / `SetDWord` で扱うと 64bit ではアドレスが切れるので、`*VoidPtr` と `SizeOf(*Function)` を使ってください。詳しくは [different.md](./different.md#動作が異なるもの) を見てください。

### サンプル

- `src/actba64/samples/viewer`: Lazarus の ViewerBy2nd を `Forms.sbp` で書き直したビューアー。画像（GDI+）と PDF（pdfium.dll）を操作画面で選び、スクリーンの窓に映します。ページ送り、拡大・縮小、回転、背景表示、自動表示、全画面、モニターの選択に対応します。動画と設定の保存はまだです。Windows の 64bit のみで、exe と同じフォルダに 64bit の pdfium.dll が要ります。
- `src/actba64/samples/shogi`: 盤と駒台を GDI で描き、押した場所で駒を動かす・持ち駒を打つ将棋。成りは尋ね、行き所が無ければ自動で成ります。王手・詰みの判定はしません。Windows のみです。

### Include

- `-linux` の Forms の長いファイルを役目ごとに分けました（`FormX11` / `FormEvent` / `FormPaint` / `FormInput` / `FormEdit` / `X11Font` / `MsgBoxEvent`）。Forms の手続きはすべて 10 行以内にしました。動きは変わりません。

### ビルド・その他

- README のコマンドラインに `-X` を載せました。

## v0.1.2（v0.1.1 からの変更点）

### ハイライト

- **ProjectEditor が Linux（X11）で動きます。** 文書の編集・保存、メニュー、ファイル選択、検索、プロジェクトの欄、クリップボード、訳す・実行する、フォームデザイナまで使えます。Linux 版の一式は `release_build.sh` で作ります。詳しくは [projecteditor.md](./projecteditor.md) の「14. Linux 版」を見てください。
- **`-linux` の Forms が窓に部品を描き、押せるようになりました。** フォームデザイナで作ったフォームを Linux でもそのまま動かせます。`MsgBox` も X の窓で出ます。
- **フォームの部品が増えました。** `CheckBox` / `RadioButton` / `EditBox` / `GroupBox` を足し、デザイナのツールボックスから Label も含めて置けます。

### コンパイラ

- 同じ行で文の後ろに `:` なしで語が続くと `expected end of statement` のエラーにします（AB 4.20 と同じ）。`-pAB2` では AB 2.62 と同じく行の残りを捨て、`-pN88` では調べません。これまでエラーにならずに通っていたソースは、`:` を入れるか行を分けてください。
- String の GC の表を伸ばせるようにしました。これまでは 4096 個を超えて確保した塊が表に載らず、二度と解放されませんでした。GC 領域は約 38KB から約 2KB になりました。
- String の GC が大域変数・スタックの印を付けていなかったのを直しました。`Dim keep(1000) As String` の `keep(492)` 以降などが、生きているのに回収されていました。
- 大文字小文字だけ違う `Const` が、同じ名前のローカル変数・引数・大域変数を置き換えていたのを直しました（変数が勝ちます）。
- 手続きの中で足した大域変数も `.data` の大きさに入れるようにしました。
- `unknown API` など低レベル化で出るエラーに `ファイル(行)` を付けました。ProjectEditor でエラーの行へ飛べます。
- Linux で動くコンパイラは、出した ELF に実行の許可（`rwxr-xr-x` から umask を引いたもの）を付けます。

### N88BASIC / ActiveBasic2

- `-pN88` で `DATA` / `READ` を使えます。実行時の関数は `Include\Data` に移しました（`-pN88` / `-pAB2` のときだけ読みます）。
- `-pAB2` で、最初の文が行番号で始まるソースは `-pN88` と同じく読みます（AB2 の `#N88BASIC` のプログラム）。
- `-pN88` の `LINE ...,BF,color2` で中を `color2` で塗ります。`COLOR = (p, &Hgrb)` でパレット 0〜15 の色を変えられます。既定のパレットの 8 は灰、9〜15 は 1〜7 の少し暗い色です。

### Include

- `Forms.sbp` の中身をクラスごとに `Include\Forms\*.sbp` へ分けました（`Forms.sbp` を取り込むのはこれまでどおりです）。
- `CheckBox`（`Checked` / `GetChecked` / `SetChecked`）、`RadioButton`（フォームのラジオボタンは 1 つの組）、`EditBox`（`GetText` / `SetText`）、`GroupBox` を足しました。押すと Button と同じく `WM_COMMAND`（`BN_CLICKED`）が届きます。

### ProjectEditor

- Linux 版を足しました（X11 + FreeType）。窓 1 枚にメニューの帯・文書のタブ・文書・メッセージ欄を並べます。
  - メニューの帯と右クリックのメニューは自前で描きます。Alt+文字・矢印キー・Enter・Esc で選べます。
  - ファイルを開く・保存のダイアログ、検索（Ctrl+F / F3 / Shift+F3）、設定（言語）を自前のダイアログで出します。
  - X の CLIPBOARD でほかのアプリとコピー・貼り付けができます。
  - `.pj` を開くと左に `#SOURCE` の一覧を出します。
  - Basic メニューの訳し先に「Linux (ELF)」を足しました（Linux 版の既定）。コンソールのプログラムは端末（`$TERMINAL` か `x-terminal-emulator` など）で動かし、端末が無ければ出力と終了コードをメッセージ欄に出します。
  - 実行はエディタと同じ OS の訳し先のときだけで、ほかは訳して「ここでは実行できない」と出します。
- フォームデザイナのツールボックスを、見出し「Toolbox」と組「General」の下に Pointer と各部品をアイコン付きで並べる形にしました。Pointer を押すとツールの選びが外れます（Esc と同じ）。
- ツールボックスに CheckBox / RadioButton / EditBox / Label / GroupBox を足し、デザイン画面でそれぞれの見た目を描きます。
- 同梱していた UDEV Gothic をやめ、OS のフォントを使います。Windows 版は MS Gothic、Linux 版は IPA ゴシック・Takao ゴシック・DejaVu Sans Mono・Liberation Mono・FreeMono のうち最初に見つかったものです。
- F1 ヘルプを language.md に合わせました（New / Delete / Super、Protected、GoTo / GoSub、Int64、`#resource` などを未対応としていたのを直しました）。

### -linux

- Forms の Button / CheckBox / RadioButton / EditBox / Label / Panel / GroupBox を窓に描きます（文字は `libfreetype.so.6` と OS のフォント）。押して離すと `WM_COMMAND`（`BN_CLICKED`）、EditBox は文字が変わると `EN_CHANGE` を送ります。部品の上のクリックと部品が受けたキーはフォームの `WndProc` に届きません（Windows の子窓と同じ）。
- Forms を使うプログラムの `MsgBox` / `MessageBox` は X の窓になりました（`MB_OK` ほか 6 つのボタンの組、`MB_DEFBUTTON2` / `3`、Enter / Esc / Tab / ←→）。閉じるまでほかのフォームの入力を止めます。X につながらなければこれまでどおり標準エラーに書きます。
- Forms の `WM_KEYDOWN` に F1〜F12、Home / End / PageUp / PageDown、Insert / Delete、Shift / Ctrl / Alt、テンキーを足しました。
- 窓の大きさを変えたときと閉じたときに XImage を解放します。
- `CreatePipe` / `CreateProcessA`（標準入出力のつなぎ替え・作業フォルダー）/ `GetEnvironmentVariableA` / `GetTempPathA` / `ShellExecuteA`（`xdg-open`）/ `lstrcmpiA` の Linux 版を足しました。

### ビルド・その他

- GitHub Actions の CI（Windows）を足しました。手元では `ci.ps1` で同じ手順を回せます。
- Linux 版のリリースを作る `release_build.sh` を足しました（`--tar` で tar.gz も作ります）。
- ANSI コードページが 932 でない機械では、CP932 のバイトを前提にしたユニットテストを飛ばします。
- String の GC の配置が変わったので、stage0 が古いと `build.ps1` の stage1 / stage2 の比較が一致しません（stage2 → stage3 は一致します）。AB 4.20 で stage0 を作り直してください。
- MIT の LICENSE を足しました。日本語訳と自作プログラムの配布条件は `docs/` にあります。README に非公式である旨を書きました。

## v0.1.1（v0.1.0 からの変更点）

### ハイライト

- **ProjectEditor にフォームデザイナが付きました（RAD の第一段階）。** 「新しいフォーム」でフォームを作り、ツールボックスから Button / Image / Panel を置き、Button をダブルクリックするとクリックの処理を書けます。「コード」「デザイナー」のタブか F12 で切り替えます。
- **`Forms.sbp` の部品が増えました。** `Control` / `Button` / `Label` / `PictureBox` と `Form.AddControl`、`OpenFileDialog` を使えます。
- **`-linux` で N88BASIC（`-pN88`）のプログラムが動きます。** X につながれば 640x480 の窓に描き、つながらなければ端末で文字だけ出します。

### コンパイラ

- コンパイラのメッセージを英語に揃えました（これまで「無効な識別子です。」など一部が日本語）。`actba64.exe` と同じフォルダに `actba_lang_ja.csv` があると日本語で出します（リリース一式には入っているので、英語にしたいときは消してください）。メッセージは ID で管理し、CSV は ProjectEditor の言語パックと同じ `id,text` です。詳しくは [build.md](./build.md#メッセージの言語) を見てください。
- `Ex"..."` で AB 4.20 の `\q`（`"`）と `\xhh`（16 進 2 桁の文字コード）を使えるようにしました。
- `src/common/StringFormat.abp` に `StringFormat("{0} message {1}", a, b)` を足しました（引数は String を 5 個まで）。
- `Str$` の結果が、String の GC にほかの生きた String を掃き出させることがあったのを直しました。`Str$` は塊の後ろに数字を置き、塊の先頭の 4 バイトを書かずにいたので、GC が古いヒープのゴミを長さとして読み、その範囲に入るポインタの印を横取りしていました（ProjectEditor で新しいフォームを作って終了すると、保存を尋ねる画面のパスがソースの 1 行になり、「はい」でも保存に失敗しました）。
- `MsgBox "文字列"` のように引数が 1 つでもコンパイルできます（hWnd は 0）。
- クラスのメソッドの中で、`p As *Foo` のフィールドに `p->M()`・`Delete p`・`p[i]` を使えるようにしました。これまでは `method call on non-class` / `Delete needs a class pointer` のエラーになり、`p[i]` は 1 バイトずつ進んでいました。
- メッセージのパスを UTF-8 にそろえました（日本語の訳と CP932 のパスが混ざり、ProjectEditor で文字化けしていました）。`actba_lang_ja.csv` は CP932 で保存したもの（BOM 付きも）を読みます。256 バイトで切る診断が UTF-8 の文字の途中で切れないようにしました。
- AB 4.20 でビルドできるように、メッセージの文から `""` をなくしました（出力は変わりません）。

### Include

- `Forms.sbp` に `Control` / `Button` と `Form.AddControl` を足しました。`InitializeComponent` で `AddControl` した部品は、フォームの窓ができたときに子窓になります。Button の押下は親の `WndProc` に `WM_COMMAND` / `BN_CLICKED` で届きます。
- `Forms.sbp` に `Label`（STATIC）、`PictureBox`（`SetBitmap`）、`Control.SetCaption` / `SetBounds` / `Enabled` / `SetEnabled`、`Form.SetCaption`、`OpenFileDialog`、`ExtractFileName` を足しました。詳しくは [language.md](./language.md) の「7.8 フォーム（Forms.sbp）」を見てください。
- `InitializeComponent` はフォームの ctor ではなく最初の `Show` で 1 度だけ呼びます（メンバの Class の ctor が、入れた値を上書きしていたため）。窓を出す前に値を読みたいときは `InitComponents()` を呼んでください。
- Win32 の構造体の 16bit のメンバを `Integer` から `Word` にしました（`BITMAP` / `BITMAPINFOHEADER` / `DEVMODE` / `CHARFORMAT` / `PARAFORMAT` / `SYSTEM_INFO` / `HOSTENT` / `SERVENT`）。このコンパイラの `Integer` は 4 バイトなので大きさが違い、`CreateDIBSection` などが失敗していました。`BITMAPFILEHEADER` も 14 バイトにしました。
- `Trim$` を `Include\default` から `src/common/StrTrim.abp` に移しました（AB 4.20 に `Trim$` は無いため）。使うときは `StrTrim.abp` を取り込んでください。

### ProjectEditor

- フォームデザイナ（RAD の第一段階）を足しました。`InitializeComponent` のある文書で F12 を押すとデザイン画面になり、窓の右辺・下辺・右下を引くと `Width` / `Height` の行を書き換えます。もう一度 F12 でソースに戻ります。詳しくは [projecteditor.md](./projecteditor.md#12-フォームデザイナ) を見てください。
- 名前を付けて保存の既定の拡張子を `.sbp` から `.abp` にしました。`.abp`（Active Basic Program）はメインのコード、`.sbp`（Sub Basic Program）は `#include` で読むファイルです。ファイルダイアログのフィルタも `*.abp` を先にしました。
- フォームデザイナの左にツールボックス（Button / Image / Panel）を足しました。ツールを選んで窓を押すと、フィールドの `名前 As 型` と `InitializeComponent` の位置・大きさ・`AddControl` の行を書き足します。部品はフィールドの型で描き分けます（[projecteditor.md](./projecteditor.md#12-フォームデザイナ)）。フィールドはメソッドより前の `Private` に書きます（新しいフォームで `WndProc` の後ろに書いてコンパイルできなかったのを直しました）。
- ファイルメニューに「新しいフォーム」を足しました。プロジェクトを開いていなければ、まず一時フォルダー（`%TEMP%\ActBa64Temp\NewN\`）に `project1.pj`・`project1.abp`（メイン）・`Form1.abp` を書き（保存先は上書き保存・名前を付けて保存か終了のときに尋ねて、そこへ移します）、開いていれば `FormN.abp` を書いて `#SOURCE` に足します。書いたフォームはそのままフォームデザイナで開きます。N88BASIC構文・ActiveBasic2構文のときは灰色です。
- 無題の文書の実行・コンパイルは、N88BASIC構文・ActiveBasic2構文のときだけでなくいつも、保存先を尋ねずに `%TEMP%\ActBa64Temp\untitled.abp` に書いて訳すようにしました（これまでの `%TEMP%\ActBa64N88\` から変えました）。
- ソースの子ウィンドウの上に「コード」「デザイナー」のタブを足しました。押すとソースとフォームデザイナが切り替わります（F12 と同じ）。
- フォームデザイナで Button をダブルクリックすると、`Sub Button1Click()` と、それを呼ぶ `WndProc` の行（`WM_COMMAND` / `BN_CLICKED`）を書き足し、コードの画面でその `Sub` の中にキャレットを置きます。
- N88BASIC構文（`-pN88`）のとき、`REM` から行末をコメントの色にします。

### -linux

- N88BASIC構文（`-pN88`）のプログラムを ELF にできます。X につながれば `libX11.so.6` で 640x480 の窓を開き、文字・`LINE`・`CIRCLE`・`PSET`・`PAINT` を描き、`INPUT` / `INKEY$` / `INPUT$` は窓のキーを読みます。X につながらなければ端末で `PRINT` / `INPUT` / `INKEY$` / `INPUT$` / `LOCATE` / `COLOR` / `CLS` を動かします（図形は描かず、標準エラーに 1 回知らせます）。
- `.so` を呼ぶときにスタックを 16 バイトにそろえます（式の途中の呼び出しで libX11 が落ちていました）。
- `Forms.sbp` の `AddControl` などは通りますが、子窓は作らず値を覚えるだけです。`OpenFileDialog.Execute` はいつも False です。
- `.so` の `Declare Function ... As Double` / `As Single` の戻り値を受け取ります（`sqrt` / `pow` など。Windows の DLL も同じ）。これまでは戻り値の型を読み捨てていました。
- `.so` の関数へ `AddressOf(f)` を直に渡すと、BASIC の関数を `.so` から呼べます（`qsort` の比較関数など。整数・ポインタの引数 6 個まで）。
- `.so` を使う（動的な）ELF は、終わるときに libc の `exit` を呼ぶので、改行の無い `printf` なども書き出されます。
- `MsgBox` が使えます。窓は出さず、「見出し: 本文」を標準エラーに 1 行で書き、最初のボタン（`MB_OK` なら `IDOK`、`MB_YESNO` なら `IDYES`）を押したことにします。これまでは `unsupported API: MessageBoxA` で終わっていました。

## v0.1.0（v0.0.9 からの変更点）

### ハイライト

- **`Int64` / `QWord` が 64bit の整数になりました（64bit 出力と `-linux`）。** これまでは `Long` / `DWord` として読み、警告を出していました。詳しくは [different.md](./different.md) を見てください。
  - 変数・仮引数（値・ByRef）・Type メンバ（配列のメンバも）・配列（多次元、`= [...]` の初期化子）が 8 バイトです。`SizeOf` / `Len` も 8 バイトで数えます。
  - `+ - * \ Mod And Or Xor Not << >>` と比較、`If x Then`、`For` の制御変数（終値・Step も）、`Select Case` が 64bit です。
  - `Function` / Class のメソッド / `Declare Function` / 関数ポインタの `As Int64` / `As QWord` の戻り値も 64bit です（`GetTickCount64` など）。仮引数が `Long` と `Int64` だけ違う関数も重ねて定義できます。
  - Long は符号で、DWord と 4294967295 までの整数のリテラルは 0 で広げます。Int64 を Long へ入れると下位 32 ビットです。Double とは 0 へ切り捨てで変換します。
  - `Print` / `Print #` / `Write #` / `Str$` は 64bit の十進で出します（`Include\default\Int64Str.abp` の `StrI64$` / `StrU64$`）。`Hex$` / `Oct$` も 64bit、`Input` / `Input #` は 64bit の十進を正確に読みます。
  - `Const BIG = 5000000000` は Int64 の定数です。`x As Double` / `As Single` / `As Long` のキャストも 64bit から変換します。ポインタ（`VarPtr`、`*T`、`VoidPtr`）を Int64 へ入れても 64bit のままです。
  - `ByRef` の Int64 / QWord の仮引数へは 64bit の変数・メンバ・要素だけを渡せます（Long を渡すとエラー）。
  - QWord: 両辺とも符号なし（QWord・DWord・非負のリテラル）の `\` `Mod` と比較は符号なし、QWord の `>>` は論理シフトです。Double との変換は 2^63 以上も正しく扱います。
- **64bit の整数リテラル。** 4294967295 を超える十進（`9223372036854775807` まで）と 9〜16 桁の `&H` は Int64 のリテラルです（これまでは Double、または 32bit に切り詰め）。

### 修正

- 66 文字以上の文字列リテラルを `+` でつなぐとコンパイラが落ちていました。定数の文字列の畳み込みが 64 バイトの配列へ写していたためです。畳み込んだ定数が 63 文字で切れていたのも直しました（`Left$("…" + "…", 100)` など）。名前を写す所もすべて 64 バイトで止めます（`AstCopyName`）。
- `Print Using` で 2^31 以上の値が `0000000000` などになっていました。整数部を `Fix`（Long）で取っていたためで、Double のまま切り捨てます。

### 互換性

- `-actba32` では、これまでどおり `Int64` を `Long`、`QWord` を `DWord` として読み、警告を出します。
- `Val` は Double を返す（ActiveBasic と同じ）ので、Int64 へ入れる値は 2^53 まで正確です。

### ビルド

- 新しいコンパイラは `_INT64` を定義し、`Include\default\Int64Str.abp` はそのときだけ読みます（Int64 を Long と読む古いコンパイラでは `Hex$(n As QWord)` が Long の版と重なるため）。古い stage0 では `build.ps1` の stage1 / stage2 の比較が一致しません（stage2 → stage3 は一致します）。AB4.20 で stage0 を作り直してください。

## v0.0.9（v0.0.8 からの変更点）

### ハイライト

- **`-X` で exe が小さくなります。** 呼ばれない関数・メソッドと、そこからしか呼ばない API を exe に入れません（Hello World 64bit: 185KB → 50KB）。ProjectEditor の Basic メニュー「使用していない命令を削除(-X)」でも入り切りできます。詳しくは [language.md](./language.md) と [projecteditor.md](./projecteditor.md) を見てください。
- **大域変数の `.data` をファイルに持たなくなりました（BSS）。** Hello World は 185KB → 144KB、`-X` と合わせると 9KB です。
- **`Forms.sbp` が `-linux` で X11 の窓になります。** 同じソースを ELF にでき、`libX11.so.6` を呼びます（X サーバーが要ります。WSL なら WSLg）。`Form.Close()` も追加しました。詳しくは [language.md](./language.md) の「7.8 フォーム（Forms.sbp）」を見てください。

### 言語

- **多次元配列の並びを ActiveBasic・C と同じにしました。** `Dim a(N, M)` の `a(i, j)` は `i * (M + 1) + j` 番目で、最後の添字が連続します。`VarPtr(a[i, 0])` から `a[i, 0..M]` を続けて読めます。
  - 多次元配列を平坦な添字 `a(k)` で読むと、`bad array index count` のコンパイルエラーになります。次元数と違う個数の添字も同じです。
- 配列・ポインタの添字に Double / Single を書けます（`a[(i + j) / 2]`）。Long に変換します。
- `VarPtr(a[i, j])` / `VarPtr(a(i, j))` を読みます。
- 多次元の UDT 配列のメンバを読み書きできます（`a(i, j).x = 10`、`Print a[i, j].x`、`With a(i, j)`）。並びは他の多次元配列と同じで、次元数と違う個数の添字はエラーです。
- `TypeDef X = *T` の別名で `Dim` した変数は `*T` と同じ型になります（`Dim d As DWordPtr` の `d[i]`）。
- `Print Using fmt; a, b, ...` で複数の値を出せます。書式は値ごとに前から当てはめて繰り返します。N88-BASIC の書式 `+` `-` `**` `\` `,` `^^^^` `!` `_` を読み、入らない数には `%` を付けます。
- 指数のリテラル（`1.5e10`、`2.5E-3`、`1E+3`）を読みます。4294967295 を超える十進の整数リテラルは Double になります（これまでは 32bit に切り詰めていました）。
- DWord の変数・仮引数・Type メンバを Double にするとき、符号なし（0..4294967295）として読みます。
- `#strict` で Byte を Long に代入しても警告しません。

### 修正

- `A() + B()` のように、名前が `$` で終わらない `As String` の関数どうしを足すと落ちていました。文字列の連結にします。
- Byte 配列（変数・Type メンバ）と文字列の比較（`If FileName = "" Then` など）が正しくありませんでした。C 文字列として比べます。
- 2^31 を超える Double の `Print` / `Str$` が `inf` になっていました。10^15 未満は整数部をそのまま、それ以上は `1.5E+20` の形で出します。
- `LoadImage`（`LR_LOADFROMFILE`）で日本語を含むパスのビットマップを開けませんでした。UTF-8 のパスを `LoadImageW` へ渡します。
- `ReadFile` / `WriteFile` のバイト数の受け取り先と `lpOverlapped` を `VoidPtr` にしました。64bit でアドレスが 32bit に切り詰められていました。コンパイラと ProjectEditor のビルドの警告が 0 になります。

### Include

- `Const RAND_MAX = &H7FFF` を追加しました。

### ProjectEditor

- 「使用していない命令を削除(-X)」を Basic メニューに追加しました。題名に `-X` が付きます。
- DLL を出力する `.pj` では、実行メニューを灰色にします。

### ビルド

- PE の書き出しが変わったので、古い stage0 では `build.ps1` の stage1 / stage2 の比較が一致しません（stage2 → stage3 は一致します）。AB4.20 で stage0 を作り直してください。

## v0.0.8（v0.0.7 からの変更点）

v0.0.7 のコンパイラを、自分自身をコンパイルできる状態に戻す修正です。

### 修正

- AB4.20 で作った stage0 から始めるブートストラップで、stage1 が自分自身をコンパイルする途中にスタックあふれで止まっていました。
  - 原因は、v0.0.7 で変えた `Str$` の処理が `And` の短絡を前提に書かれていたことです。AB4.20 は `And` の両辺を評価するので、stage0 は Long の `Str$` にも Double / Single 用のコードを出していました。
  - 条件を `If` の入れ子に書き直しました。直したソースは、自分自身をコンパイルすると同じバイナリになります。
  - ソースからビルドする人は、AB4.20 で stage0 を作り直してください。

## v0.0.7（v0.0.6 からの変更点）

ActiveBasic 2.62 のソースを読む `-pAB2` モードを追加しました。`-pN88` で読める N88-BASIC の範囲も広げています。どちらも、ユーザーのソースを書き換えずにコンパイルできることを目標にしています。

### ハイライト

- **ActiveBasic 2.62 のソースをコンパイルできます。** `-pAB2` を付けると、ActiveBasic 2.62 のソースとして読みます。詳しくは [language.md](./language.md) の「1.8 ActiveBasic 2.62 構文（-pAB2）」を見てください。
  - 構文: `Field #n` と `Get` / `Put #n` によるランダムアクセスファイル、`Lof(#1)`、`Data` / `Read`、`On Error Goto`（読み飛ばします）を読みます。`ClipStr$`、`CmdLine$`、`CurDir$` は括弧なしで書けます。`3.14#` は Double の印として読みます。
  - 窓: `Window` 命令の "NORMAL" 窓、`GetWndMsg` によるメッセージ待ち、`SendWndMsg`、`ShowWnd` / `WndPos` / `OwnerWnd` を使えます。`Window` に窓プロシージャを渡すと、メッセージをそのプロシージャへ送ります。
  - そのほか: クリップボード、`KLen` / `KMid$`、`SelectPrinter` / `LPrint` を使えます。
  - 引数: ユーザーのソースで `ByVal` / `ByRef` を書かない引数は、AB2 と同じく `ByRef` になります。
  - 確かめたプログラム: MorseEncoder2000 と、RAD ツールの TkyWgs をコンパイルして動かしました。
- **ProjectEditor で -pAB2 を選べます。** Basic メニューの「ActiveBasic2構文(-pAB2)」で切り替えます。
  - 「N88BASIC構文(-pN88)」とは同時に選べません。
  - 保存していない新しい文書のままでも実行できます。
- **Class で中身のある `Virtual` と `Override` を使えます。** 窓を Class として書ける `Forms.sbp` も追加しました。詳しくは [language.md](./language.md) の「3.3 Class」と「7.8 フォーム（Forms.sbp）」を見てください。

### Class

- 中身のある `Virtual` Sub / Function を書き、子の Class で `Override` して差し替えられます。
  - 呼び出しは vtable を通るので、`obj.M()`、`p->M()`、メソッドの中の `M()` のどれでも子の版が呼ばれます。基底の ctor の中から呼んでも子の版が呼ばれます。
  - 親に `Virtual` が無いのに `Override` を書くと、コンパイルエラーになります。
  - 親の `Virtual` と同じ名前のメソッドを `Override` なしで書くと、コンパイルエラーになります。
  - 中身の無い `Virtual` 宣言だけの Class は、これまでどおり COM インターフェースとして扱います。
  - 最初に `Virtual` を持つ Class は、ほかの Class を `Inherits` できません。
- 基底の ctor / dtor を自動で呼びます。
  - ctor は「基底の ctor → メンバの ctor → 本体」、dtor は「本体 → メンバの dtor → 基底の dtor」の順に呼びます。ctor / dtor を省略したときも同じです。
  - 本体に `Super.Parent(...)` / `Super.~Parent()` を書いたときは、自動では呼びません。
  - 基底に引数なしの ctor が無いのに `Super.Parent(...)` を書かないと、コンパイルエラーになります。
- フィールドの無い Class も `Dim` / `New` できます。これまでは「Dim UDT size 0」のエラーになっていました。

### Forms.sbp

- `#include <Forms.sbp>` で、窓を `Form` クラスの子として書けます。
  - `Form` は `Left` / `Top` / `Width` / `Height` / `Caption` / `Handle` を持ちます。
  - ctor が `InitializeComponent()` を呼ぶので、子は `Override` して値を入れます。
  - メッセージは `WndProc(msg, wParam, lParam)` に届きます。子は `Override` し、扱わないメッセージを `Super.WndProc` へ渡します。
  - `Application.Run(form)` は窓を出し、閉じるまでメッセージループを回します。
- サンプル `src/actba64/samples/forms/`（`project1.abp` と `Form1.abp`）を追加しました。

### -pN88（N88-BASIC 構文）

- `INPUT` 文を読めるようになりました。
- `CONSOLE ,,,1` のように、命令の引数を省いて書けます。
- 1 行の `IF` を読めるようになりました。読める形は次のとおりです。
  - `IF 条件 THEN 文:文 ELSE 文`
  - `IF 条件 THEN 行番号`
  - `IF 条件 GOTO 行番号`

### N88BASIC の窓

`#N88BASIC`、`-pN88`、`-pAB2` で共通の変更です。

- `Input x` のように問いかけの文字列がないときは、`? ` を出してから入力を待ちます。
- 入力中は、入力位置でカーソルが点滅します。

### 修正

- `Str$` に Double / Single を渡すと、整数として変換していました。いまは `Print` と同じく実数の文字列になります。これまでは `Str$(0.1)` が `-1717986919` になっていました。
- 実数リテラルを Double の精度で読むようになりました。これまでは小数部を 9 桁で打ち切っていたので、`0.0000000001` が 0 になっていました。
- `.5` のように先頭の 0 を省いた小数を読めるようになりました。
- `Atn` と `Sqr` を Double の精度で計算するようになりました。これまでは `Atn(1)` が π/4 から 0.0125 ずれていました。
- 同じ名前の関数を引数の型で呼び分けるとき、String の変数や式を渡しても String の版を選ばないことがありました。いまは String の版を選びます。
- `Chr$` に Double の式を渡すと `Chr$(0)` になっていたのを直しました。
- `ByRef` の引数に変数以外を渡すと黙って失敗していました。いまは、その行を示してエラーにします。
- 手続きの中の構文エラーを、間違った行番号で報告することがありました。いまはエラーのあった行で報告します。
- `#include <windows.sbp>` のように `Include\default` のファイルを書いても、二重に読まなくなりました。
- 64bit で、32bit 用の大きさを入れた `OPENFILENAME` / `CHOOSEFONT` を渡しても、ファイルとフォントのダイアログが開きます。
- ステータスバーの日本語が文字化けしなくなりました。

### サンプル・ドキュメント

- `src/actba64/samples` に次のサンプルを追加しました。
  - `MovingReversiGui.abp`: 動くリバーシの GUI 版です。盤と手の処理はコンソール版と共有しています。
  - `AltBPause.abp`: Alt + B を押すと Pause キーを送ります。
  - `circle.sbp`: N88BASIC 構文で円を描きます。
- [language.md](./language.md) の `#USEWINDOW` の説明を直しました。`#USEWINDOW` は `.pj` に書いたときだけ効きます。GUI で画面への `Print` を使っても表示されないことも書き足しました。
- 古いプロトタイプ（`src/prototype1`〜`4`）を削除しました。
- [index.md](./index.md) に、動かないコードの報告先（GitHub Issues）を書きました。

## v0.0.6（v0.0.5 からの変更点）

Linux 向けの実行ファイルを作れるようになりました。また、ActiveBasic 4 の書き方への対応を大きく広げ、既存のプログラムをそのままコンパイルできる範囲が増えています。

### ハイライト

- **Linux で動く実行ファイルを作れます。** `-linux` を付けると、x86-64 Linux の ELF を出力します。libc を使わずカーネルを直接呼ぶので、そのまま実行できます。コンソール入出力、ファイル、メモリ、時刻、`Sleep`、コマンドライン、子プロセスが使えます。
  - `Declare` の `Lib` に `libc.so.6` のような共有ライブラリを書くと、その関数を呼べます（`printf` のような可変長引数の関数も呼べます）。
  - Linux 版のない Windows API を呼んでいると、呼んだ行を示して警告します。
  - 使われない関数は出力に含めないので、Hello World は約 29KB です。
- **コンパイラ自身を Linux で動かすこともできます。** `actba64.pj` を `-linux` でコンパイルすると Linux 版のコンパイラができ、Windows 版と同じ実行ファイルを出力します。
- **ActiveBasic2.62以前のコード対応** `-pN88` を付けると、行番号付き・`Dim` なしの N88-BASIC のプログラムをコンパイルします。ProjectEditor では Basic メニューの「N88BASIC構文(-pN88)」で切り替えます。-pN88の場合は保存していない新しい文書のままでも実行できます。
- **関数のオーバーロード。** 同じ名前で引数の数や型が違う `Function` / `Sub`、メソッド、コンストラクタを定義でき、呼び出しの引数で呼び分けます。

### 言語・コンパイラ

**新しく使えるようになったもの**

- 型:
  - `Type X Pack(n)` と `Type Align(n) X` で、フィールドを n バイトに詰められます。
  - `TypeDef` と `Enum` を、使う場所より後ろで定義できます。`Enum` の値は `,` で区切っても書けます。
  - `Type` のフィールドの要素数に、`Title[N_TITLE - 1]` のような定数式を書けます。
  - `Const X As Long = 3` のように、型を付けた `Const` を書けます。手続きの中にも `Const` を書けます。
  - `&H10&` のような、末尾に `&` の付いた 16 進数を読みます。
  - 型の位置の `Char` は `Byte` として読みます。
  - `QWord` / `Int64` は 32bit の整数（`DWord` / `Long`）として読み、警告を出します。
  - `Declare` の `ByRef x As Any` は、渡したものを何でもアドレスで渡します。
- クラス:
  - 後ろで定義するクラスや型を、フィールドとして値で持てます。
  - メソッドの中で、ポインタのフィールドに添字を付けて読み書きできます（`tbl[2] = ...`）。
  - `Get` / `Set` という名前のメソッドを定義できます。
  - 関数ポインタのフィールドを呼べます。メソッドの中で `AddressOf` を使えます。
  - メソッドで Double の引数と戻り値を使えます。
  - 後ろで定義するクラスを `Dim` で使えます。
- ポインタ:
  - `*Double` / `*Single` / `*Word` / `*BytePtr` に添字を付けると、要素の大きさごとに進み、要素の型で読み書きします。
  - `h.Raw.GameID[i]` や `p->Raw.GameID[i]` のような、入れ子のメンバの配列を読み書きできます。
- 構文:
  - `Else If`（空白あり）を `ElseIf` と同じに扱います。
  - `ExitDo` / `ExitFor` / `ExitWhile` / `EndType` のように、空白なしの書き方も受け付けます。
  - 文末の `;` を受け付けます。
  - `Debug` 文を受け付けます（実行ファイルでは何もしません）。
  - `x As Long` のような型変換を、式の中に書けます。
  - 配列の初期化子 `Dim t[2] = [1, 2, 3] As DWord` を、`Word` / `Byte` / `BytePtr` でも使えます。最後の要素の後ろに `,` があってもかまいません。
- `strstr`、`_System_hConsoleOut`（標準出力のハンドル）を使えます。
- `#include <api_winsock2.sbp>` を書いてもエラーになりません。

**ActiveBasic と同じ動作になったもの**

- 呼ばれない `Function` / `Sub` やクラスの中に未定義の名前などの誤りがあっても、エラーにしません。ActiveBasic は使われない手続きをコンパイルしないためです。
- 関数・型・フィールド・メソッドの名前で、大文字と小文字を区別しません（`printf` を `Printf` でも呼べます。`As Rect` は `RECT` と同じです）。同じ綴りの名前がある場合は、そちらを優先します。
- `Function` / `Sub` の中の `Return` はコンパイルエラーにします。`Return` は `GoSub` から戻るための文です。
- 数値の計算:
  - `Mod` は、Double / Single を整数に切り捨ててから余りを求めます（`1.5 Mod 2` は 1）。
  - `\` と `Mod` は符号付きで計算します（`-7 Mod 3` は -1、`-7 \ 2` は -3）。
  - `As` のない `Function` の戻り値は Double です（型を推定できない旨の警告を出します）。
  - Single の計算は Double で行い、`Print` では有効数字 6 桁で表示します。
- 配列とアドレス:
  - `Dim w[n] As Word` の要素は 2 バイトです。
  - 配列名や `Type` のフィールドをそのまま書くと、そのアドレスになります。構造体を受け取る API に、そのまま渡せます。
  - 配列の要素に `Len` を使うと、要素の大きさを返します。
  - 手続きの中で `Dim` した `Type` と配列は、0 で初期化します。
  - `Print` / `Print #` / `Write #` に `Byte` 配列や `*Byte` を渡すと、文字列として書きます。
- 引数:
  - `ByRef` の `Long` / `Word` / `Byte` の引数を、その大きさで読み書きします。隣の配列要素を壊さなくなりました。
  - `ByRef q As *Byte` の引数に添字を付けると、呼び出し側が渡したバッファを読み書きします。
- `Const` を同じ値で定義し直してもエラーにしません。違う値のときはエラーにします。
- `Do` の後ろの `While` / `Until` は同じ行にあるときだけ読むので、次の行の `While ... Wend` はループのままです。
- 括弧なしの `InsertMenuItem` を、ActiveBasic 3 の RAD が書くメニューの命令として読みます。

**日本語の表示**

- コンボボックス・リストボックス・リストビューの項目と見出しが文字化けしなくなりました。
- 日付・時刻の書式に日本語を使っても、文字化けしなくなりました。
- `SetWindowText` などに Shift-JIS の文字列を渡しても、正しく表示します。
- `GetModuleFileName` は UTF-8 のパスを返します。

**修正**

- MCI の構造体を Windows と同じ並びにしたので、64bit で `mciSendCommand` が落ちなくなりました。
- `Mid$` に文字列の長さを超える開始位置を渡すと落ちることがあったのを直しました。
- 出力先の exe が実行中で書き込めないときは、コンパイルを失敗にします（これまでは成功と表示していました）。
- 64bit で、引数の合計が 127 バイトを超える呼び出しをコンパイルできるようになりました。
- `String` の引数に C 文字列（`BytePtr` など）を渡したときは、中身をコピーして受け取ります。
- N88BASIC のウィンドウを閉じると、プログラムが終了するようになりました。
- 一度のコンパイルで報告できるエラーと警告を増やしました（4096 件まで）。

### ProjectEditor

- 64bit / 32bit の選択を `.pj` の `#PLATFORM` と連動させました。`.pj` を開くとその設定になり、メニューで選び直すと `.pj` に書き戻します。
- 未保存の文書を閉じるとき、エディタを終了するとき、表示言語を変えて再起動するときに、保存するかを確認します。
- 文書を開いていないときも、タイトルにプロジェクトのパスと 64bit / 32bit を表示します。
- 起動時にときどき落ちることがあったのを直しました。
- エラーメッセージの日本語のパスが文字化けしなくなりました。
- 同梱のフォントを読み込めないときは MS ゴシックで表示するので、日本語が四角になりません。
- メッセージウィンドウが再び複数行を表示するようになりました。
- アイコンを新しくしました。

### サンプル・ドキュメント

- `src/actba64/example` に HelloWorld、FizzBuzz、エラトステネスのふるいを追加しました。
- README を書き直し、英語版（`README.md`）と日本語版（`README.ja.md`）を用意しました。
- 対応する ActiveBasic のバージョンを [activebasic-versions.md](./activebasic-versions.md) にまとめました。
- [index.md](./index.md) に、ダウンロードページへのリンクと、Hello World を動かす手順を追加しました。

### 既知の制限

- `-linux` で使えるのは、`Include\linux` に Linux 版がある API だけです。それ以外を呼ぶと、実行時に `unsupported API: 名前` と表示して終了します。
- `-linux` の `Date$` / `Time$` は UTC です。
- `QWord` / `Int64` は 32bit として扱うので、32bit を超える値は扱えません。

## v0.0.3 からの変更点

ActiveBasic 4.20 / 4.24 で書かれた既存のプログラムを、**ソースを書き換えずにそのままコンパイルして動かせる** ことを目標に、互換性を大きく広げました。ウィンドウを使う GUI プログラム、N88BASIC のプログラム、スクリーンセーバーなどのサンプルが動くようになっています。

### ハイライト

- **32bit の exe も actba64.exe 1 本で作れます。** `-actba32` を付けると 32bit、付けなければ 64bit で出力します。これまでの `actba32.exe` はなくなりました。
- **DLL を作れます。** `.pj` に `#MODULETYPE=1` を書き、公開する関数に `Function Export` を付けます。
- **ProjectEditor が MDI になりました。** 複数のファイルを開いたまま切り替えて編集できます。`.pj` を開くとソース一覧が出て、コンパイル・実行はプロジェクト単位で行います。
- **日本語がそのまま表示されます。** ウィンドウのタイトル、メニュー、メッセージボックス、フォント名、ファイルダイアログのパスなどで文字化けしなくなりました。Shift-JIS で書かれた古いソースも読み込めます。
- **アイコンとビットマップをリソースとして埋め込めます。** `#resource "xxx.rc"` の ICON と BITMAP を exe に入れます。リソース ID は ActiveBasic と同じく、`.rc` と同じフォルダの `resource.sbp` の `Const` から読みます。

### 言語・コンパイラ

**新しく使えるようになったもの**

- クラス:
  - `New` / `Delete` でオブジェクトを作成・破棄できます。
  - 継承と `Super` を使えます。
  - `Private` / `Protected` によるアクセス制限が効きます。
  - メソッドの中では、同じクラスのメソッドを `This.` なしで呼べます。
- `Enum`、関数ポインタ型、`Const` マクロ(`RGB(r, g, b)` のように引数を取るもの)。
- `GoTo` / `GoSub` の飛び先に、行番号と `*ラベル` の両方を使えます。
- 条件付きコンパイル(`#define` / `#ifdef` / `#ifndef` / `#else` / `#endif`)。
- 小数点で終わる数値(`1.` など)を Double として読みます。
- 演算子 `=>` / `=<` を `>=` / `<=` として扱います。
- `Print Using`、`Oct$`、`String$`、`ZeroString`、Double を返す `Val`。
- `GetSingle` / `SetSingle` / `GetDouble` / `SetDouble`、`realloc`、`_splitpath`。
- ファイル I/O:
  - `Open` / `Close`、`Input #`、`Print #`、`Write`。
  - `Field` / `Get #` / `Put #`、`Eof` / `Loc` / `Lof`。
- `MsgBox` やパス・日付を扱う BASIC 命令。
- N88BASIC モード:
  - `Color`、`PSET`、`LINE STEP`、`LINE ... ,BF` のスタイル指定。
  - 型を書かない `Dim`、カンマ区切りの `Input`。
- コモンダイアログとコモンコントロールの API 宣言:
  - `ChooseColor`、`ChooseFont`、`PageSetupDlg`、`PrintDlg`。
  - `InitCommonControlsEx`。

**ActiveBasic と同じ動作になったもの**

- 構文:
  - 行末の ` _` で次の行につなげた場合も、全体を 1 行として扱います。1 行の `If ... Then` がつないだ行にまたがっても動きます。
  - `If` や `Select Case` の中に単独で書いた `End` を、プログラム終了の `End` 文として扱います。
  - `SelectCase` / `EndSelect` / `EndFunction` のように、空白なしの書き方も受け付けます。
  - `Next` の後ろに何が書いてあっても無視します。
  - `Let` 付きの代入を受け付けます。
- 呼ばれない `Function` / `Sub` に構文エラーがあっても、エラーにせずにコンパイルを続けます。
- `#console` がない場合は GUI プログラムとして作ります。ただし `#N88BASIC` / `#prompt` ではなく、画面への `Print` がある場合はコンソールプログラムとして作ります。
- 数値の変換:
  - 整数型への代入では、Double / Single の値を切り捨てて整数にします。対象は構造体の整数フィールド、`Declare` した API の整数引数、整数の `For` の `From` / `To` / `Step` です。
  - Single 型のフィールドを Single として読み書きします。
  - `/` は実数の割り算です。
  - `^` は Double でも正しく計算します。
  - `Sgn` は実数の符号を返します。
- 出力・入力:
  - `Print` の数値の書式と、`;` / `,` による区切りを揃えました。
  - 引数のない `Print` は改行だけを出力します。
  - `Input` で値が足りないときは、もう一度入力を求めます。
- `Rnd` は ActiveBasic と同じ乱数列を返します。
- `Len` は、数値の変数・配列・式に使うと、そのバイト数を返します。
- 配列名を値として渡すと、先頭要素のアドレスを渡します。
- 64bit で、4GB を超えるアドレスへのポインタ演算が正しく動きます。
- `Left$` / `Mid$` / `Right$` と `+` による文字列連結が、`GetCommandLine()` の戻り値や BytePtr を直接受け取っても落ちなくなりました。

**エラー表示**

- `#include` で指定したファイルがないときは、`ファイル(行): cannot open include file "フルパス"` と表示します。
- 未定義の名前を使ったときは、その名前をエラーに表示します。
- 原因を表示せずにコンパイルが失敗していた構文エラーを、`syntax error` として報告します。

### ProjectEditor

- MDI になりました:
  - ソースは最大 8 枚まで開いたままにできます。
  - プロジェクトウィンドウの行をクリックすると、そのファイルを開きます。
- 編集操作:
  - Ctrl+F で検索、F3 で次を検索します。
  - Shift で選択範囲を広げられます。
  - ドラッグで選択できます。
  - Ctrl を使う編集キーが使えます。
  - 行番号を表示します。
  - タブを 4 桁ごとに揃えて表示します。
- コンパイルと実行:
  - メッセージウィンドウのエラー行をクリックすると、該当するソース行へ移動します。
  - 実行は exe のあるフォルダで始めます。exe の隣のデータファイルを相対パスで開けます。
  - 終了後もコンソールを開いたままにする実行コマンドがあります。
- 日本語のパスやフォルダにあるファイルも、文字化けせずに開く・コンパイルする・実行することができます。
- ファイルをドラッグ&ドロップして開けます。
- 大きいファイルも正しく開けます。

### 配布物

- `release\` に `rc.exe` を同梱しました。`#resource` の `.rc` はリリースフォルダだけでコンパイルできます。
- `actba32.exe` は同梱しなくなりました。32bit の exe は `actba64 -actba32` で作ります。

### 既知の制限

- `Len` に `GetCommandLine()` の戻り値や `HeapAlloc` で確保したバッファを渡すと、正しい長さを返しません。長さ情報を持たない生のポインタだからです。代わりに `lstrlen` を使ってください。
- 8 バイト整数のフィールドに負の Double を代入すると、整数に変換されません。

詳しい言語仕様は [language.md](./language.md)、ActiveBasic との違いは [different.md](./different.md) を参照してください。
