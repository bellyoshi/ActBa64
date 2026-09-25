# -*- coding: utf-8 -*-
"""Split .abp/.sbp files at Function/Sub boundaries so each part <= MAX_LINES."""
from __future__ import annotations

import re
from pathlib import Path

MAX_LINES = 400
ROOT = Path(r"C:\Users\bellm\source\repos\bellyoshi\ActBa64\src")

FUNC_START = re.compile(
    r"^(?:Public\s+|Private\s+)?(?:Function|Sub)\s+\w+",
    re.I,
)
FUNC_END = re.compile(r"^End\s+(Function|Sub)\b", re.I)
TYPE_START = re.compile(r"^Type\s+\w+", re.I)
TYPE_END = re.compile(r"^End\s+Type\b", re.I)
CLASS_START = re.compile(r"^Class\s+\w+", re.I)
CLASS_END = re.compile(r"^End\s+Class\b", re.I)

SKIP_DIR_PARTS = {
    "prototype1",
    "prototype2",
    "prototype3",
    "prototype4",
    "bin",
    "stage0",
    "stage1",
    "stage2",
}


def should_skip(p: Path) -> bool:
    parts = set(p.parts)
    if parts & SKIP_DIR_PARTS:
        return True
    name = p.name.lower()
    if name.startswith("_dyn_stress"):
        return True
    return False


