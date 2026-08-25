# -*- coding: utf-8 -*-
"""Comprehensive ActiveBasic BasicHelp.html parser."""
import re
import json
import sys
from html import unescape
from collections import defaultdict, Counter

PATH = r'c:\Users\bellm\Downloads\BasicHelp.html'
OUT = r'c:\Users\bellm\source\repos\bellyoshi\ActBa64\tools\basichelp_extract.json'

def clean_html(text):
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'</?(?:p|div|tr|td|li)[^>]*>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    return text.strip()

def extract_spans(content):
    """Extract awtext span contents - these hold the visible text."""
    spans = re.findall(
        r'<span[^>]*class="[^"]*awtext[^"]*"[^>]*>(.*?)</span>',
        content, re.I | re.S
    )
    texts = []
    for s in spans:
        t = clean_html(s)
        if t and len(t) > 1:
            texts.append(t)
    return texts

def extract_links(content):
    links = []
    for href, text in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', content, re.I|re.S):
        t = clean_html(text)
        if t:
            links.append({'text': t, 'href': href})
    return links

def categorize_link(text):
    """Categorize Japanese help link text."""
    cats = {
        'statement': r'命令文$',
        'function': r'関数$',
        'struct': r'構造体$',
        'class': r'クラス$',
        'constant': r'定数$',
        'event': r'イベント$',
        'property': r'プロパティ$',
        'method': r'メソッド$',
        'operator': r'演算子$',
        'type': r'型$|データ型',
        'directive': r'ディレクティブ|#',
        'message': r'メッセージ$|メッセージ：',
        'enum': r'列挙',
        'module': r'モジュール',
        'variable': r'変数',
        'predefined': r'定義済み|組込|ビルトイン|内部',
        'syntax': r'構文|文法|言語',
        'rule': r'規則|ルール|注意|制約',
        'directx': r'DirectX|Direct3D|D3D|DirectDraw|DirectSound|DirectInput',
        'gui': r'Form|Dialog|Control|Window|GUI|ウィンドウ|コントロール|画面',
        'file_io': r'ファイル|File|Open|Close',
        'string': r'文字列|String',
        'array': r'配列|Array',
        'pointer': r'ポインタ|Pointer',
    }
    for cat, pat in cats.items():
        if re.search(pat, text, re.I):
            return cat
    return 'other'

def find_topic_blocks(content):
    """
    Help topics often appear as bold/large awtext spans followed by description.
    Look for patterns like 'XXX 命令文', 'XXX 関数', etc.
    """
    full_text = clean_html(content)
    
    # Topic header patterns (Japanese ActiveBasic help convention)
    TOPIC_PATTERNS = [
        (r'([A-Za-z_#][\w$]*)\s+命令文', 'statement'),
        (r'([A-Za-z_#][\w$]*)\s+関数', 'function'),
        (r'([A-Za-z_#][\w$]*)\s+構造体', 'struct'),
        (r'([A-Za-z_#][\w$]*)\s+クラス', 'class'),
        (r'([A-Za-z_#][\w$]*)\s+定数', 'constant'),
        (r'([A-Za-z_#][\w$]*)\s+イベント', 'event'),
        (r'([A-Za-z_#][\w$]*)\s+プロパティ', 'property'),
        (r'([A-Za-z_#][\w$]*)\s+メソッド', 'method'),
        (r'([A-Za-z_#][\w$]*)\s+演算子', 'operator'),
        (r'([A-Za-z_#][\w$]*)\s+型', 'type'),
        (r'(#[A-Za-z_][\w]*)', 'directive'),
    ]
    
    topics = {}
    for pat, cat in TOPIC_PATTERNS:
        for m in re.finditer(pat, full_text):
            name = m.group(1)
            key = (name, cat)
            if key not in topics:
                start = m.start()
                ctx = full_text[max(0,start-50):min(len(full_text),start+800)]
                topics[key] = {
                    'name': name,
                    'category': cat,
                    'context': ctx,
                }
    return list(topics.values())

