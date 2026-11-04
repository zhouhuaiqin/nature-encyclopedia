# -*- coding: utf-8 -*-
"""去重 v3.1 扩编计划（按 id 与学名），并补 7 种使总数达到 2400。"""
import glob
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "plan"
NEW = [
    "species-animals-add7.json", "species-animals-add8.json", "species-animals-add9.json",
    "species-plants-add5.json", "species-plants-add6.json",
]

# 1) 载入所有计划，先占位旧计划
occupied_id = {}
occupied_latin = {}
data = {}
for f in sorted(glob.glob(str(PLAN / "species*.json"))):
    name = Path(f).name
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    data[name] = d
    if name not in NEW:
        for r in d["species"]:
            occupied_id.setdefault(r[0], name)
            occupied_latin.setdefault(r[2], name)

# 2) 新计划逐行去重（保持组内顺序）
for name in NEW:
    d = data[name]
    kept = []
    dropped = []
    for r in d["species"]:
        if r[0] in occupied_id or r[2] in occupied_latin:
            dropped.append(r)
            continue
        occupied_id[r[0]] = name
        occupied_latin[r[2]] = name
        kept.append(r)
    d["species"] = kept
    (PLAN / name).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(name, "kept", len(kept), "dropped", len(dropped))

# 3) 补 7 种，凑 2400
ADDITIONS = [
    ("species-animals-add7.json", ["mammal-north-american-porcupine", "北美豪猪", "Erethizon dorsatum", "mammals", "01-mammals.js"]),
    ("species-animals-add7.json", ["mammal-black-tailed-prairie-dog", "黑尾土拨鼠", "Cynomys ludovicianus", "mammals", "01-mammals.js"]),
    ("species-animals-add7.json", ["bird-black-grouse", "黑琴鸡", "Lyrurus tetrix", "birds", "02-birds.js"]),
    ("species-animals-add7.json", ["bird-great-bustard", "大鸨", "Otis tarda", "birds", "02-birds.js"]),
    ("species-animals-add8.json", ["fish-yellowfin-tuna", "黄鳍金枪鱼", "Thunnus albacares", "fish", "05-fish.js"]),
    ("species-plants-add5.json", ["tree-robust-grevillea", "银桦", "Grevillea robusta", "trees", "01-trees.js"]),
    ("species-plants-add5.json", ["shrub-hamabo-hibiscus", "海滨木槿", "Hibiscus hamabo", "shrubs", "02-shrubs.js"]),
]
for name, row in ADDITIONS:
    d = data[name]
    assert row[0] not in occupied_id and row[2] not in occupied_latin, row
    d["species"].append(row)
    occupied_id[row[0]] = name
    occupied_latin[row[2]] = name
    (PLAN / name).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# 4) 复核
rows = []
tabs = Counter()
for name, d in data.items():
    tabs[d["tab"]] += len(d["species"])
    rows.extend(d["species"])
print("tabs:", dict(tabs), "sum:", sum(tabs.values()))
print("categories:", dict(Counter(r[3] for r in rows)))
ids = Counter(r[0] for r in rows)
lats = Counter(r[2] for r in rows)
print("dup ids:", [k for k, v in ids.items() if v > 1])
print("dup latins:", [k for k, v in lats.items() if v > 1])
