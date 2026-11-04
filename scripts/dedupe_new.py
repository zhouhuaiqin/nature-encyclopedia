# -*- coding: utf-8 -*-
"""去重 v3.2 新扩编计划（add10/11/12、plants add7/8），不追加其他内容。"""
import glob
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "plan"
NEW = ["species-animals-add10.json", "species-animals-add11.json", "species-animals-add12.json",
       "species-plants-add7.json", "species-plants-add8.json"]

occupied_id, occupied_latin = {}, {}
data = {}
for f in sorted(glob.glob(str(PLAN / "species*.json"))):
    name = Path(f).name
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    data[name] = d
    if name not in NEW:
        for r in d["species"]:
            occupied_id.setdefault(r[0], name)
            occupied_latin.setdefault(r[2], name)

for name in NEW:
    d = data[name]
    kept, dropped = [], []
    for r in d["species"]:
        if r[0] in occupied_id or r[2] in occupied_latin:
            dropped.append((r[0], r[1]))
            continue
        occupied_id[r[0]] = name
        occupied_latin[r[2]] = name
        kept.append(r)
    d["species"] = kept
    (PLAN / name).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(name, "kept", len(kept), "dropped", len(dropped), dropped[:5])

rows = [r for d in data.values() for r in d["species"]]
tabs = Counter()
for d in data.values():
    tabs[d["tab"]] += len(d["species"])
print("tabs:", dict(tabs), "sum:", sum(tabs.values()))
print("categories:", dict(Counter(r[3] for r in rows)))
print("targets:", dict(Counter(r[4] for r in rows if len(r) > 4)))