def extract_signatures(content):
    """Extract function/method signatures from help text."""
    full = clean_html(content)
    sigs = {}
    # Function call patterns
    for m in re.finditer(
        r'\b([A-Za-z_][\w$]*)\s*\(\s*([^)]{0,300})\)',
        full
    ):
        name = m.group(1)
        args = m.group(2).strip()
        if name in sigs:
            continue
        # Filter noise - real API names
        if len(name) < 2 or name in ('if', 'for', 'while', 'case', 'then', 'span', 'style', 'class'):
            continue
        if re.match(r'^[A-Z#]|^[a-z]+[$]?$', name) or name.startswith('Get') or name.startswith('Set'):
            sigs[name] = f"{name}({args})"
    return sigs

def search_language_features(content, links):
    """Search for core language features."""
    
    # Language keywords/statements to find
    LANG_FEATURES = {
        'directives': [
            '#strict', '#define', '#include', '#if', '#else', '#elif', '#endif',
            '#region', '#endregion', '#pragma', '#const', '#rem', '#option',
        ],
        'statements': [
            'Dim', 'ReDim', 'Static', 'Const', 'Let', 'Set',
            'If', 'Then', 'Else', 'ElseIf', 'End If', 'Select Case', 'Case', 'End Select',
            'For', 'Next', 'Step', 'To', 'Each', 'In',
            'While', 'Wend', 'Do', 'Loop', 'Until',
            'GoSub', 'Return', 'Goto', 'On GoSub', 'On Goto',
            'With', 'End With',
            'Function', 'End Function', 'Sub', 'End Sub',
            'Class', 'End Class', 'Enum', 'End Enum',
            'Type', 'End Type', 'TypeDef', 'Union', 'End Union',
            'Property', 'Get', 'Set', 'End Property',
            'Print', 'Input', 'Open', 'Close', 'Write', 'Line Input',
            'Exit', 'Continue', 'Stop', 'End', 'Rem',
            'Call', 'Declare', 'Lib', 'Alias', 'AddressOf',
            'New', 'Delete', 'Implements', 'Interface',
            'Public', 'Private', 'Protected', 'Shared',
            'ByRef', 'ByVal', 'Optional', 'ParamArray',
            'On Error', 'Resume', 'Try', 'Catch', 'Finally', 'Throw',
            'SyncLock', 'Using', 'Namespace', 'Module',
            'AddHandler', 'RemoveHandler', 'RaiseEvent', 'Event',
            'Operator', 'DirectCast', 'CType', 'TypeOf', 'Is', 'IsNot',
            'Me', 'MyBase', 'Nothing', 'Null', 'True', 'False',
            'DoEvents', 'Sleep', 'Lock', 'Unlock',
        ],
        'types': [
            'Integer', 'Long', 'Single', 'Double', 'String', 'Boolean',
            'Byte', 'Short', 'Char', 'Pointer', 'Handle', 'Variant', 'Object', 'Any',
            'WCHAR', 'DWORD', 'WORD', 'BOOL', 'HANDLE', 'HWND', 'HDC', 'HINSTANCE',
            'LPSTR', 'LPCSTR', 'LPVOID', 'UINT', 'INT', 'LONG', 'ULONG',
            'D3DCOLOR', 'D3DVECTOR', 'D3DMATRIX', 'RECT', 'POINT', 'SIZE',
            'COLORREF', 'MSG', 'WNDCLASS', 'PAINTSTRUCT', 'FILETIME', 'SYSTEMTIME',
            'BITMAPINFO', 'LOGFONT', 'WNDCLASSEX', 'POINTAPI',
        ],
        'builtin_functions': [
            # String
            'Len', 'Left$', 'Right$', 'Mid$', 'InStr', 'InStrRev', 'Replace',
            'Trim$', 'LTrim$', 'RTrim$', 'UCase$', 'LCase$', 'Str$', 'Val',
            'Format$', 'Space$', 'String$', 'Asc', 'Chr$', 'Hex$', 'Oct$', 'Bin$',
            'Split', 'Join', 'StrReverse', 'StrComp', 'Filter',
            # Math
            'Abs', 'Sgn', 'Int', 'Fix', 'Round', 'Rnd', 'Randomize',
            'Sqr', 'Exp', 'Log', 'Sin', 'Cos', 'Tan', 'Atn',
            # File I/O
            'FreeFile', 'FileLen', 'LOF', 'Loc', 'Seek', 'Eof',
            'Dir$', 'Kill', 'Name', 'MkDir', 'RmDir', 'ChDir', 'CurDir$',
            'FileCopy', 'SetAttr', 'GetAttr', 'FileDateTime', 'FileAttr',
            # Array
            'UBound', 'LBound', 'Array', 'Erase', 'IsArray',
            # Type
            'CInt', 'CLng', 'CSng', 'CDbl', 'CBool', 'CStr', 'CByte', 'CShort',
            'TypeName', 'VarType', 'IsNumeric', 'IsDate', 'IsEmpty', 'IsNull',
            'IsObject', 'IsNothing',
            # Date/Time
            'Now', 'Date$', 'Time$', 'Timer', 'DateAdd', 'DateDiff', 'DatePart',
            'DateSerial', 'TimeSerial', 'Year', 'Month', 'Day', 'Hour', 'Minute', 'Second', 'Weekday',
            # Misc
            'MsgBox', 'InputBox', 'Beep', 'Shell', 'Environ$', 'Command$',
            'DoEvents', 'Sleep', 'Choose', 'Switch', 'IIf', 'Eval', 'Execute',
            'GetSetting', 'SaveSetting',
            # Memory/Pointer (ActiveBasic specific)
            'GetByte', 'GetWord', 'GetDWord', 'GetSingle', 'GetDouble',
            'SetByte', 'SetWord', 'SetDWord', 'SetSingle', 'SetDouble',
            'CopyMemory', 'MoveMemory', 'ZeroMemory', 'AllocMemory', 'FreeMemory',
            'AddressOf', 'VarPtr', 'StrPtr', 'ObjPtr',
            # Win32 common
            'Load', 'LoadLibrary', 'GetProcAddress', 'FreeLibrary',
            'GetLastError', 'CloseHandle', 'CreateFile', 'ReadFile', 'WriteFile',
            'GlobalAlloc', 'GlobalLock', 'GlobalUnlock', 'GlobalFree',
            'HeapAlloc', 'HeapFree', 'VirtualAlloc', 'VirtualFree',
            'SendMessage', 'PostMessage', 'FindWindow', 'GetWindow', 'SetWindow',
            'GetMessage', 'DispatchMessage', 'PeekMessage', 'TranslateMessage',
            'RegisterClass', 'CreateWindow', 'DefWindowProc', 'DestroyWindow',
            'BeginPaint', 'EndPaint', 'InvalidateRect', 'UpdateWindow',
            'OpenClipboard', 'CloseClipboard', 'SetClipboardData', 'GetClipboardData',
            'DeleteObject', 'SelectObject', 'CreatePen', 'CreateBrush', 'CreateFont',
            'LoadImage', 'BitBlt', 'StretchBlt', 'TextOut', 'DrawText',
            'DestroyIcon', 'mciSendCommand',
        ],
        'directx_gui': [
            'DirectX', 'Direct3D', 'DirectDraw', 'DirectSound', 'DirectInput', 'DirectPlay',
            'CDirectX', 'CDirect3D', 'CDirectDraw', 'CDirectSound', 'CDirectInput',
            'CAudio', 'CListener', 'CSurface', 'CTexture', 'CDevice', 'CSprite',
            'D3DVECTOR', 'D3DMATRIX', 'D3DCOLOR', 'D3DVIEWPORT',
            'Form', 'Dialog', 'Button', 'Label', 'TextBox', 'ListBox', 'ComboBox',
            'CheckBox', 'RadioButton', 'PictureBox', 'Timer', 'Menu', 'Window',
            'Control', 'Canvas', 'Panel', 'ScrollBar', 'ProgressBar', 'StatusBar',
            'ToolBar', 'TreeView', 'ListView', 'TabControl', 'ImageList',
            'CForm', 'CDialog', 'CButton', 'CLabel', 'CTextBox', 'CListBox',
            'CComboBox', 'CCheckBox', 'CRadioButton', 'CPictureBox', 'CTimer',
            'CWindow', 'CControl', 'CCanvas', 'CPanel',
        ],
        'rules_keywords': [
            '行番号', 'ラベル', '文字列', '文字列リテラル', 'コメント',
            '識別子', '予約語', '演算子', '優先順位', '型変換', 'キャスト',
            '配列', 'モジュール', 'スコープ', '参照', 'ポインタ',
            'Unicode', 'Shift-JIS', 'SJIS', '文字コード', 'エンコーディング',
            'コンパイル', '実行', 'エラー処理', 'オプション',
            'Public', 'Private', 'アクセス', 'オーバーロード', 'オーバーライド',
            '継承', 'ポリモーフィズム', 'デリゲート', 'イベント',
        ],
    }
    
    full = clean_html(content)
    link_texts = {l['text'] for l in links}
    link_text_lower = {t.lower(): t for t in link_texts}
    
    results = {}
    for category, features in LANG_FEATURES.items():
        results[category] = []
        for feat in features:
            # Check link index
            link_match = None
            for suffix in ['命令文', '関数', '構造体', 'クラス', '定数', 'イベント', 'プロパティ', 'メソッド', '型', '']:
                candidate = f"{feat} {suffix}".strip() if suffix else feat
                if candidate in link_texts:
                    link_match = candidate
                    break
                # Also try with $ suffix stripped
                base = feat.rstrip('$')
                candidate2 = f"{base} {suffix}".strip() if suffix else base
                if candidate2 in link_texts:
                    link_match = candidate2
                    break
            
            # Search in content
            pat = re.compile(r'\b' + re.escape(feat.rstrip('$')) + r'\b', re.I)
            matches = list(pat.finditer(full))
            
            # Get context from first substantial match
            context = ''
            signature = ''
            if matches:
                for m in matches:
                    start = max(0, m.start() - 100)
                    end = min(len(full), m.end() + 500)
                    ctx = full[start:end]
                    if len(ctx) > 150:
                        context = ctx
                        break
                if not context and matches:
                    m = matches[0]
                    context = full[max(0,m.start()-100):min(len(full),m.end()+300)]
                
                # Extract signature
                sig_m = re.search(
                    rf'\b{re.escape(feat.rstrip("$"))}\s*\([^)]*\)',
                    context, re.I
                )
                if sig_m:
                    signature = sig_m.group(0)
            
            has_link = link_match is not None
            has_content = len(matches) > 0
            clearly_documented = has_link or (has_content and len(context) > 200 and 
                any(kw in context for kw in ['構文', '書式', '説明', '引数', '戻り', '例', 'パラメータ', '使用方法']))
            
            if has_link or has_content:
                results[category].append({
                    'name': feat,
                    'link_entry': link_match,
                    'occurrences': len(matches),
                    'signature': signature,
                    'clearly_documented': clearly_documented,
                    'has_dedicated_page': has_link,
                    'context_preview': context[:500] if context else '',
                })
    
    return results

