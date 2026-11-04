# -*- coding: utf-8 -*-
"""统计新扩编计划中与其他计划重复的行（按 id 与学名），输出需要替换的数量。"""
import glob
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW = [
    "species-animals-add7.json", "species-animals-add8.json", "species-animals-add9.json",
    "species-plants-add5.json", "species-plants-add6.json",
]
all_rows = {}
for f in sorted(glob.glob(str(ROOT / "plan" / "species*.json"))):
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    for r in d["species"]:
        all_rows.setdefault(r[0], []).append((Path(f).name, r))
latin_owner = {}
for rid, lst in all_rows.items():
    for fn, r in lst:
        latin_owner.setdefault(r[2], set()).add(rid)

for name in NEW:
    d = json.loads((ROOT / "plan" / name).read_text(encoding="utf-8"))
    drop = []
    for r in d["species"]:
        dup_id = any(fn != name for fn, _ in all_rows.get(r[0], []))
        dup_latin = len(latin_owner.get(r[2], set())) > 1
        if dup_id or dup_latin:
            drop.append((r[0], r[1], r[2], r[3], r[4]))
    print(name, "rows", len(d["species"]), "need replace", len(drop))
    for row in drop:
        print("   -", row)
