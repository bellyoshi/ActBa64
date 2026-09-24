import re
from pathlib import Path

files = [
    Path("src/actba64/AstLower.abp"),
    Path("src/actba64/AstLowerAddr.abp"),
    Path("src/actba64/AstLowerRt.abp"),
    Path("src/actba64/AstLowerApi.abp"),
    Path("src/actba64/AstLowerDriver.abp"),
    Path("src/actba64/StrGcRt.abp"),
]

pat = re.compile(r"^(Function|Sub)\s+(\w+)", re.I)
end_pat = re.compile(r"^End\s+(Function|Sub)\s*$", re.I)


def scan_file(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    procs = []
    i = 0
    while i < len(lines):
        m = pat.match(lines[i].strip())
        if not m:
            i += 1
            continue
        name = m.group(2)
        start = i
        j = i + 1
        depth = 0
        while j < len(lines):
            s = lines[j].strip()
            if pat.match(s):
                depth += 1
            if end_pat.match(s):
                if depth == 0:
                    length = j - start + 1
                    procs.append((name, start + 1, j + 1, length))
                    i = j
                    break
                depth -= 1
            j += 1
        i += 1
    return procs


over = []
for fp in files:
    for name, start, end, length in scan_file(fp):
        if length > 50:
            over.append((fp.name, name, start, end, length))

print(f"Total >50: {len(over)}")
for row in sorted(over, key=lambda x: -x[4]):
    print(f"{row[0]}:{row[2]}-{row[3]} {row[1]} = {row[4]} lines")
