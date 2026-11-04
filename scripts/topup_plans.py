# -*- coding: utf-8 -*-
"""补齐到 2400：检查候选 id/学名是否已被占用，只追加未占用的。"""
import glob
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "plan"

ids, lats = set(), set()
data = {}
for f in sorted(glob.glob(str(PLAN / "species*.json"))):
    name = Path(f).name
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    data[name] = d
    for r in d["species"]:
        ids.add(r[0])
        lats.add(r[2])

TARGET = 2400
total = sum(len(d["species"]) for d in data.values())
print("current total:", total)
need = TARGET - total
print("need:", need)

# 候选池：优先常见、与本期主题一致
candidates = [
    ("species-animals-add7.json", "bird-hazel-grouse", "花尾榛鸡", "Tetrastes bonasia", "birds", "02-birds.js"),
    ("species-animals-add7.json", "bird-great-bustard", "大鸨", "Otis tarda", "birds", "02-birds.js"),
    ("species-animals-add7.json", "bird-willow-ptarmigan", "柳雷鸟", "Lagopus lagopus", "birds", "02-birds.js"),
    ("species-animals-add8.json", "fish-yellowfin-tuna", "黄鳍金枪鱼", "Thunnus albacares", "fish", "05-fish.js"),
    ("species-animals-add8.json", "fish-atlantic-bluefin-tuna", "蓝鳍金枪鱼", "Thunnus thynnus", "fish", "05-fish.js"),
    ("species-animals-add8.json", "fish-atlantic-cod", "鳕鱼", "Gadus morhua", "fish", "05-fish.js"),
    ("species-plants-add5.json", "tree-robust-grevillea", "银桦", "Grevillea robusta", "trees", "01-trees.js"),
    ("species-plants-add5.json", "shrub-hamabo-hibiscus", "海滨木槿", "Hibiscus hamabo", "shrubs", "02-shrubs.js"),
    ("species-plants-add5.json", "tree-qinggang", "青冈", "Cyclobalanopsis glauca", "trees", "01-trees.js"),
    ("species-plants-add6.json", "fern-king-fern", "王紫萁", "Osmunda regalis", "ferns-gymnosperms", "06-ferns-gymnosperms.js"),
]

added = 0
for fname, rid, cn, latin, cat, target in candidates:
    if added >= need:
        break
    if rid in ids or latin in lats:
        print("skip occupied:", rid, cn)
        continue
    data[fname]["species"].append([rid, cn, latin, cat, target])
    ids.add(rid)
    lats.add(latin)
    added += 1
    (PLAN / fname).write_text(json.dumps(data[fname], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("added:", rid, cn)

total = sum(len(d["species"]) for d in data.values())
print("final total:", total)
tabs = Counter()
for name, d in data.items():
    tabs[d["tab"]] += len(d["species"])
print("tabs:", dict(tabs))
print("categories:", dict(Counter(r[3] for name, d in data.items() for r in d["species"])))
dup_ids = [k for k, v in Counter(r[0] for d in data.values() for r in d["species"]).items() if v > 1]
dup_lats = [k for k, v in Counter(r[2] for d in data.values() for r in d["species"]).items() if v > 1]
print("dup ids:", dup_ids)
print("dup latins:", dup_lats)
