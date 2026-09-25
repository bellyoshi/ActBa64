import re
import sys
from pathlib import Path

FILES = [
    "AstLowerExpr.abp",
    "AstLowerExprOps.abp",
    "AstLowerStmt.abp",
    "AstLowerStmtCtrl.abp",
    "AstLowerRt.abp",
    "AstLowerAddr.abp",
    "AstLower.abp",
    "AstLowerApi.abp",
    "AstLowerDriver.abp",
    "StrGcRt.abp",
]

START = re.compile(r"^\s*(?:Function|Sub)\s+([A-Za-z_][A-Za-z0-9_$]*)")
END = re.compile(r"^\s*End\s+(?:Function|Sub)\b")

root = Path(__file__).resolve().parent.parent / "src" / "actba64"
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50

total = 0
for name in FILES:
    path = root / name
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = None
    fname = ""
    over = []
    for i, line in enumerate(lines, 1):
        if start is None:
            m = START.match(line)
            if m:
                start, fname = i, m.group(1)
        elif END.match(line):
            n = i - start + 1
            if n > limit:
                over.append((fname, start, n))
            start = None
    total += len(over)
    print(f"{name}: {len(over)} over {limit}")
    for fname, start, n in over:
        print(f"    {fname} (line {start}) = {n}")

print(f"TOTAL over {limit}: {total}")
