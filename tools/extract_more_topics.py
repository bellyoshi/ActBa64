# -*- coding: utf-8 -*-
import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\bellm\source\repos\bellyoshi\ActBa64\tools\basichelp_final.json', encoding='utf-8') as f:
    d = json.load(f)

by_id = {}
for section in ['syntax_features','builtin_functions','types_and_structures','language_rules','classes','directx_gui','events']:
    for t in d.get(section, []):
        if 'id' in t:
            by_id[t['id']] = t

# Map toc to topics
toc_map = {href.lstrip('#'): name for href, name in d['full_toc']}

MORE = ['With', 'TypeDef', 'Enum', 'Select Case', 'If ', 'ReDim', 'Let', 'SendWndMsg', 
        'DelWnd', 'Window 命令', '列挙', 'マクロ', 'コールバック', '関数ポインタ',
        'コメント', '識別子', '文字列', '改行', 'Rem', 'プロンプト', 'Include',
        'SizeOf', 'MakeStr', 'ELM', 'Inkey', 'Write命令', 'Get#', 'Put#',
        'Randomize', 'Rnd', 'Const', 'Continue', 'Exit ', 'Inherits',
        'CAudio', 'CImage', 'CMesh', 'DirectX', 'dx_']

print('=== ADDITIONAL LANGUAGE TOPICS ===')
for tid, name in sorted(toc_map.items(), key=lambda x: int(re.search(r'\d+', x[0]).group())):
    for s in MORE:
        if s.lower() in name.lower():
            t = by_id.get(tid, {})
            print(f'\n--- {name} (chmtopic) ---')
            print(f"Doc: {t.get('clearly_documented','?')}/{t.get('doc_quality','?')}")
            print(t.get('preview', '(no body extracted)')[:1000])
            break

# DirectX class methods
print('\n\n=== DIRECTX CLASS TOPICS ===')
for tid, name in toc_map.items():
    if any(k in name for k in ['CAudio', 'CImage', 'CMesh', 'CRect', 'CInput', 'CListener', 'DirectX', 'dx_']):
        t = by_id.get(tid, {})
        print(f'  {name} [{t.get("doc_quality","?")}]')

# All statement names from toc
print('\n\n=== ALL 命令文/命令語 IN TOC ===')
for tid, name in toc_map.items():
    if '命令' in name or 'ステートメント' in name or 'スチE' in name:
        print(f'  {name}')

# All 関数 in toc that are basic (not Win32)
print('\n\n=== BASIC/STANDARD 関数 IN TOC ===')
basic_prefixes = ['Len', 'Left', 'Right', 'Mid', 'InStr', 'Str', 'Val', 'Hex', 'Oct', 'Chr', 'Asc',
                  'Abs', 'Sgn', 'Int', 'Fix', 'Round', 'Rnd', 'Sqr', 'Sin', 'Cos', 'Tan', 'Log', 'Exp',
                  'Date', 'Time', 'Inkey', 'Input', 'MakeStr', 'VarPtr', 'StrPtr', 'AddressOf', 'ELM',
                  'GetByte', 'GetWord', 'GetDWord', 'GetSingle', 'GetDouble', 'SetByte', 'SetWord',
                  'SetDWord', 'SetSingle', 'SetDouble', 'SizeOf', 'Eof', 'malloc', 'calloc', 'realloc', 'free']
for tid, name in toc_map.items():
    if '関数' in name:
        base = name.replace('関数','').strip()
        if any(base.startswith(p) or base == p for p in basic_prefixes):
            t = by_id.get(tid, {})
            print(f'  {name} [{t.get("doc_quality","?")}] preview={t.get("preview","")[:120]}')
