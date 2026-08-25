# -*- coding: utf-8 -*-
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\bellm\source\repos\bellyoshi\ActBa64\tools\basichelp_final.json', encoding='utf-8') as f:
    d = json.load(f)

all_topics = (d['syntax_features'] + d['builtin_functions'] + d['types_and_structures'] + 
              d['language_rules'] + d['classes'] + d['directx_gui'] + d['events'])

# Build id->topic map
by_id = {t['id']: t for t in all_topics if 'id' in t}
by_name = {t['name']: t for t in all_topics}

KEYS = [
    '基本型', 'Class', 'End Class', 'Type', 'End Type', 'Dim', 'Function', 'Sub', 'Declare',
    '#strict', '#define', '#ifdef', '#include', 'With', 'GoSub', 'Goto', 'Return',
    'Enum', 'TypeDef', 'Let', 'ByRef', 'Select Case', 'If', 'For', 'While', 'Do',
    'Print', 'Input', 'Open', 'ReDim', 'New', 'Delete', 'AddressOf', 'Const',
    '行番号', 'ラベル', 'コメント', '識別子', '文字列', '演算子', 'ポインタ', '列挙',
    'As演算子', 'SizeOf', 'VarPtr', 'StrPtr', 'MakeStr', 'Field', 'Window',
    'GetDouble', 'SetDouble', 'TypeDef', '関数ポインタ', 'コールバック',
]

print('=== KEY TOPIC DETAILS ===')
seen = set()
for href, name in d['full_toc']:
    for kw in KEYS:
        if kw.lower() in name.lower() or name.startswith(kw):
            if name in seen:
                break
            seen.add(name)
            tid = href.lstrip('#')
            topic = by_id.get(tid) or by_name.get(name)
            if topic:
                print(f'\n--- {name} ---')
                print(f"Category: {topic.get('category')} | Doc: {topic.get('clearly_documented')}/{topic.get('doc_quality')}")
                print(f"Signature: {topic.get('signature','')}")
                print(topic.get('preview','')[:900])
            break

print('\n\n=== ALL STATEMENTS ===')
for t in d['syntax_features']:
    if t.get('category') == 'statement':
        print(f"  {t['name']} [{t['doc_quality']}] sig={t.get('signature','')[:50]}")

print('\n=== ALL DIRECTIVES ===')
for t in d['syntax_features']:
    n = t.get('name','')
    if t.get('category') == 'directive' or n.startswith('#'):
        print(f"  {n} [{t['doc_quality']}]")
        print(f"    {t.get('preview','')[:200]}")

print('\n=== ALL OPERATORS ===')
for t in d['syntax_features']:
    if t.get('category') == 'operator':
        print(f"  {t['name']} [{t['doc_quality']}]")
        print(f"    {t.get('preview','')[:300]}")

print('\n=== BASIC TYPES ===')
for t in d['types_and_structures']:
    if '基本型' in t['name']:
        print(t['preview'][:2000])

print('\n=== FILE I/O STATEMENTS ===')
for t in d['syntax_features']:
    if t.get('category') == 'file_io' or any(k in t['name'] for k in ['Open', 'Close', 'Print', 'Input', 'Field', 'Get#', 'Put#', 'Write', 'Eof']):
        print(f"  {t['name']}")
        print(f"    {t.get('preview','')[:400]}")
        print()

print('\n=== STANDARD FUNCTIONS (string/math) ===')
std_funcs = ['Len', 'Left$', 'Right$', 'Mid$', 'InStr', 'Trim', 'UCase', 'LCase', 
             'Str$', 'Val', 'Format$', 'Chr$', 'Asc', 'Hex$', 'Oct$',
             'Abs', 'Sgn', 'Int', 'Fix', 'Round', 'Rnd', 'Sqr', 'Sin', 'Cos', 'Tan',
             'UBound', 'LBound', 'Array', 'MsgBox', 'Shell', 'Inkey$', 'Input$']
for fn in std_funcs:
    for t in d['builtin_functions']:
        if fn.lower() in t['name'].lower():
            print(f"  {t['name']} [{t['doc_quality']}] sig={t.get('signature','')[:60]}")
            break
    else:
        print(f"  {fn} [NOT IN TOC]")

print('\n=== LINE NUMBER / LABEL / GoSub ===')
for t in all_topics:
    p = t.get('preview','')
    n = t.get('name','')
    if any(k in p for k in ['行番号', 'ラベル']) or any(k in n for k in ['GoSub', 'Goto', 'Return']):
        print(f'--- {n} ---')
        print(p[:700])
        print()
