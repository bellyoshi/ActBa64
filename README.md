# ActBa64

[日本語](README.ja.md) | English

ActBa64 is a compiler for a large subset of the ActiveBasic language (versions 4.20 / 4.24), written in ActiveBasic itself. It started as an experiment — "what happens if you build an ActiveBasic look-alike in ActiveBasic?" — and has grown into a self-hosting toolchain that compiles itself, its resource compiler and its own editor.

The goal is to let existing ActiveBasic programs compile and run **without editing the source**. However, ActBa64 is an independent implementation modeled on ActiveBasic and is not fully compatible with it. Some specifications and behaviors may differ; see [Differences from ActiveBasic](docs/different.md).

ActBa64 is an unofficial project and is not affiliated with Discoversoft, the developer of ActiveBasic.

## Features

- **One compiler, three targets.** `actba64.exe` writes a 64-bit Windows PE (PE32+) by default, a 32-bit PE (PE32) with `-actba32`, and an x86-64 Linux ELF with `-linux`. The lexer, parser, AST and IR are shared; only code generation and the file format differ.
- **Self-hosting.** The compiler builds itself, and the stage 1 and stage 2 binaries are byte-identical. The Linux build of the compiler also reproduces itself and emits the same PE files as the Windows build.
- **Windows GUI programs.** Win32 API declarations, window classes, menus, dialogs, common dialogs and common controls work. Strings are UTF-8 internally and are converted to UTF-16 at the API boundary, so Japanese text shows correctly. Shift-JIS sources are still accepted.
- **Language.** Classes (`New` / `Delete`, inheritance, `Super`, `Virtual`, `Private` / `Protected`), `Type`, `Enum`, function pointers, `Const` macros, IEEE Double math, file I/O (`Open`, `Input #`, `Print #`, `Field`, `Get #`, `Put #`), `Print Using`, conditional compilation, and more.
- **DLLs and resources.** Build DLLs with `#MODULETYPE=1` and `Function Export`. Embed icons and bitmaps from a `.rc` file with `#resource`, compiled by the bundled `rc.exe`.
- **N88-BASIC.** `#N88BASIC` gives a 640x480 graphics window (`LINE`, `CIRCLE`, `PSET`, `COLOR`, `LOCATE`, `INKEY$`). `-pN88` reads classic N88-BASIC source with optional line numbers and no `Dim`.
- **Linux without libc.** `-linux` writes a static ELF that talks to the kernel directly: console, files, heap, time, command line and child processes. A `Declare` whose `Lib` is a `.so` turns the output into a dynamically linked ELF, so you can call libc or libm.
- **DirectX 11** through COM vtables (DirectX 9 is not supported). See the samples under `src/actba64/samples/dx*`.
- **ProjectEditor.** A 64-bit MDI editor with project (`.pj`) support, compile / run, jump-to-error, find, syntax highlighting, F1 help, and English / Japanese UI.
- **Debugger.** `-debug` writes line and variable info to a `.abdbg` file next to the exe. `abdbg.exe` (also written in ActiveBasic) runs it with breakpoints (conditional too), step over / in / out, a call stack and a variable tree; ProjectEditor drives it with F5 / F9 / F10 / F11. Windows 64-bit and 32-bit exes.
- **Readable diagnostics.** Errors and warnings use the form `error: file(line): message`, and several are reported per run.

## Download

