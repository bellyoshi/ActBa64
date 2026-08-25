# -*- coding: utf-8 -*-
"""Final ActiveBasic 4.20 BasicHelp.html extractor - splits by chmtopic anchors."""
import re, json, sys, io
from html import unescape
from collections import defaultdict

PATH = r'c:\Users\bellm\Downloads\BasicHelp.html'
OUT = r'c:\Users\bellm\source\repos\bellyoshi\ActBa64\tools\basichelp_final.json'

def clean(t):
    t = re.sub(r'<br\s*/?>', '\n', t, flags=re.I)
    t = re.sub(r'</?(?:p|div|tr|td|li)[^>]*>', '\n', t, flags=re.I)
    t = re.sub(r'<[^>]+>', '', t)
    t = unescape(t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    return t.strip()

def categorize(name):
    rules = [
        ('statement', r'命令文|命令語|ステートメント|スチEートメント'),
        ('function', r'関数$'),
        ('struct', r'構造体$'),
        ('class', r'クラス$'),
        ('constant', r'定数$'),
        ('event', r'イベント$'),
        ('property', r'プロパティ$'),
        ('method', r'メソッド$'),
        ('operator', r'演算子$'),
        ('directive', r'ディレクティブ|#'),
        ('type', r'基本型|データ型|型$|型一覧|型変数'),
        ('enum', r'列挙|Enum'),
        ('syntax', r'構文|言語|文法'),
        ('rule', r'行番号|ラベル|コメント|識別子|予約語|演算子の優先|文字列|ポインタ'),
        ('file_io', r'ファイル|Open|Close|Print|Input'),
        ('directx', r'DirectX|Direct3D|D3D|DirectDraw|DirectSound|DirectInput|CAudio|CImage|CMesh|CListener|CRect'),
        ('gui', r'Form|Dialog|Button|Window|GUI|ウィンドウ|コントロール|CForm|CDialog'),
        ('win32', r'Win32|Declare|API|メッセージ：'),
        ('macro', r'マクロ|#define'),
    ]
    for cat, pat in rules:
        if re.search(pat, name, re.I):
            return cat
    return 'other'

def extract_signature(text, name):
    base = name.rstrip('$').split('(')[0].split(' ')[0]
    for pat in [
        rf'\b{re.escape(base)}\s*\([^)]{{0,200}}\)',
        rf'{re.escape(base)}\s+[^\n]{{0,100}}',
    ]:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(0).strip()
    return ''

def assess_documentation(text, name):
    """Rate how clearly a topic is documented."""
    if len(text) < 50:
        return False, 'minimal'
    has_syntax = any(k in text for k in ['構文', '書式', '形式', 'Format', 'format'])
    has_params = any(k in text for k in ['引数', 'パラメータ', 'param', 'Param', '戻り値', '戻り'])
    has_example = any(k in text for k in ['例', 'Example', 'example', 'サンプル'])
    has_desc = len(text) > 200
    if has_syntax and (has_params or has_example):
        return True, 'clear'
    if has_desc and (has_syntax or has_params):
        return True, 'partial'
    if has_desc:
        return True, 'partial'
    return False, 'minimal'

def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    with open(PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract TOC links
    toc = {}
    for href, text in re.findall(r'<a[^>]+href="(#chmtopic\d+)"[^>]*>(.*?)</a>', content, re.I|re.S):
        t = clean(text)
        if t and href not in toc:
            toc[href] = t
    
    print(f"TOC entries: {len(toc)}")
    
    # Split content by chmtopic anchors
    topic_pattern = re.compile(r'<a\s+name="(chmtopic\d+)"[^>]*>', re.I)
    splits = []
    last_id = None
    last_pos = 0
    for m in topic_pattern.finditer(content):
        if last_id:
            splits.append((last_id, content[last_pos:m.start()]))
        last_id = m.group(1)
        last_pos = m.start()
    if last_id:
        splits.append((last_id, content[last_pos:]))
    
    print(f"Topic sections: {len(splits)}")
    
    topics = []
    for topic_id, raw in splits:
        name = toc.get('#' + topic_id, topic_id)
        text = clean(raw)
        cat = categorize(name)
        sig = extract_signature(text, name)
        clear, quality = assess_documentation(text, name)
        topics.append({
            'id': topic_id,
            'name': name,
            'category': cat,
            'signature': sig,
            'clearly_documented': clear,
            'doc_quality': quality,
            'text_length': len(text),
            'preview': text[:600],
        })
    
    # Organize by category
    by_cat = defaultdict(list)
    for t in topics:
        by_cat[t['category']].append(t)
    
    # Language syntax features (statements, directives, keywords)
    syntax_cats = ['statement', 'directive', 'syntax', 'type', 'enum', 'operator', 'rule', 'macro', 'file_io']
    syntax_features = []
    for cat in syntax_cats:
        for t in by_cat.get(cat, []):
            syntax_features.append(t)
    
    # Also add statement-like topics from 'other' that match known keywords
    LANG_KW = [
        '#strict', '#define', '#include', '#if', '#else', '#endif', '#region', '#endregion',
        'GoSub', 'Return', 'Goto', 'With', 'Class', 'Enum', 'TypeDef', 'Let', 'ByRef', 'ByVal',
        'Dim', 'ReDim', 'Static', 'Const', 'Function', 'Sub', 'If', 'Select Case',
        'For', 'Next', 'While', 'Wend', 'Do', 'Loop', 'Until',
        'Print', 'Input', 'Open', 'Close', 'Write', 'Line Input',
        'Type', 'End Type', 'End Class', 'End Enum', 'End With',
        'New', 'Delete', 'Declare', 'Call', 'AddressOf',
        'Public', 'Private', 'Protected', 'Property', 'Get', 'Set',
        'On Error', 'Resume', 'Exit', 'Continue', 'Stop', 'End', 'Rem',
        'Using', 'SyncLock', 'Try', 'Catch', 'Finally', 'Throw',
        'AddHandler', 'RemoveHandler', 'RaiseEvent', 'Event',
        'Operator', 'DirectCast', 'CType', 'TypeOf', 'Is', 'IsNot',
        'Me', 'MyBase', 'Nothing', 'Null', 'True', 'False',
        'Optional', 'ParamArray', 'Implements', 'Interface', 'Shared', 'Override',
    ]
    for t in topics:
        for kw in LANG_KW:
            if kw.lower() in t['name'].lower() or t['name'].startswith(kw):
                if t not in syntax_features:
                    syntax_features.append(t)
    
    # Built-in functions
    builtins = by_cat.get('function', [])
    # Add memory/pointer functions from statements
    for t in by_cat.get('statement', []):
        if any(k in t['name'] for k in ['GetByte', 'GetWord', 'GetDWord', 'GetSingle', 'GetDouble',
                                          'SetByte', 'SetWord', 'SetDWord', 'SetSingle', 'SetDouble',
                                          'VarPtr', 'StrPtr', 'ObjPtr']):
            builtins.append(t)
    
    # Types and structures
    types = by_cat.get('struct', []) + by_cat.get('type', [])
    # Add basic types from topics mentioning 基本型
    for t in topics:
        if '基本型' in t['name'] or t['name'] in ['Integer', 'Long', 'Single', 'Double', 'String', 'Boolean', 'Byte', 'Pointer']:
            if t not in types:
                types.append(t)
    
    # DirectX/GUI
    dx_gui = by_cat.get('directx', []) + by_cat.get('gui', [])
    for t in topics:
        if any(k in t['name'] for k in ['CAudio', 'CImage', 'CMesh', 'CListener', 'CRectPolygon',
                                          'CInputKeyboard', 'CInputMouse', 'DirectX', 'Direct3D',
                                          'D3DVECTOR', 'D3DMATRIX', 'D3DCOLOR']):
            if t not in dx_gui:
                dx_gui.append(t)
    
    # Rules
    rules = by_cat.get('rule', [])
    for t in topics:
        if any(k in t['preview'][:200] for k in ['行番号', 'ラベル', 'コメント', '識別子', '文字列',
                                                   '改行', '予約語', '優先順位', 'キャスト', '#strict']):
            if t not in rules and t['category'] in ('rule', 'syntax', 'type', 'other', 'statement'):
                rules.append(t)
    
    # Win32 API (sample - top entries)
    win32 = by_cat.get('win32', []) + [t for t in by_cat.get('function', []) if 'Lib' in t.get('preview', '')]
    
    # Classes
    classes = by_cat.get('class', [])
    
    # Constants
    constants = by_cat.get('constant', [])
    
    # Events
    events = by_cat.get('event', [])
    
    result = {
        'metadata': {
            'source': PATH,
            'total_topics': len(topics),
            'toc_entries': len(toc),
            'note': 'ActiveBasic help file (CHM export). Version 4.20 inferred from user request; file title shows Win32 message help.',
        },
        'syntax_features': [{k: v for k, v in t.items() if k != 'preview'} | {'preview': t['preview'][:300]} 
                              for t in sorted(syntax_features, key=lambda x: x['name'])],
        'builtin_functions': [{k: v for k, v in t.items() if k != 'preview'} | {'preview': t['preview'][:300]}
                              for t in sorted(builtins, key=lambda x: x['name'])],
        'types_and_structures': [{k: v for k, v in t.items() if k != 'preview'} | {'preview': t['preview'][:300]}
                                  for t in sorted(types, key=lambda x: x['name'])],
        'classes': [{k: v for k, v in t.items() if k != 'preview'} | {'preview': t['preview'][:300]}
                    for t in sorted(classes, key=lambda x: x['name'])],
        'directx_gui': [{k: v for k, v in t.items() if k != 'preview'} | {'preview': t['preview'][:300]}
                        for t in sorted(dx_gui, key=lambda x: x['name'])],
        'language_rules': [{k: v for k, v in t.items() if k != 'preview'} | {'preview': t['preview'][:400]}
                           for t in sorted(rules, key=lambda x: x['name'])[:80]],
        'constants_sample': [{k: v for k, v in t.items() if k != 'preview'} | {'preview': t['preview'][:200]}
                             for t in sorted(constants, key=lambda x: x['name'])[:100]],
        'events': [{k: v for k, v in t.items() if k != 'preview'} | {'preview': t['preview'][:200]}
                   for t in sorted(events, key=lambda x: x['name'])],
        'win32_api_sample': [{k: v for k, v in t.items() if k != 'preview'} | {'preview': t['preview'][:200]}
                             for t in sorted(win32, key=lambda x: x['name'])[:80]],
        'category_counts': {k: len(v) for k, v in sorted(by_cat.items())},
        'full_toc': sorted(toc.items(), key=lambda x: int(re.search(r'\d+', x[0]).group())),
    }
    
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Written {OUT}")
    
    # Print summary
    print("\n" + "="*70)
    print("ACTIVEBASIC BasicHelp.html - LANGUAGE SPECIFICATION EXTRACTION")
    print("="*70)
    print(f"\nTotal topics: {len(topics)}")
    print(f"Category counts: {dict(result['category_counts'])}")
    
    def print_section(title, items, limit=60):
        print(f"\n{'='*70}")
        print(f"{title} ({len(items)} items)")
        print('='*70)
        for t in items[:limit]:
            doc = '✓' if t['clearly_documented'] else '✗'
            q = t.get('doc_quality', '?')
            sig = t.get('signature', '')[:55]
            print(f"  [{doc}/{q:7}] {t['name'][:55]:55} {sig}")
        if len(items) > limit:
            print(f"  ... +{len(items)-limit} more")
    
    print_section("1. LANGUAGE SYNTAX FEATURES", syntax_features)
    print_section("2. BUILT-IN FUNCTIONS", builtins)
    print_section("3. TYPES AND DATA STRUCTURES", types)
    print_section("4. CLASSES", classes)
    print_section("5. DIRECTX/GUI FEATURES", dx_gui)
    print_section("6. LANGUAGE RULES", rules, limit=40)
    print_section("7. EVENTS", events, limit=30)
    
    # Print full TOC language-related entries
    print(f"\n{'='*70}")
    print("TABLE OF CONTENTS - Language-related entries")
    print('='*70)
    lang_toc = [(h, n) for h, n in result['full_toc'] 
                if categorize(n) in syntax_cats + ['function', 'struct', 'class', 'enum', 'directx', 'gui', 'rule']]
    for href, name in lang_toc[:100]:
        print(f"  {name}")
    if len(lang_toc) > 100:
        print(f"  ... +{len(lang_toc)-100} more")

if __name__ == '__main__':
    main()
