#!/usr/bin/env bash
# release_build.sh - Linux 版のリリース一式を release-linux/ に揃える（release_build.ps1 の Linux 版）
#
#   既定: ブートストラップ → stage1 → stage2 → stage3（stage2 = stage3 を確かめる）
#         → rc → ProjectEditor → release-linux/ へコピー
#
# 使い方:
#   ./release_build.sh                       # ブートストラップは下の順で探す
#   ./release_build.sh -b path/to/actba64    # Linux 版の actba64（ELF）を指定
#   ./release_build.sh --skip-selfhost       # 既存の stage2 を使い、rc と ProjectEditor だけ作り直す
#   ./release_build.sh --skip-compare        # stage2 と stage3 の比較をしない
#   ./release_build.sh --tar                 # actba64-linux-x86_64.tar.gz も作る
#
# ブートストラップの探し方: -b、環境変数 ACTBA64、src/actba64/bin/linux/actba64
#   （Windows の run_selfhost_linux.ps1 が作る）、PATH の actba64
# 作業場所: src/actba64/bin/lx/stage0..3（stage0 = ブートストラップの写し。各 stage の隣に今の
#   src/Include を置く。コンパイラは隣の Include を読む）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CC_DIR="$ROOT/src/actba64"
RC_DIR="$ROOT/src/rc"
EDITOR_DIR="$ROOT/src/projecteditor"
INCLUDE_SRC="$ROOT/src/Include"
HELP_SRC="$EDITOR_DIR/help"
WORK="$CC_DIR/bin/lx"
RELEASE_DIR="$ROOT/release-linux"
TAR_NAME="actba64-linux-x86_64.tar.gz"

BOOT=""
SKIP_SELFHOST=0
SKIP_COMPARE=0
MAKE_TAR=0

usage() {
    sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        -b|--bootstrap) BOOT="${2:?-b needs a path}"; shift 2 ;;
        --skip-selfhost) SKIP_SELFHOST=1; shift ;;
        --skip-compare) SKIP_COMPARE=1; shift ;;
        --tar) MAKE_TAR=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

die() { echo "error: $*" >&2; exit "${2:-1}"; }

need() {
    [ -e "$1" ] || die "$2 : $1" 2
}

# ELF かどうか（Windows の actba64.exe を渡したときに早めに止める）
is_elf() {
    [ -f "$1" ] && [ "$(head -c 4 "$1" | od -An -tx1 | tr -d ' \n')" = "7f454c46" ]
}

# Include を stage の隣へ置き直す
put_include() {
    rm -rf "$1/Include"
    cp -R "$INCLUDE_SRC" "$1/Include"
}

# compile <compiler> <cwd> <args...>
compile() {
    local cc="$1" dir="$2"
    shift 2
    echo "-- (cd ${dir#"$ROOT"/}) $(basename "$cc") $*"
    local start=$SECONDS
    if ! (cd "$dir" && "$cc" "$@"); then
        die "build failed: $*"
    fi
    echo "   ok ($((SECONDS - start))s)"
}

# build_stage <compiler> <stage>: actba64.pj -linux -> $WORK/<stage>/actba64
build_stage() {
    local cc="$1" out="$WORK/$2"
    echo ""
    echo "=== $2 ==="
    mkdir -p "$out"
    rm -f "$out/actba64"
    put_include "$out"
    compile "$cc" "$CC_DIR" actba64.pj -linux -o "$out/actba64"
    [ -f "$out/actba64" ] || die "no output: $out/actba64"
    chmod +x "$out/actba64"
}

need "$INCLUDE_SRC" "Include missing"
need "$CC_DIR/actba64.pj" "actba64 project missing"
need "$RC_DIR/rc.pj" "rc project missing"
need "$EDITOR_DIR/ProjectEditor.pj" "ProjectEditor project missing"
need "$HELP_SRC" "help missing"

STAGE2="$WORK/stage2/actba64"

