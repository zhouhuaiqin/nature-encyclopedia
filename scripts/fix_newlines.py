# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
files = [
    "data/animals/11-new-species.js",
    "data/animals/12-new-birds.js",
    "data/plants/09-new-plants.js",
    "data/plants/10-new-fungi.js",
]
for f in files:
    p = ROOT / f
    s = p.read_text(encoding="utf-8")
    # 文件中是 \\n（两个反斜杠+n），改成 JS 的 \n（一个反斜杠+n）
    s = s.replace("\\\\n", "\\n")
    p.write_text(s, encoding="utf-8")
print("newlines fixed")
