import re, sys, os

FILES = ["AstLower.abp","AstLowerApi.abp","AstLowerDriver.abp","AstLowerRt.abp","AstLowerStmtCtrl.abp","StrGcRt.abp"]
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "actba64")

start_re = re.compile(r'^\s*(Function|Sub)\s+([A-Za-z_][A-Za-z0-9_$]*)', re.I)
end_re = re.compile(r'^\s*End\s+(Function|Sub)\b', re.I)

def scan(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    i = 0
    while i < len(lines):
        m = start_re.match(lines[i])
        if m:
            kind = m.group(1); name = m.group(2); s = i
            j = i + 1
            while j < len(lines) and not end_re.match(lines[j]):
                j += 1
            n = j - s + 1
            out.append((name, kind, s + 1, j + 1, n))
            i = j + 1
        else:
            i += 1
    return out

def main():
    files = sys.argv[1:] or FILES
    total_over = 0
    grand = []
    for fn in files:
        p = os.path.join(BASE, fn)
        res = scan(p)
        over = [r for r in res if r[4] > 50]
        total_over += len(over)
        print(f"== {fn}: {len(res)} routines, {len(over)} over 50")
        for name, kind, s, e, n in sorted(over, key=lambda x: -x[4]):
            print(f"   {n:4d}  {kind:8s} {name}  (L{s}-{e})")
            grand.append((n, fn, name))
    print(f"\nTOTAL OVER 50: {total_over}")
    return total_over

if __name__ == "__main__":
    main()