if [ "$SKIP_SELFHOST" -eq 0 ]; then
    if [ -z "$BOOT" ]; then
        if [ -n "${ACTBA64:-}" ]; then
            BOOT="$ACTBA64"
        elif [ -f "$CC_DIR/bin/linux/actba64" ]; then
            BOOT="$CC_DIR/bin/linux/actba64"
        elif command -v actba64 >/dev/null 2>&1; then
            BOOT="$(command -v actba64)"
        else
            die "no bootstrap compiler. Pass -b <Linux actba64>, set ACTBA64, or run run_selfhost_linux.ps1 on Windows (makes src/actba64/bin/linux/actba64)" 2
        fi
    fi
    BOOT="$(cd "$(dirname "$BOOT")" && pwd)/$(basename "$BOOT")"
    is_elf "$BOOT" || die "bootstrap is not a Linux ELF: $BOOT" 2
    echo "bootstrap: $BOOT"
    # ブートストラップは隣の Include を読むので、stage0 へ写して今の src/Include を隣に置く
    # （そのままだと古い Include で stage1 を作ってしまう）
    mkdir -p "$WORK/stage0"
    if [ "$BOOT" != "$WORK/stage0/actba64" ]; then
        cp "$BOOT" "$WORK/stage0/actba64"
    fi
    chmod +x "$WORK/stage0/actba64"
    put_include "$WORK/stage0"
    BOOT="$WORK/stage0/actba64"

    # ブートストラップはソースより古いことがあるので、比べるのは stage2 と stage3（ci.ps1 と同じ）
    build_stage "$BOOT" stage1
    build_stage "$WORK/stage1/actba64" stage2
    if [ "$SKIP_COMPARE" -eq 0 ]; then
        build_stage "$STAGE2" stage3
        h2="$(sha256sum "$STAGE2" | cut -d' ' -f1)"
        h3="$(sha256sum "$WORK/stage3/actba64" | cut -d' ' -f1)"
        echo "stage2: $h2"
        echo "stage3: $h3"
        [ "$h2" = "$h3" ] || die "stage2 and stage3 differ (not a fixed point)"
        echo "MATCH"
    fi
fi

is_elf "$STAGE2" || die "stage2 missing: $STAGE2 (run without --skip-selfhost)" 2
put_include "$WORK/stage2"

TMP="$WORK/release_tmp"
rm -rf "$TMP"
mkdir -p "$TMP"

echo ""
echo "=== rc.pj -> rc ==="
compile "$STAGE2" "$RC_DIR" rc.pj -linux -o "$TMP/rc"
# actba64 は #resource の .rc を隣の rc で .res にする
cp "$TMP/rc" "$WORK/stage2/rc"
chmod +x "$TMP/rc" "$WORK/stage2/rc"

echo ""
echo "=== ProjectEditor.pj -> ProjectEditor ==="
compile "$STAGE2" "$EDITOR_DIR" ProjectEditor.pj -linux -o "$TMP/ProjectEditor"
chmod +x "$TMP/ProjectEditor"

rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"
cp "$STAGE2" "$RELEASE_DIR/actba64"
mv "$TMP/rc" "$RELEASE_DIR/rc"
mv "$TMP/ProjectEditor" "$RELEASE_DIR/ProjectEditor"
rm -rf "$TMP"
# actba64 の隣にあればメッセージを日本語で出す（消せば英語）
cp "$CC_DIR/actba_lang_ja.csv" "$RELEASE_DIR/"
cp -R "$INCLUDE_SRC" "$RELEASE_DIR/Include"
cp -R "$HELP_SRC" "$RELEASE_DIR/help"
for f in "$EDITOR_DIR"/ProjectEditor_lang_*.csv; do
    [ -f "$f" ] && cp "$f" "$RELEASE_DIR/"
done
for f in keywords.txt setting.ini; do
    [ -f "$EDITOR_DIR/$f" ] && cp "$EDITOR_DIR/$f" "$RELEASE_DIR/"
done
chmod +x "$RELEASE_DIR/actba64" "$RELEASE_DIR/rc" "$RELEASE_DIR/ProjectEditor"

if [ "$MAKE_TAR" -eq 1 ]; then
    rm -f "$ROOT/$TAR_NAME"
    tar -C "$ROOT" -czf "$ROOT/$TAR_NAME" --transform 's,^release-linux,actba64,' release-linux
    echo ""
    echo "archive: $ROOT/$TAR_NAME"
fi

echo ""
echo "release ready: $RELEASE_DIR"
ls -1 "$RELEASE_DIR" | sed 's/^/  /'
