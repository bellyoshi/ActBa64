import json, re, os

root = r"C:\Users\bellm\.cursor\projects\c-Users-bellm-source-repos-bellyoshi-ActBa64\agent-transcripts"
pat = re.compile(r"0\s*,\s*1\s*,\s*2|マジック|const\s*で|リテラルを|MAXIDX|LEX_TEXT")

for dirpath, _, files in os.walk(root):
    for f in files:
        if not f.endswith(".jsonl"):
            continue
        path = os.path.join(dirpath, f)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if '"role":"user"' not in line:
                    continue
                if not pat.search(line):
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                texts = []
                for c in o.get("message", {}).get("content", []):
                    if isinstance(c, dict) and c.get("type") == "text":
                        texts.append(c.get("text", "")[:1200])
                if texts:
                    print("---", path, "L" + str(i))
                    print(texts[0][:1200])
                    print()