Get the latest build from [GitHub Releases](https://github.com/bellyoshi/ActBa64/releases). Unzip it anywhere and keep the files together:

| File | Purpose |
|---|---|
| `ProjectEditor.exe` | Editor. Calls `actba64.exe` in the same folder |
| `actba64.exe` | Compiler |
| `rc.exe` | Resource compiler. Started by `actba64.exe`. |
| `abdbg.exe` | Debugger. Started by ProjectEditor (F5) |
| `Include\` | Standard headers. Must be in the same folder as `actba64.exe` |
| `help\` | HTML reference opened with F1 |
| `ProjectEditor_lang_*.csv`, `keywords.txt`, `setting.ini` | UI languages, highlight keywords, settings |

## Quick start

`hello.abp`:

```vb
#console
Print "Hello World!"
```

```powershell
actba64 hello.abp -o hello.exe              # 64-bit Windows
actba64 hello.abp -actba32 -o hello32.exe   # 32-bit Windows
actba64 hello.abp -linux -o hello           # x86-64 Linux ELF
```

Or open `ProjectEditor.exe`, type the program and choose Run from the Basic menu.

### Command line

```text
actba64 <src.abp|.pj> [-actba32] [-linux] [-X] [-pN88] [-pAB2] [-o <out>]
```

| Option | Meaning |
|---|---|
| `-o <out>` | Output path. Required for a `.abp`; optional for a `.pj` that has `#OUTPUT_RELEASE` (relative to the `.pj`) |
| `-actba32` | 32-bit PE instead of 64-bit |
| `-linux` | x86-64 Linux ELF |
| `-X` | Leave out functions and methods that are never called, and the APIs only they use (Hello World 64-bit: 163 KB → 12 KB). `-linux` always does this |
| `-pN88` | Read the source as N88-BASIC |
| `-pAB2` | Read the source as ActiveBasic 2.62 |

A project file (`.pj`) lists sources under `#SOURCE` and compiles them as one program. The exit code is non-zero when compilation fails.

## Building from source

Requirements: Windows with PowerShell, and **ActiveBasic 4.20** for the first bootstrap only. WSL is optional and is used for the Linux tests.

1. **stage0**: build `src/actba64/actba64.pj` with ActiveBasic 4.20 and save it as `src\actba64\bin\stage0\actba64.exe` (a 32-bit host).
2. **stage1 / stage2**: stage0 compiles the compiler as a 64-bit program, and that compiler compiles itself again. The two results must be identical.

```powershell
cd src\actba64
.\build.ps1                     # stage0 -> stage1 -> stage2, then compare
cd ..\..
.\release_build.ps1             # bootstrap + rc.exe + ProjectEditor -> release\
.\release_build.ps1 -SkipSelfHost   # reuse the existing stage2
```

Building ProjectEditor also needs `Callback.wbp` and `MakeWindow.wbp` in `src\projecteditor\` (written by the ActiveBasic RAD). Details and troubleshooting: [docs/build.md](docs/build.md).

## Tests

```powershell
.\check.ps1 unit           # unit tests in src\unittest (run before every commit)
.\check.ps1 integration    # compile-and-run tests in src\actba64\test, plus Linux tests and Linux self-hosting under WSL (run before every push)
```

The integration runner can also target another stage or the 32-bit back end:

```powershell
cd src\actba64
.\run_test2.ps1 stage2 -Actba32
.\run_test2.ps1 -IncludeGui     # also run GUI tests (skipped by default)
```

## Repository layout

| Path | Contents |
|---|---|
| `src/actba64` | Compiler: lexer, parser, AST lowering, IR, x64 / x86 code generators, PE and ELF writers. Also `test/` (integration tests), `samples/` and `example/` |
| `src/Include` | Standard headers shared by the compiler and the editor (`default`, `console`, `N88BASIC`, `d3d11`, `linux`) |
| `src/rc` | Resource compiler (`rc.exe`) |
| `src/projecteditor` | ProjectEditor source, help and language files |
| `src/abdbg` | Debugger (`abdbg.exe`) and its tests |
| `src/common` | Utilities shared by the compiler and the editor |
| `src/unittest` | Unit tests |
| `src/dbgtest` | Unit tests for the debugger parts of abdbg and ProjectEditor |
| `docs/` | Documentation |

The early prototypes (old assembler / linker) have moved to [bellyoshi/Actba64-prototype](https://github.com/bellyoshi/Actba64-prototype). They are not part of the current toolchain.

## Documentation

The documentation is written in Japanese and is also published at [docs.actba64.com](https://docs.actba64.com).

- [Language reference](docs/language.md)
- [Differences from ActiveBasic](docs/different.md)
- [Known issues](docs/known.md) (behaviors kept from ActiveBasic 4.20)
- [Build and tests](docs/build.md)
- [ProjectEditor](docs/projecteditor.md)
- [Debugger](docs/debugger.md)
- [String GC design](docs/string-gc.md)
- [Coding conventions](docs/coding.md)
- [Release notes](docs/release-notes.md)
- [TODO](docs/todo.md)

## Status

ActBa64 is under active development. Notable gaps today: DirectX 9, `On Error` / `Resume`, `Int64` / `QWord` types, scientific notation literals, general `Single` arithmetic, and `MENU` resources. Under `-linux`, only APIs that have a Linux implementation in `Include\linux` work; the compiler warns about the others.

## License

MIT License. Programs you build with ActBa64 (EXE / DLL) belong to you, and you may distribute them freely, including for commercial use. See [LICENSE](LICENSE) ([日本語訳](docs/license.ja.md)) and [Distribution terms for programs you create](docs/distribution.md).
