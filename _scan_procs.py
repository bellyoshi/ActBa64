import re, os
files = [
r'src/actba64/samples/dxcube/dx_d3d11.sbp',
r'src/actba64/samples/dxvertexcolor/dx_d3d11.sbp',
r'src/actba64/samples/dxxform/dx_d3d11.sbp',
r'src/actba64/samples/dxcube2/dx_d3d11.sbp',
r'src/actba64/samples/MovingReversiMove.abp',
r'src/actba64/test/_pe_gui_cmdarg.abp',
r'src/actba64/test/t_cmdarg.abp',
r'src/actba64/samples/MovingReversiBoard.abp',
r'src/actba64/samples/reversi_gui_draw.abp',
r'src/actba64/samples/dxsample/dx_d3d11.sbp',
]
root = r'C:\Users\bellm\source\repos\bellyoshi\ActBa64'
pat = re.compile(r'^\s*((?:Public|Private|Static)\s+)?(Function|Sub)\s+(\w+)', re.I)
end_pat = re.compile(r'^\s*End\s+(Function|Sub)\b', re.I)
decl = re.compile(r'^\s*Declare\b', re.I)
for f in files:
    path = os.path.join(root, f)
    with open(path, encoding='utf-8', errors='replace') as fh:
        lines = fh.readlines()
    i = 0
    procs = []
    while i < len(lines):
        if decl.match(lines[i]):
            i += 1
            continue
        m = pat.match(lines[i])
        if m:
            kind, name = m.group(2), m.group(3)
            start = i
            i += 1
            while i < len(lines) and not end_pat.match(lines[i]):
                i += 1
            if i < len(lines):
                end = i
                count = end - start + 1
                procs.append((name, kind, count))
                i += 1
            continue
        i += 1
    print('### ' + f)
    for name, kind, count in procs:
        flag = ' *' if count > 50 else ''
        print('  %s %s: %d%s' % (kind, name, count, flag))
