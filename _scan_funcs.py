import re
from pathlib import Path

FILES = [
    "Preproc.abp", "PreprocCond.abp", "PreprocPj.abp", "Lexer.abp", "CodeGen.abp",
    "CodeGen32.abp", "Types.abp", "Utils.abp", "ApiMap.abp", "ImportBuilder.abp", "Compiler.abp",
]
base = Path(r"C:/Users/bellm/source/repos/bellyoshi/ActBa64/src/actba64")
start_re = re.compile(r"^(Sub|Function)\s+\w+", re.I)
end_re = re.compile(r"^End\s+(Sub|Function)\s*", re.I)


def count_in_file(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    results = []
    i = 0
    while i < len(lines):
        if start_re.match(lines[i].strip()):
            start = i
            name = lines[i].strip()
            i += 1
            while i < len(lines):
                if end_re.match(lines[i].strip()):
                    length = i - start + 1
                    if length > 50:
                        results.append((length, name, start + 1, i + 1))
                    i += 1
                    break
                i += 1
        else:
            i += 1
    return results


all_r = []
for f in FILES:
    p = base / f
    r = count_in_file(p)
    for item in r:
        all_r.append((f, *item))

all_r.sort(key=lambda x: -x[2])
print(f"Total >50: {len(all_r)}")
for f, length, name, s, e in all_r:
    print(f"{f}:{s}-{e} ({length}) {name[:80]}")
