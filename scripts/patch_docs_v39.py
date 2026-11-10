# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def edit(path, pairs):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    for a, b in pairs:
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")


edit("README.md", [
    ("2400 个物种", "2663 个物种"),
    ("2658 个物种", "2663 个物种"),
    ("2658", "2663"),
    ("1534", "1535"),
    ("1124", "913"),
    ("真菌 213", "真菌 215"),
    ("v3.5", "v3.9"),
])
edit("SPEC.md", [
    ("2658", "2663"),
    ("1534", "1535"),
    ("真菌（菌物界） | plants | 08-fungi.js + 08b + 08c | 213", "真菌（菌物界） | fungi | 08-fungi.js + 08b + 08c | 215"),
    ("| fungi | 真菌（菌物界） | plants |", "| fungi | 真菌（菌物界） | fungi |"),
    ("| 213 |", "| 215 |"),
])
edit("DEPLOY.md", [
    ("2658", "2663"),
])
print("docs patched")
