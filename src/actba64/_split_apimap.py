# Rewrite LowMapWinApi into per-DLL helpers using ApiHit1/ApiHit2.
import re

path = r'C:\Users\bellm\source\repos\bellyoshi\ActBa64\src\actba64\ApiMap.abp'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    src = f.read()

# Parse API entries from LowMapWinApi body
fn = re.search(
    r"Function LowMapWinApi\(name As \*Byte, ByRef dllKind As Long, apiOut As \*Byte\) As Long\n"
    r"(.*?)\nEnd Function\n",
    src,
    re.S,
)
if not fn:
    raise SystemExit('LowMapWinApi not found')

body = fn.group(1)
entries = []
section = 'misc'
for line in body.splitlines():
    m = re.match(r"\s*' --- (\w+) ---", line)
    if m:
        section = m.group(1)
        continue
    m = re.match(
        r'\s*If ApiNameEq\(VarPtr\(n\), "([^"]+)"\) <> 0(?: Then| Or ApiNameEq\(VarPtr\(n\), "([^"]+)"\) <> 0 Then)',
        line,
    )
    if m:
        key1 = m.group(1)
        key2 = m.group(2)
        entries.append({'section': section, 'keys': [key1] + ([key2] if key2 else []), 'dll': None, 'exp': None})
        continue
    m = re.match(r'\s*dllKind = (IR_DLL_\w+)', line)
    if m and entries and entries[-1]['dll'] is None:
        entries[-1]['dll'] = m.group(1)
        continue
    m = re.match(r'\s*ApiCopy\(apiOut, "([^"]+)"\)', line)
    if m and entries and entries[-1]['exp'] is None:
        entries[-1]['exp'] = m.group(1)

for e in entries:
    if not e['dll'] or not e['exp']:
        raise SystemExit('bad entry: %r' % e)

print('parsed', len(entries), 'apis')

helpers = '''
Function ApiHit1(n As *Byte, key As *Byte, dll As Long, expName As *Byte, ByRef dllKind As Long, apiOut As *Byte) As Long
    ApiHit1 = 0
    If ApiNameEq(n, key) = 0 Then Exit Function
    dllKind = dll
    ApiCopy(apiOut, expName)
    ApiHit1 = 1
End Function

Function ApiHit2(n As *Byte, key1 As *Byte, key2 As *Byte, dll As Long, expName As *Byte, ByRef dllKind As Long, apiOut As *Byte) As Long
    ApiHit2 = 0
    If ApiNameEq(n, key1) = 0 Then
        If ApiNameEq(n, key2) = 0 Then Exit Function
    End If
    dllKind = dll
    ApiCopy(apiOut, expName)
    ApiHit2 = 1
End Function
'''

# group by section, then chunk so each helper stays well under 100 lines
# each hit is 1 line + maybe blank; ~18 entries => ~40 lines
CHUNK = 16
chunks = []
by_sec = []
cur_sec = None
cur = []
for e in entries:
    if e['section'] != cur_sec:
        if cur:
            by_sec.append((cur_sec, cur))
        cur_sec = e['section']
        cur = []
    cur.append(e)
if cur:
    by_sec.append((cur_sec, cur))

chunk_funcs = []
dispatch_calls = []
for sec, items in by_sec:
    nchunk = 0
    for i in range(0, len(items), CHUNK):
        nchunk += 1
        part = items[i:i + CHUNK]
        fname = 'ApiMap_%s' % sec
        if len(items) > CHUNK:
            fname = 'ApiMap_%s%d' % (sec, nchunk)
        lines = [
            'Function %s(n As *Byte, ByRef dllKind As Long, apiOut As *Byte) As Long' % fname,
            '    %s = 1' % fname,
        ]
        for e in part:
            if len(e['keys']) == 1:
                lines.append(
                    '    If ApiHit1(n, "%s", %s, "%s", dllKind, apiOut) <> 0 Then Exit Function'
                    % (e['keys'][0], e['dll'], e['exp'])
                )
            else:
                lines.append(
                    '    If ApiHit2(n, "%s", "%s", %s, "%s", dllKind, apiOut) <> 0 Then Exit Function'
                    % (e['keys'][0], e['keys'][1], e['dll'], e['exp'])
                )
        lines.append('    %s = 0' % fname)
        lines.append('End Function')
        chunk_funcs.append('\n'.join(lines))
        dispatch_calls.append(fname)

dispatch = [
    'Function LowMapWinApi(name As *Byte, ByRef dllKind As Long, apiOut As *Byte) As Long',
    '    Dim n(63) As Byte',
    '    Dim i As Long',
    '    Dim c As Long',
    '',
    '    LowMapWinApi = 0',
    '    dllKind = 0',
    '    apiOut[0] = 0',
    '    i = 0',
    '    While name[i] <> 0 And i < 63',
    '        c = name[i]',
    '        If c >= 65 And c <= 90 Then c = c + 32',
    '        n[i] = c',
    '        i = i + 1',
    '    Wend',
    '    n[i] = 0',
    '',
]
for fname in dispatch_calls:
    dispatch.append('    If %s(VarPtr(n), dllKind, apiOut) <> 0 Then' % fname)
    dispatch.append('        LowMapWinApi = 1')
    dispatch.append('        Exit Function')
    dispatch.append('    End If')
dispatch.append('End Function')

new_fn = helpers.strip() + '\n\n' + '\n\n'.join(chunk_funcs) + '\n\n' + '\n'.join(dispatch) + '\n'
new_src = src[:fn.start()] + new_fn + src[fn.end():]
with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(new_src)
print('wrote', path)
print('helpers', len(chunk_funcs), 'dispatch lines', len(dispatch))
