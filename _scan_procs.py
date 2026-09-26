import re
import pathlib

files = [
    r"src/actba64/samples/dxcube/dx_d3d11.sbp",
    r"src/actba64/samples/dxvertexcolor/dx_d3d11.sbp",
    r"src/actba64/samples/dxxform/dx_d3d11.sbp",
    r"src/actba64/samples/dxcube2/dx_d3d11.sbp",
]
root = pathlib.Path(r"C:\Users\bellm\source\repos\bellyoshi\ActBa64")
all_over = []
for rel in files:
    p = root / rel
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    print("===", rel, "===")
    i = 0
    procs = []
    while i < len(lines):
        m = re.match(r"^\s*(Function|Sub)\s+([^\s(]+)", lines[i], re.I)
        if m:
            kind, name = m.group(1), m.group(2)
            start = i
            j = i + 1
            while j < len(lines):
                if re.match(r"^\s*End\s+(Function|Sub)\b", lines[j], re.I):
                    end = j
                    n = end - start + 1
                    procs.append((name, kind, start + 1, end + 1, n))
                    i = j
                    break
                j += 1
        i += 1
    for name, kind, s, e, n in procs:
        flag = " *** OVER ***" if n > 50 else ""
        print(f"  {kind} {name}: lines {s}-{e} = {n}{flag}")
        if n > 50:
            all_over.append((rel, name, n))
    print()
print("OVER COUNT:", len(all_over))
for x in all_over:
    print(" ", x)
