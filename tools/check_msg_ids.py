# -*- coding: utf-8 -*-
"""actba64 のメッセージ ID を調べる。

  python tools/check_msg_ids.py          # 食い違いがあれば終了コード 1
  python tools/check_msg_ids.py --list   # ID と英語の文の一覧も出す

調べること:
  - src/actba64/*.abp の Tr$(id, "英語") / Tr1$〜Tr4$ / PvFailName(p, id, "英語")
    - 同じ ID に違う英語の文が付いていないか
    - ID の無い Tr$("...") が残っていないか
  - src/actba64/actba_lang_ja.csv
    - ソースに無い ID、同じ ID の重複
    - {0} などの置き換えの番号が英語の文と同じか
    - 訳の無い ID（警告のみ）
"""
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "actba64")
CSV_JA = os.path.join(SRC, "actba_lang_ja.csv")

CALL = re.compile(r'(?:\bTr\d?\$\(|PvFailName\(p, )(\d+), "((?:[^"]|"")*)"')
NO_ID = re.compile(r'\bTr\d?\$\("')
HOLE = re.compile(r"(?<!\{)\{(\d+)\}")


def read_text(path):
    raw = open(path, "rb").read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp932")


def holes(s):
    return sorted(set(HOLE.findall(s)))


def scan_source(errors):
    msgs = {}
    for path in sorted(glob.glob(os.path.join(SRC, "*.abp"))):
        name = os.path.basename(path)
        for n, line in enumerate(read_text(path).splitlines(), 1):
            if line.lstrip().startswith("'"):
                continue
            if NO_ID.search(line):
                errors.append(f"{name}:{n}: Tr$ without a message ID")
            for m in CALL.finditer(line):
                mid, en = int(m.group(1)), m.group(2).replace('""', '"')
                if mid in msgs and msgs[mid][0] != en:
                    errors.append(f"{name}:{n}: ID {mid} has another text (first at {msgs[mid][1]})")
                msgs.setdefault(mid, (en, f"{name}:{n}"))
    return msgs


def scan_csv(msgs, errors, warnings):
    seen = set()
    with open(CSV_JA, encoding="utf-8-sig", newline="") as f:
        for n, row in enumerate(csv.reader(f), 1):
            if not row or row[0].startswith("#") or not row[0].strip().isdigit():
                continue
            mid = int(row[0])
            text = row[1] if len(row) > 1 else ""
            if mid in seen:
                errors.append(f"actba_lang_ja.csv:{n}: duplicate ID {mid}")
            seen.add(mid)
            if mid not in msgs:
                errors.append(f"actba_lang_ja.csv:{n}: ID {mid} is not used in the source")
            elif text and holes(text) != holes(msgs[mid][0]):
                errors.append(f"actba_lang_ja.csv:{n}: ID {mid} placeholders differ from the English text")
    for mid in sorted(set(msgs) - seen):
        warnings.append(f"ID {mid} has no Japanese text: {msgs[mid][0]}")


def main():
    errors, warnings = [], []
    msgs = scan_source(errors)
    scan_csv(msgs, errors, warnings)
    if "--list" in sys.argv:
        for mid in sorted(msgs):
            print(f"{mid}\t{msgs[mid][0]}")
    for w in warnings:
        print("warning: " + w)
    for e in errors:
        print("error: " + e)
    print(f"{len(msgs)} IDs, next free ID: {max(msgs, default=1000) + 1}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
