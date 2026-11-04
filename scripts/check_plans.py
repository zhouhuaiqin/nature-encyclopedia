# -*- coding: utf-8 -*-
"""校验 v3.1 扩编计划：数量、id/学名重复、可疑学名。"""
import glob
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = []
seen_id = {}
for f in sorted(glob.glob(str(ROOT / "plan" / "species*.json"))):
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    for r in d["species"]:
        if r[0] in seen_id:
            print("DUP-ID", Path(f).name, r[0], "already in", seen_id[r[0]])
        seen_id[r[0]] = Path(f).name
        rows.append(r)

tabs = Counter()
for f in sorted(glob.glob(str(ROOT / "plan" / "species*.json"))):
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    tabs[d["tab"]] += len(d["species"])
print("tabs:", dict(tabs), "sum:", sum(tabs.values()))

cat = Counter(r[3] for r in rows)
print("categories:", dict(cat))

lat = {}
for r in rows:
    if r[2] in lat and lat[r[2]] != r[0]:
        print("DUP-LATIN", r[0], lat[r[2]], r[2])
    lat[r[2]] = r[0]

for r in rows:
    if any(c in r[2] for c in "?") or r[2].endswith("2"):
        print("BAD-LATIN", r)

newfiles = [
    "plan/species-animals-add7.json", "plan/species-animals-add8.json",
    "plan/species-animals-add9.json", "plan/species-plants-add5.json",
    "plan/species-plants-add6.json",
]
for rel in newfiles:
    d = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    print(rel, "count:", len(d["species"]), "targets:", dict(Counter(r[4] for r in d["species"])))
