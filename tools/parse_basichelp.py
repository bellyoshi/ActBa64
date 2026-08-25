"""Parse ActiveBasic BasicHelp.html and extract language specification."""
import re
import json
import sys
from html import unescape
from collections import defaultdict, Counter

PATH = r'c:\Users\bellm\Downloads\BasicHelp.html'

def clean_html(text):
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_all(pattern, content, flags=re.I|re.S):
    return [clean_html(m) for m in re.findall(pattern, content, flags)]

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'explore'
    
    with open(PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    print(f"File size: {len(content):,} chars")
    
    if mode == 'explore':
        title = re.search(r'<title[^>]*>(.*?)</title>', content, re.I|re.S)
        print('Title:', clean_html(title.group(1)) if title else 'N/A')
        
        # All heading levels
        for tag in ['h1','h2','h3','h4','h5','h6']:
            heads = extract_all(rf'<{tag}[^>]*>(.*?)</{tag}>', content)
            print(f"\n{tag.upper()}: {len(heads)} total")
            for h in heads[:15]:
                print(f"  - {h[:120]}")
        
        # Links with href
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', content, re.I|re.S)
        print(f"\nTotal links: {len(links)}")
        href_samples = Counter()
        for href, text in links[:5000]:
            t = clean_html(text)
            if t and len(t) < 80:
                href_samples[t] += 1
        print("Top link texts:")
        for t, c in href_samples.most_common(40):
            print(f"  [{c}] {t}")
        
        # Look for topic/article divs
        for cls in ['topic', 'article', 'content', 'body', 'section', 'entry']:
            n = len(re.findall(rf'class="[^"]*{cls}[^"]*"', content, re.I))
            if n: print(f"class*='{cls}': {n}")
        
        # Japanese text blocks
        jp = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{3,}')
        jp_sections = set()
        for m in jp.finditer(content):
            start = max(0, m.start()-100)
            end = min(len(content), m.end()+100)
            ctx = clean_html(content[start:end])
            if len(ctx) > 5 and len(ctx) < 200:
                jp_sections.add(ctx)
        print(f"\nJapanese context samples ({len(jp_sections)}):")
        for s in sorted(jp_sections)[:50]:
            print(f"  {s[:150]}")
        return

    if mode == 'full':
        result = parse_full(content)
        out = r'c:\Users\bellm\source\repos\bellyoshi\ActBa64\tools\basichelp_extract.json'
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Written to {out}")
        print_summary(result)
        return

def parse_full(content):
    """Full extraction of language features."""
    result = {
        'metadata': {},
        'syntax': [],
        'directives': [],
        'statements': [],
        'keywords': [],
        'builtin_functions': [],
        'types': [],
        'directx_gui': [],
        'rules': [],
        'sections': [],
    }
    
    title = re.search(r'<title[^>]*>(.*?)</title>', content, re.I|re.S)
    result['metadata']['title'] = clean_html(title.group(1)) if title else ''
    
    # Version info
    for pat in [r'ActiveBasic\s*[\d.]+', r'Version\s*[\d.]+', r'4\.20', r'4\.2\d']:
        for m in re.finditer(pat, content[:50000], re.I):
            result['metadata'].setdefault('version_mentions', []).append(m.group(0))
    
    # Extract all sections by headings
    section_pattern = re.compile(
        r'<h([1-6])[^>]*>(.*?)</h\1>(.*?)(?=<h[1-6][^>]*>|$)',
        re.I | re.S
    )
    
    sections = []
    for level, heading_raw, body_raw in section_pattern.finditer(content):
        heading = clean_html(heading_raw)
        body = clean_html(body_raw)
        if heading:
            sections.append({
                'level': int(level),
                'heading': heading,
                'body_preview': body[:2000],
                'body_len': len(body_raw),
            })
    result['sections'] = sections
    print(f"Found {len(sections)} sections")
    
    # Known syntax keywords and directives
    SYNTAX_KEYWORDS = [
        '#strict', '#define', '#include', '#if', '#else', '#endif', '#region', '#endregion',
        'GoSub', 'Return', 'With', 'Class', 'Enum', 'TypeDef', 'Let', 'ByRef', 'ByVal',
        'Dim', 'ReDim', 'Static', 'Const', 'Function', 'Sub', 'End', 'If', 'Then', 'Else',
        'ElseIf', 'Select', 'Case', 'For', 'Next', 'While', 'Wend', 'Do', 'Loop', 'Until',
        'Exit', 'Continue', 'On', 'Error', 'Resume', 'Goto', 'Gosub',
        'New', 'Delete', 'Me', 'MyBase', 'Implements', 'Interface', 'Property', 'Get', 'Set',
        'Public', 'Private', 'Protected', 'Shared', 'Override', 'MustOverride',
        'As', 'Optional', 'ParamArray', 'Is', 'Not', 'And', 'Or', 'Xor', 'Mod',
        'True', 'False', 'Nothing', 'Null',
        'Print', 'Input', 'Open', 'Close', 'Write', 'Line Input',
        'Type', 'End Type', 'Union', 'End Union',
        'DoEvents', 'Sleep', 'Stop', 'End', 'Rem', "'",
        'Call', 'Declare', 'Lib', 'Alias', 'AddressOf',
        'Using', 'Namespace', 'Module', 'Structure',
        'Try', 'Catch', 'Finally', 'Throw',
        'SyncLock', 'Lock', 'Unlock',
        'AddHandler', 'RemoveHandler', 'RaiseEvent', 'Event',
        'Operator', 'DirectCast', 'CType', 'TypeOf',
        'Step', 'To', 'Each', 'In',
    ]
    
    DIRECTIVES = ['#strict', '#define', '#include', '#if', '#else', '#endif', '#region', '#endregion',
                  '#pragma', '#const', '#rem', '#option']
    
    # Search for each keyword in content with context
    for kw in SYNTAX_KEYWORDS:
        # Case-sensitive search for keywords as whole words
        pat = re.compile(r'\b' + re.escape(kw.lstrip('#')) + r'\b' if not kw.startswith('#') 
                        else re.escape(kw), re.I if not kw.startswith('#') else 0)
        matches = list(pat.finditer(content))
        if matches:
            # Get best context from first few matches
            contexts = []
            for m in matches[:3]:
                start = max(0, m.start() - 200)
                end = min(len(content), m.end() + 400)
                ctx = clean_html(content[start:end])
                contexts.append(ctx[:500])
            
            # Find if there's a dedicated section
            dedicated = any(kw.lower() in s['heading'].lower() for s in sections)
            
            entry = {
                'name': kw,
                'occurrences': len(matches),
                'has_dedicated_section': dedicated,
                'clearly_documented': dedicated or any(len(c) > 100 for c in contexts),
                'context_samples': contexts[:2],
            }
            
            if kw.startswith('#') or kw in DIRECTIVES:
                result['directives'].append(entry)
            elif kw in ['Print', 'Input', 'Open', 'Close', 'Write', 'Dim', 'ReDim', 'If', 'For', 'While', 'Do', 'With', 'Class', 'Enum', 'TypeDef', 'Function', 'Sub', 'GoSub', 'Return', 'Let', 'ByRef']:
                result['statements'].append(entry)
            else:
                result['keywords'].append(entry)
    
    # Built-in functions - search for Function/Sub patterns in help
    BUILTIN_PATTERNS = [
        # String
        r'\b(Len|Left\$?|Right\$?|Mid\$?|InStr|Replace|Trim|LTrim|RTrim|UCase|LCase|Str\$?|Val|Format\$?|Space\$?|String\$?|Asc|Chr\$?|Hex\$?|Oct\$?|Bin\$?|Split|Join|InStrRev|StrReverse|StrComp|Filter|GetSetting|SaveSetting)\s*\(',
        # Math
        r'\b(Abs|Sgn|Int|Fix|Round|Rnd|Randomize|Sqr|Exp|Log|Sin|Cos|Tan|Atn|Pi)\s*\(',
        # File I/O
        r'\b(Open|Close|Print\s*#|Input\s*#|Line\s*Input|Write\s*#|Get\s*#|Put\s*#|Seek|Loc|LOF|Eof|FreeFile|FileLen|Dir\$?|Kill|Name|MkDir|RmDir|ChDir|CurDir\$?|FileAttr|FileDateTime|FileCopy|SetAttr|GetAttr)\b',
        # Array
        r'\b(UBound|LBound|Array|Erase|IsArray|Redim\s*Preserve)\b',
        # Type conversion
        r'\b(CInt|CLng|CSng|CDbl|CBool|CStr|CByte|CShort|CType|DirectCast|TypeName|VarType|IsNumeric|IsDate|IsEmpty|IsNull|IsObject|IsArray|IsNothing)\b',
        # Date/Time
        r'\b(Now|Date|Time|Timer|DateAdd|DateDiff|DatePart|DateSerial|TimeSerial|Year|Month|Day|Hour|Minute|Second|Weekday)\b',
        # Misc
        r'\b(MsgBox|InputBox|Beep|Shell|Environ\$?|Command\$?|DoEvents|Sleep|Stop|End|Random|Choose|Switch|IIf|Eval|Execute)\b',
        # Win32
        r'\b(Win[A-Z][a-zA-Z0-9_]*|GetWindow|SetWindow|SendMessage|PostMessage|FindWindow|CreateWindow|LoadLibrary|GetProcAddress|VirtualAlloc|CopyMemory|PeekMessage|DispatchMessage|RegisterClass|DefWindowProc)\b',
        # DirectX related
        r'\b(DX[A-Z][a-zA-Z0-9_]*|DirectX|Direct3D|DirectDraw|DirectSound|DirectInput|DirectPlay|DirectShow|D3D[A-Z][a-zA-Z0-9_]*|IDirect[A-Z][a-zA-Z0-9_]*)\b',
        # GUI
        r'\b(Form|Button|Label|TextBox|ListBox|ComboBox|CheckBox|RadioButton|PictureBox|Timer|Menu|Dialog|Window|Control|Canvas|Panel|ScrollBar|ProgressBar|StatusBar|ToolBar|TreeView|ListView|TabControl|ImageList|NotifyIcon|ContextMenu)\b',
    ]
    
    found_builtins = {}
    for pat_str in BUILTIN_PATTERNS:
        pat = re.compile(pat_str, re.I)
        for m in pat.finditer(content):
            name = m.group(1) if m.lastindex else m.group(0)
            name = name.strip()
            if name not in found_builtins:
                start = max(0, m.start() - 300)
                end = min(len(content), m.end() + 600)
                ctx = clean_html(content[start:end])
                # Try to extract signature
                sig_match = re.search(
                    rf'{re.escape(name)}\s*\([^)]*\)',
                    ctx, re.I
                )
                sig = sig_match.group(0) if sig_match else ''
                
                dedicated = any(name.lower() in s['heading'].lower() for s in sections)
                found_builtins[name] = {
                    'name': name,
                    'signature': sig,
                    'has_dedicated_section': dedicated,
                    'clearly_documented': dedicated or (sig != '' and len(ctx) > 150),
                    'context': ctx[:600],
                }
    
    result['builtin_functions'] = sorted(found_builtins.values(), key=lambda x: x['name'].lower())
    
    # Types
    TYPE_PATTERNS = [
        r'\b(Integer|Long|Single|Double|String|Boolean|Byte|Short|Char|Pointer|Handle|Variant|Object|Any)\b',
        r'\b(WCHAR|DWORD|WORD|BYTE|BOOL|HANDLE|HWND|HDC|HINSTANCE|LPSTR|LPCSTR|LPVOID|UINT|INT|LONG|ULONG|SIZE_T)\b',
        r'\b(D3DCOLOR|D3DVECTOR|D3DMATRIX|RECT|POINT|SIZE|COLORREF|MSG|WNDCLASS|PAINTSTRUCT)\b',
    ]
    found_types = {}
    for pat_str in TYPE_PATTERNS:
        pat = re.compile(pat_str)
        for m in pat.finditer(content):
            name = m.group(0)
            if name not in found_types:
                dedicated = any(name.lower() in s['heading'].lower() for s in sections)
                start = max(0, m.start() - 200)
                end = min(len(content), m.end() + 400)
                ctx = clean_html(content[start:end])
                found_types[name] = {
                    'name': name,
                    'has_dedicated_section': dedicated,
                    'clearly_documented': dedicated,
                    'context': ctx[:400],
                }
    result['types'] = sorted(found_types.values(), key=lambda x: x['name'])
    
    # DirectX/GUI sections
    dx_gui_keywords = ['DirectX', 'Direct3D', 'DirectDraw', 'DirectSound', 'DirectInput', 
                       'GUI', 'Form', 'Window', 'Control', 'Dialog', 'Button', 'Label',
                       'D3D', 'グラフィック', 'ウィンドウ', 'コントロール', '画面', '描画']
    for s in sections:
        h = s['heading']
        b = s['body_preview']
        for kw in dx_gui_keywords:
            if kw.lower() in h.lower() or kw in b:
                result['directx_gui'].append({
                    'heading': h,
                    'level': s['level'],
                    'preview': b[:500],
                    'keyword_matched': kw,
                })
                break
    
    # Language rules
    RULE_KEYWORDS = [
        '行番号', 'line number', '文字列', 'string', 'コメント', 'comment',
        '識別子', 'identifier', '予約語', 'reserved', '演算子', 'operator',
        '優先順位', 'precedence', '型', 'type conversion', 'キャスト', 'cast',
        '配列', 'array', 'インデックス', 'index', 'オプション', 'option',
        'コンパイル', 'compile', '実行', 'runtime', 'エラー', 'error handling',
        'モジュール', 'module', 'スコープ', 'scope', '名前空間', 'namespace',
        '参照', 'reference', 'ポインタ', 'pointer', 'メモリ', 'memory',
        'Unicode', 'Shift-JIS', 'SJIS', 'UTF', '文字コード', 'encoding',
        'ラベル', 'label', 'GoSub', 'Goto',
    ]
    for s in sections:
        h = s['heading']
        b = s['body_preview']
        for kw in RULE_KEYWORDS:
            if kw.lower() in h.lower() or kw in h or kw.lower() in b.lower() or kw in b:
                result['rules'].append({
                    'heading': h,
                    'level': s['level'],
                    'preview': b[:800],
                    'keyword_matched': kw,
                })
                break
    
    # Extract link-based index (often help files have index pages)
    links = re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', content, re.I|re.S)
    index_entries = []
    for href, text in links:
        t = clean_html(text)
        if t and len(t) < 100 and not t.startswith('http'):
            index_entries.append({'text': t, 'href': href})
    result['index_entries'] = index_entries[:2000]
    
    return result

def print_summary(result):
    print("\n=== METADATA ===")
    print(json.dumps(result['metadata'], ensure_ascii=False, indent=2))
    
    print(f"\n=== DIRECTIVES ({len(result['directives'])}) ===")
    for d in sorted(result['directives'], key=lambda x: x['name']):
        doc = 'YES' if d['clearly_documented'] else 'NO'
        sec = 'section' if d['has_dedicated_section'] else ''
        print(f"  {d['name']:20} occ={d['occurrences']:5}  doc={doc} {sec}")
    
    print(f"\n=== STATEMENTS ({len(result['statements'])}) ===")
    for d in sorted(result['statements'], key=lambda x: x['name']):
        doc = 'YES' if d['clearly_documented'] else 'NO'
        sec = 'section' if d['has_dedicated_section'] else ''
        print(f"  {d['name']:20} occ={d['occurrences']:5}  doc={doc} {sec}")
    
    print(f"\n=== KEYWORDS ({len(result['keywords'])}) ===")
    for d in sorted(result['keywords'], key=lambda x: x['name'])[:60]:
        doc = 'YES' if d['clearly_documented'] else 'NO'
        print(f"  {d['name']:20} occ={d['occurrences']:5}  doc={doc}")
    
    print(f"\n=== BUILTIN FUNCTIONS ({len(result['builtin_functions'])}) ===")
    for f in result['builtin_functions']:
        doc = 'YES' if f['clearly_documented'] else 'NO'
        sig = f['signature'][:60] if f['signature'] else ''
        sec = 'section' if f['has_dedicated_section'] else ''
        print(f"  {f['name']:25} doc={doc} {sec}  {sig}")
    
    print(f"\n=== TYPES ({len(result['types'])}) ===")
    for t in result['types']:
        doc = 'YES' if t['clearly_documented'] else 'NO'
        sec = 'section' if t['has_dedicated_section'] else ''
        print(f"  {t['name']:20} doc={doc} {sec}")
    
    print(f"\n=== DIRECTX/GUI SECTIONS ({len(result['directx_gui'])}) ===")
    seen = set()
    for g in result['directx_gui']:
        if g['heading'] not in seen:
            seen.add(g['heading'])
            print(f"  [{g['level']}] {g['heading'][:80]}")
    
    print(f"\n=== RULES SECTIONS ({len(result['rules'])}) ===")
    seen = set()
    for r in result['rules']:
        if r['heading'] not in seen:
            seen.add(r['heading'])
            print(f"  [{r['level']}] {r['heading'][:80]}")

if __name__ == '__main__':
    main()