def extract_link_index(links):
    """Organize all help links by category."""
    by_cat = defaultdict(list)
    for l in links:
        cat = categorize_link(l['text'])
        by_cat[cat].append(l['text'])
    return {k: sorted(set(v)) for k, v in by_cat.items()}

def extract_version_info(content):
    info = {}
    for pat in [
        r'ActiveBasic\s*([\d.]+)',
        r'Version\s*([\d.]+)',
        r'バージョン\s*([\d.]+)',
        r'(\d+\.\d+)\s*(?:版|リリース)',
    ]:
        for m in re.finditer(pat, content[:100000], re.I):
            info.setdefault('versions', []).append(m.group(0))
    return info

def main():
    print("Loading file...")
    with open(PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    print(f"Loaded {len(content):,} chars")
    
    print("Extracting links...")
    links = extract_links(content)
    print(f"Found {len(links)} links")
    
    print("Extracting link index...")
    link_index = extract_link_index(links)
    
    print("Finding topic blocks...")
    topics = find_topic_blocks(content)
    print(f"Found {len(topics)} topic blocks")
    
    print("Searching language features...")
    features = search_language_features(content, links)
    
    print("Extracting signatures...")
    all_sigs = extract_signatures(content)
    
    version_info = extract_version_info(content)
    
    # Extract language-spec related links specifically
    lang_links = []
    for l in links:
        t = l['text']
        if any(kw in t for kw in ['命令文', '構文', '言語', '文法', '型', '演算子', '命令', 
                                    'ディレクティブ', '#', 'GoSub', 'With', 'Class', 'Enum',
                                    'TypeDef', 'Let', 'ByRef', 'Print', 'Input', 'Dim',
                                    'Function', 'Sub', 'ReDim', 'Const', 'Static']):
            lang_links.append(l)
    
    # DirectX/GUI links
    dx_links = [l for l in links if categorize_link(l['text']) in ('directx', 'gui', 'class', 'struct')
                and any(kw in l['text'] for kw in ['Direct', 'D3D', 'CForm', 'CDialog', 'CAudio', 
                     'CSurface', 'CTexture', 'CDevice', 'Form', 'Dialog', 'Button', 'Window',
                     'DirectX', 'Direct3D', 'DirectDraw', 'DirectSound', 'DirectInput',
                     'D3D', 'GUI', 'ウィンドウ', 'コントロール', '画面', '描画', 'グラフィック'])]
    
    result = {
        'metadata': {
            'source': PATH,
            'size_chars': len(content),
            'total_links': len(links),
            'version_info': version_info,
        },
        'link_index_by_category': link_index,
        'language_links': lang_links,
        'directx_gui_links': dx_links,
        'topics_from_patterns': topics,
        'features': features,
        'all_signatures_sample': dict(list(all_sigs.items())[:500]),
    }
    
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Written to {OUT}")
    
    # Print summary to stdout (UTF-8)
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("\n" + "="*60)
    print("ACTIVEBASIC BasicHelp.html EXTRACTION SUMMARY")
    print("="*60)
    
    print(f"\nVersion info: {version_info}")
    print(f"Total links: {len(links)}")
    
    print("\n--- LINK INDEX BY CATEGORY ---")
    for cat, items in sorted(link_index.items()):
        print(f"\n[{cat}] ({len(items)} items)")
        for item in items[:30]:
            print(f"  {item}")
        if len(items) > 30:
            print(f"  ... and {len(items)-30} more")
    
    print("\n--- LANGUAGE FEATURES ---")
    for cat, items in features.items():
        documented = sum(1 for i in items if i['clearly_documented'])
        with_page = sum(1 for i in items if i['has_dedicated_page'])
        print(f"\n[{cat}] found={len(items)} documented={documented} with_page={with_page}")
        for item in sorted(items, key=lambda x: x['name']):
            doc = '✓' if item['clearly_documented'] else '✗'
            page = 'PAGE' if item['has_dedicated_page'] else '    '
            sig = item.get('signature', '')[:50]
            print(f"  {doc} {page} {item['name']:25} occ={item['occurrences']:4}  {sig}")

if __name__ == '__main__':
    main()
