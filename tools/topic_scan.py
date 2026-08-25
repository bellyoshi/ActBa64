# -*- coding: utf-8 -*-
import re, sys, io
from html import unescape
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'c:\Users\bellm\Downloads\BasicHelp.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

def clean(t):
    t = re.sub(r'<[^>]+>', '', t)
    return unescape(t).strip()

anchors = re.findall(r'<a[^>]*>(.*?)</a>', content, re.I|re.S)
print('Total <a> tags:', len(anchors))
href_links = re.findall(r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>', content, re.I|re.S)
print('With href:', len(href_links))
for h, t in href_links[:20]:
    t2 = clean(t)
    print(f'  href={h[:40]!r} text={t2[:60]!r}')

patterns = [
    '命令文', '関数', '構造体', 'クラス', '定数', 'イベント', 'プロパティ', 'メソッド',
    '演算子', 'データ型', '型一覧', '構文', '言語', '文法', '命令',
    '列挙型', 'モジュール', '組込', 'ビルトイン', '内部関数',
]
for pat in patterns:
    n = len(re.findall(pat, content))
    if n > 0:
        print(f'Pattern {pat}: {n}')

full = clean(content)
topic_re = re.compile(r'([#A-Za-z_][\w$]*(?:\.[\w$]+)*)\s+(命令文|関数|構造体|クラス|定数|イベント|プロパティ|メソッド|演算子)', re.U)
topics = topic_re.findall(full)
print(f'\nTopic titles found: {len(topics)}')
cat_counter = Counter(t[1] for t in topics)
print('By category:', dict(cat_counter))

by_cat = {}
for name, cat in topics:
    by_cat.setdefault(cat, set()).add(name)
for cat in sorted(by_cat):
    items = sorted(by_cat[cat])
    print(f'\n[{cat}] ({len(items)})')
    for i in items[:50]:
        print(f'  {i}')
    if len(items) > 50:
        print(f'  ...+{len(items)-50}')

# Search language keywords with context
for kw in ['#strict', '#define', '#include', 'GoSub', 'With', 'TypeDef', 'Let ', 'ByRef', 
           '行番号', 'ラベル', '文字列', 'ActiveBasic', '4.20', '4.2', 'ReDim', 'Option',
           'End Type', 'End Class', 'Select Case', 'On Error', 'Declare Sub', 'Declare Function']:
    idx = content.find(kw)
    if idx >= 0:
        ctx = clean(content[max(0,idx-100):idx+300])
        print(f'\n=== Found {kw!r} at {idx} ===')
        print(ctx[:350])

# Find awtext002 (likely headings) content
headings = re.findall(r'class="awspan awtext002"[^>]*>(.*?)</span>', content, re.I|re.S)
print(f'\nawtext002 headings: {len(headings)}')
heading_texts = [clean(h) for h in headings if clean(h)]
# Filter language-related
lang_kw = ['命令', '関数', '構文', '型', 'Class', 'Enum', 'With', 'GoSub', 'Print', 'Dim', 'DirectX', 'Direct3D']
print('\nLanguage-related awtext002 headings:')
for h in heading_texts:
    if any(k in h for k in lang_kw) or re.search(r'(命令文|関数|構造体|クラス)$', h):
        print(f'  {h[:100]}')

# awtext001 might be subheadings
subheadings = re.findall(r'class="awspan awtext001"[^>]*>(.*?)</span>', content, re.I|re.S)
print(f'\nawtext001 subheadings: {len(subheadings)}')

# Look for page breaks / topic separators
seps = ['page-break', 'awpage', 'topic', 'Topic', 'TOPIC', 'new-page', 'section-break']
for s in seps:
    n = content.lower().count(s.lower())
    if n: print(f'Separator {s}: {n}')

# Count unique title-like patterns at start of sections
# Look for bold topic names followed by category
bold_topics = re.findall(
    r'awtext002[^>]*>([^<]{2,80}(?:命令文|関数|構造体|クラス|定数|イベント|プロパティ|メソッド))',
    content, re.I
)
print(f'\nBold topic headers: {len(bold_topics)}')
for b in sorted(set(clean(x) for x in bold_topics))[:80]:
    print(f'  {b}')
