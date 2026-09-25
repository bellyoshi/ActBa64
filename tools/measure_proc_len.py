#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Report Function/Sub procedures longer than a line threshold in .abp sources."""
import re
import sys

START_RE = re.compile(r'^\s*(?:Public\s+|Private\s+)?(Function|Sub)\s+([A-Za-z_][A-Za-z0-9_]*)', re.I)
END_RE = re.compile(r'^\s*End\s+(Function|Sub)\b', re.I)
DECL_RE = re.compile(r'^\s*Declare\b', re.I)


def scan(path, threshold):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.read().split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if DECL_RE.match(line):
            i += 1
            continue
        m = START_RE.match(line)
        if m:
            start = i + 1
            j = i + 1
            while j < len(lines) and not END_RE.match(lines[j]):
                j += 1
            end = j + 1
            n = end - start + 1
            if n > threshold:
                out.append((m.group(2), start, end, n))
            i = j + 1
            continue
        i += 1
    return out


def main():
    threshold = 50
    files = []
    for a in sys.argv[1:]:
        if a.startswith('--threshold='):
            threshold = int(a.split('=', 1)[1])
        else:
            files.append(a)
    total = 0
    for path in files:
        bad = scan(path, threshold)
        total += len(bad)
        print('%s: %d over %d' % (path, len(bad), threshold))
        for name, s, e, n in bad:
            print('    %-40s %5d-%-5d %4d lines' % (name, s, e, n))
    print('TOTAL over %d: %d' % (threshold, total))
    return total


if __name__ == '__main__':
    sys.exit(0 if main() == 0 else 1)