def split_units(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    """Return (prologue, list of unit line-lists). Units are Type/Class/Function/Sub blocks
    plus any trailing blank/comment lines attached to the previous unit until next block.
    """
    n = len(lines)
    i = 0
    # find first structural block
    first = None
    while i < n:
        s = lines[i].strip()
        if FUNC_START.match(s) or TYPE_START.match(s) or CLASS_START.match(s):
            first = i
            break
        i += 1
    if first is None:
        return lines[:], []

    prologue = lines[:first]
    units: list[list[str]] = []
    i = first
    while i < n:
        s = lines[i].strip()
        if FUNC_START.match(s):
            start = i
            i += 1
            while i < n and not FUNC_END.match(lines[i].strip()):
                i += 1
            if i < n:
                i += 1  # include End
            unit = lines[start:i]
            # attach following blank/comment-only lines until next block
            while i < n:
                t = lines[i].strip()
                if FUNC_START.match(t) or TYPE_START.match(t) or CLASS_START.match(t):
                    break
                if t == "" or t.startswith("'"):
                    unit.append(lines[i])
                    i += 1
                    continue
                # Dim/Const/etc between functions -> treat as own tiny unit start
                break
            units.append(unit)
            continue
        if TYPE_START.match(s):
            start = i
            i += 1
            while i < n and not TYPE_END.match(lines[i].strip()):
                i += 1
            if i < n:
                i += 1
            unit = lines[start:i]
            while i < n:
                t = lines[i].strip()
                if FUNC_START.match(t) or TYPE_START.match(t) or CLASS_START.match(t):
                    break
                if t == "" or t.startswith("'"):
                    unit.append(lines[i])
                    i += 1
                    continue
                break
            units.append(unit)
            continue
        if CLASS_START.match(s):
            start = i
            i += 1
            while i < n and not CLASS_END.match(lines[i].strip()):
                i += 1
            if i < n:
                i += 1
            unit = lines[start:i]
            while i < n:
                t = lines[i].strip()
                if FUNC_START.match(t) or TYPE_START.match(t) or CLASS_START.match(t):
                    break
                if t == "" or t.startswith("'"):
                    unit.append(lines[i])
                    i += 1
                    continue
                break
            units.append(unit)
            continue
        # orphan Dim/Const between blocks — own unit
        start = i
        i += 1
        while i < n:
            t = lines[i].strip()
            if FUNC_START.match(t) or TYPE_START.match(t) or CLASS_START.match(t):
                break
            i += 1
        units.append(lines[start:i])
    return prologue, units


def pack_parts(prologue: list[str], units: list[list[str]], max_lines: int) -> list[list[str]]:
    """Greedy pack units into parts. Prologue only in part 0.
    If a single unit alone exceeds max_lines, still put it alone (cannot mid-split).
    """
    parts: list[list[str]] = []
    cur: list[str] = []
    # part 0 starts with prologue
    header = list(prologue)
    budget0 = max_lines - len(header)
    if budget0 < 1:
        # prologue alone too big — keep as part0, start packing from part1
        parts.append(header)
        header = []
        cur = []
        use_header = False
    else:
        cur = list(header)
        use_header = True

    for unit in units:
        ulen = len(unit)
        if not cur:
            cur = list(unit)
            continue
        if len(cur) + ulen <= max_lines:
            cur.extend(unit)
        else:
            parts.append(cur)
            cur = list(unit)
    if cur:
        parts.append(cur)
    if not parts:
        parts = [header if header else []]
    return parts


def part_path(orig: Path, index: int) -> Path:
    """AstLowerExpr.abp -> AstLowerExpr.abp (0), AstLowerExpr2.abp (1), ..."""
    if index == 0:
        return orig
    stem, suf = orig.stem, orig.suffix
    return orig.with_name(f"{stem}{index + 1}{suf}")


def split_file(path: Path) -> list[Path]:
    text = path.read_text(encoding="utf-8", errors="replace")
    # normalize newlines but preserve content
    lines = text.splitlines(keepends=True)
    # ensure each line has newline for counting consistency — use splitlines without keepends
    raw = text.splitlines()
    # re-add as lines without forcing \r\n issues: write with \n
    lines = raw
    if len(lines) <= MAX_LINES:
        return [path]

    prologue, units = split_units(lines)
    # verify no unit is incomplete: if any unit > MAX and is a function, warn
    parts = pack_parts(prologue, units, MAX_LINES)
    # drop trailing empty parts
    while parts and all(not x.strip() for x in parts[-1]):
        parts.pop()

    written: list[Path] = []
    for i, part in enumerate(parts):
        # trim trailing blank lines in part for cleanliness but keep under limit
        while part and part[-1].strip() == "":
            part.pop()
        outp = part_path(path, i)
        body = "\n".join(part)
        if body and not body.endswith("\n"):
            body += "\n"
        # add part header comment for secondary parts
        if i > 0:
            hdr = f"' --- split from {path.name} (part {i + 1}) ---\n"
            if not body.startswith("' --- split"):
                body = hdr + body
            # if adding header pushes over limit, still OK preference is clarity;
            # re-check: if > MAX, strip header
            if body.count("\n") + (0 if body.endswith("\n") else 1) > MAX_LINES:
                body = "\n".join(part)
                if body and not body.endswith("\n"):
                    body += "\n"
        outp.write_text(body, encoding="utf-8", newline="\n")
        written.append(outp)
        lc = len(body.splitlines())
        print(f"  write {outp.name} ({lc} lines)")
        if lc > MAX_LINES:
            print(f"  WARNING: {outp.name} still {lc} > {MAX_LINES} (oversized unit)")
    return written


def update_list_file(list_path: Path, replacements: dict[str, list[str]]) -> None:
    """Replace 'Foo.abp' with 'Foo.abp\\nFoo2.abp...' in pj/idx source lists."""
    if not list_path.exists():
        return
    text = list_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    changed = False
    for line in lines:
        stripped = line.strip()
        # match exact filename on line (pj) or #include "file"
        m_inc = re.match(r'^#include\s+"([^"]+)"\s*$', stripped)
        key = None
        if m_inc:
            key = m_inc.group(1)
        elif stripped in replacements:
            key = stripped
        if key and key in replacements:
            parts = replacements[key]
            if m_inc:
                for p in parts:
                    out.append(f'#include "{p}"\n')
            else:
                nl = "\r\n" if line.endswith("\r\n") else "\n"
                for p in parts:
                    out.append(p + nl)
            changed = True
        else:
            out.append(line)
    if changed:
        list_path.write_text("".join(out), encoding="utf-8")
        print(f"updated {list_path}")


def main() -> None:
    # collect targets
    targets: list[Path] = []
    for p in sorted(ROOT.rglob("*")):
        if p.suffix.lower() not in {".abp", ".sbp"}:
            continue
        if should_skip(p):
            continue
        try:
            n = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if n > MAX_LINES:
            targets.append(p)

    print(f"targets: {len(targets)}")
    replacements: dict[str, list[str]] = {}  # basename -> [part names]

    for path in targets:
        print(f"\n=== {path.relative_to(ROOT)} ===")
        # skip samples for now? User said all sources - include samples
        written = split_file(path)
        if len(written) > 1:
            replacements[path.name] = [w.name for w in written]

    # update actba64.pj / actba64.idx
    act = ROOT / "actba64"
    update_list_file(act / "actba64.pj", replacements)
    update_list_file(act / "actba64.idx", replacements)

    # projecteditor idxs
    pe = ROOT / "projecteditor"
    for name in ("editor.idx", "ProjectEditor.idx", "projecteditor.idx"):
        update_list_file(pe / name, replacements)

    # recount
    print("\n=== remaining >400 ===")
    left = 0
    for p in sorted(ROOT.rglob("*")):
        if p.suffix.lower() not in {".abp", ".sbp"}:
            continue
        if should_skip(p):
            continue
        n = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
        if n > MAX_LINES:
            print(f"{n:5d}  {p.relative_to(ROOT)}")
            left += 1
    print(f"left: {left}")


if __name__ == "__main__":
    main()
