import re
from pathlib import Path

def count_abp_functions(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    starts = []
    for i, line in enumerate(lines):
        m = re.match(r"^\s*(Public\s+|Private\s+)?(Function|Sub)\s+(\w+)", line, re.I)
        if m:
            starts.append((i, m.group(2), m.group(3)))

    results = []
    for idx, (start_i, kind, name) in enumerate(starts):
        end_i = starts[idx + 1][0] - 1 if idx + 1 < len(starts) else len(lines) - 1
        for j in range(start_i, min(end_i + 1, len(lines))):
            if re.match(r"^\s*End\s+(Function|Sub)\s*$", lines[j], re.I):
                end_i = j
                break
        body_lines = end_i - start_i + 1
        if body_lines > 50:
            results.append((name, kind, start_i + 1, end_i + 1, body_lines))
    return results


base = Path(__file__).resolve().parent / "src" / "actba64"
files = [
    "ParserCtrl.abp",
    "ParserClass.abp",
    "Parser.abp",
    "ParserDim.abp",
    "ParserDriver.abp",
    "ParserExpr.abp",
    "ParserN88.abp",
    "ParserStmtIO.abp",
]
total = 0
for f in files:
    p = base / f
    overs = count_abp_functions(p)
    total += len(overs)
    for name, kind, s, e, n in overs:
        print(f"{f}: {kind} {name} L{s}-L{e} ({n} lines)")
print(f"TOTAL >50: {total}")
