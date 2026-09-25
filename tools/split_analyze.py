import os, re, sys

TARGETS = sys.argv[1:]

start_re = re.compile(rb'^\s*(?:Public\s+|Private\s+|Static\s+)?(Sub|Function)\s+', re.I)
end_re = re.compile(rb'^\s*End\s+(Sub|Function)\s*(?:\'.*)?$', re.I)
decl_re = re.compile(rb'^\s*Declare\s+', re.I)

def parse(path):
    data = open(path, 'rb').read()
    lines = data.split(b'\r\n')
    trailing_nl = False
    if lines and lines[-1] == b'':
        lines = lines[:-1]
        trailing_nl = True
    units = []  # (start, end) inclusive indexes of function bodies
    i = 0
    n = len(lines)
    depth = 0
    cur = None
    for i, ln in enumerate(lines):
        if decl_re.match(ln):
            continue
        if start_re.match(ln) and cur is None:
            cur = i
        elif end_re.match(ln) and cur is not None:
            units.append((cur, i))
            cur = None
    if cur is not None:
        print('  !! UNTERMINATED unit starting at line', cur + 1)
    return lines, units, trailing_nl

for path in TARGETS:
    lines, units, tn = parse(path)
    print('=' * 70)
    print(path, len(lines), 'lines,', len(units), 'units, trailing_nl=', tn)
    # report non-blank non-comment top-level lines outside units
    covered = [False] * len(lines)
    for s, e in units:
        for k in range(s, e + 1):
            covered[k] = True
    for k, ln in enumerate(lines):
        if covered[k]:
            continue
        t = ln.strip()
        if not t or t.startswith(b"'"):
            continue
        print('   OUT %5d: %s' % (k + 1, t.decode('cp932', 'replace')))
