# -*- coding: utf-8 -*-
import re, json
from html import unescape

path = r'c:\Users\bellm\Downloads\BasicHelp.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

def clean(t):
    t = re.sub(r'<[^>]+>', '', t)
    t = unescape(t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

parts = re.split(r'<a\s+name="(chmtopic\d+)"[^>]*>', content, flags=re.I)
sections = {}
for i in range(1, len(parts), 2):
    sections[parts[i]] = clean(parts[i+1])[:1500]

ids = ['chmtopic9','chmtopic11','chmtopic13','chmtopic19','chmtopic40','chmtopic48',
       'chmtopic56','chmtopic63','chmtopic64','chmtopic78','chmtopic80','chmtopic90',
       'chmtopic94','chmtopic95','chmtopic97','chmtopic109']
for tid, text in sections.items():
    if any(k in text[:300] for k in ['命令語： With', '命令語： If', 'Select Case', 'TypeDef',
            '列挙型', 'ReDim', 'GoSub', 'Goto', '行番号', '#include', '識別子', 'コメント',
            'SendWndMsg', 'ByRef', 'Let ', 'End With', 'End Enum']):
        if tid not in ids:
            ids.append(tid)

out = {}
for tid in sorted(set(ids), key=lambda x: int(re.search(r'\d+', x).group())):
    if tid in sections:
        out[tid] = sections[tid]

with open(r'C:\Users\bellm\source\repos\bellyoshi\ActBa64\tools\lang_sections.json','w',encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('extracted', len(out))
