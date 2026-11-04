# -*- coding: utf-8 -*-
"""追加最后 2 种使计划达到 2400，并创建两个新数据文件的空骨架。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "plan"

for fname, row in [
    ("species-animals-add7.json", ["mammal-rock-squirrel", "岩松鼠", "Sciurotamias davidianus", "mammals", "01-mammals.js"]),
    ("species-animals-add7.json", ["bird-sewerzows-grouse", "斑尾榛鸡", "Tetrastes sewerzowi", "birds", "02-birds.js"]),
]:
    d = json.loads((PLAN / fname).read_text(encoding="utf-8"))
    assert all(r[0] != row[0] and r[2] != row[2] for n in PLAN.glob("species*.json")
               for r in json.loads(n.read_text(encoding="utf-8"))["species"]), row
    d["species"].append(row)
    (PLAN / fname).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

total = 0
for f in sorted(PLAN.glob("species*.json")):
    if f.name.startswith("species-animals") or f.name.startswith("species-plants"):
        total += len(json.loads(f.read_text(encoding="utf-8"))["species"])
print("plan total:", total)

head = "/* 昆虫扩编 3（v3.1）：数据由子任务分批追加到本行之前 */\n"
sentinel = "/* ==== FILE-END: 在此行之前追加新的 registerSpecies 调用 ==== */\n"
for rel in ["data/animals/06e-insects-extra3.js", "data/plants/08c-fungi-extra2.js"]:
    p = ROOT / rel
    if not p.exists():
        p.write_text(head + sentinel, encoding="utf-8")
        print("created", rel)
