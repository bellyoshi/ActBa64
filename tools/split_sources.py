"""Split oversized ActiveBasic sources at Sub/Function boundaries.

Usage: python tools/split_sources.py [--apply] <file> [<file> ...]
"""
import os
import re
import sys

LIMIT = 400

start_re = re.compile(rb'^\s*(?:Public\s+|Private\s+|Static\s+)*(?:Sub|Function)\s+[A-Za-z_~]', re.I)
end_re = re.compile(rb'^\s*End\s+(?:Sub|Function)\s*(?:\'.*)?$', re.I)
decl_re = re.compile(rb'^\s*Declare\s+', re.I)
blk_start_re = re.compile(rb'^\s*(?:Class|Interface|Type|Enum)\s+[A-Za-z_]', re.I)
blk_end_re = re.compile(rb'^\s*End\s+(?:Class|Interface|Type|Enum)\s*(?:\'.*)?$', re.I)
cmt_re = re.compile(rb"^\s*'")


def detect_eol(data):
    if b'\r\n' in data:
        return b'\r\n'
    if b'\n' in data:
        return b'\n'
    return b'\r\n'


def parse(path):
    data = open(path, 'rb').read()
    eol = detect_eol(data)
    trailing = data.endswith(eol)
    lines = data.split(eol)
    if trailing:
        lines = lines[:-1]
    units = []
    cur = None
    in_blk = False
    for i, ln in enumerate(lines):
        if in_blk:
            if blk_end_re.match(ln):
                in_blk = False
            continue
        if cur is None and blk_start_re.match(ln):
            in_blk = True
            continue
        if decl_re.match(ln):
            continue
        if cur is None:
            if start_re.match(ln):
                cur = i
        else:
            if end_re.match(ln):
                units.append((cur, i))
                cur = None
    if cur is not None:
        raise SystemExit('%s: unterminated Sub/Function at line %d' % (path, cur + 1))
    return lines, units, eol, trailing


def chunkify(lines, units):
    """Return (prologue_lines, [chunk_lines, ...], epilogue_lines)."""
    chunks = []
    starts = []
    for s, e in units:
        a = s
        while a - 1 >= 0 and cmt_re.match(lines[a - 1]):
            a -= 1
        starts.append(a)
    # make sure attached comments do not overlap previous unit end
    for j in range(len(units)):
        lo = 0 if j == 0 else units[j - 1][1] + 1
        if starts[j] < lo:
            starts[j] = lo
    prologue_end = starts[0] if units else len(lines)
    prologue = lines[:prologue_end]
    for j, (s, e) in enumerate(units):
        nxt = starts[j + 1] if j + 1 < len(units) else len(lines)
        chunks.append(lines[starts[j]:nxt])
    return prologue, chunks


def strip_trailing_blanks(ls):
    while ls and not ls[-1].strip():
        ls.pop()
    return ls


def split_file(path, apply=False, verbose=True):
    lines, units, eol, trailing = parse(path)
    if len(lines) <= LIMIT:
        if verbose:
            print('%s: %d lines, no split needed' % (path, len(lines)))
        return []
    prologue, chunks = chunkify(lines, units)
    root, ext = os.path.splitext(path)
    base = os.path.basename(root)

    parts = []           # list of list-of-lines
    cur = list(prologue)
    header_len = 0
    for ch in chunks:
        cand = len(cur) + len(ch)
        if cur and cand > LIMIT and len(strip_trailing_blanks(list(cur))) > 0 and len(cur) > header_len:
            parts.append(cur)
            idx = len(parts) + 1
            hdr = [
                b"' ===================================================",
                ("'  %s%d - split from %s%s (part %d)" % (base, idx, base, ext, idx)).encode('ascii'),
                b"' ===================================================",
                b'',
            ]
            cur = list(hdr)
            header_len = len(hdr)
        cur = cur + ch
    parts.append(cur)

    outputs = []
    for i, p in enumerate(parts):
        p = strip_trailing_blanks(list(p))
        name = path if i == 0 else '%s%d%s' % (root, i + 1, ext)
        outputs.append((name, p))

    if verbose:
        print('%s: %d lines -> %d parts' % (path, len(lines), len(outputs)))
        for name, p in outputs:
            flag = '  OVER!' if len(p) > LIMIT else ''
            print('    %-60s %4d%s' % (os.path.basename(name), len(p), flag))

    if apply:
        for name, p in outputs:
            data = eol.join(p) + eol
            with open(name, 'wb') as f:
                f.write(data)
    return [os.path.basename(n) for n, _ in outputs]


if __name__ == '__main__':
    args = sys.argv[1:]
    apply = '--apply' in args
    files = [a for a in args if not a.startswith('--')]
    for f in files:
        split_file(f, apply=apply)
