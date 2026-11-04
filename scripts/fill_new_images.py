# -*- coding: utf-8 -*-
"""为新增物种补图（离线、快速）：
1) 同属已有照片 → 复制并继承署名/许可（注明同属近缘种）；
2) 同科已有照片 → 复制（注明同科代表照片）；
3) 都没有 → 本站自绘 CC0 占位图。
"""
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi
import make_placeholders as mp

ROOT = Path(__file__).resolve().parent.parent
BAD = {"all rights reserved", "gfdl", "cc-by-nd", "cc-by-nc-nd"}
NEW_PLAN = ["species-animals-add7.json", "species-animals-add8.json", "species-animals-add9.json",
            "species-plants-add5.json", "species-plants-add6.json"]


def genus_of(e):
    return (e["latin"].split() or [""])[0]


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    # 新物种 id 与所属科
    new_ids = []
    cat_of = {}
    for name in NEW_PLAN:
        d = json.loads((ROOT / "plan" / name).read_text(encoding="utf-8"))
        for r in d["species"]:
            new_ids.append(r[0])
            cat_of[r[0]] = r[3]
    # 类别 → 代表科（用 plan 条目的 taxonomy 不可得，这里以同 category 的照片做兜底）
    donors_genus = defaultdict(list)
    donors_cat = defaultdict(list)
    for e in plan.values():
        rec = ledger.get(e["id"]) or {}
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        if not p.exists():
            continue
        if "原创占位图" in (rec.get("note") or ""):
            continue
        if (rec.get("license") or "").lower() in BAD:
            continue
        donors_genus[genus_of(e)].append(e["id"])
        donors_cat[e["category"]].append(e["id"])

    stats = {"existing": 0, "genus": 0, "category": 0, "placeholder": 0}
    for sid in new_ids:
        e = plan[sid]
        out = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
        if out.exists():
            stats["existing"] += 1
            continue
        donors = [d for d in donors_genus.get(genus_of(e), []) if d != sid]
        note = "同属近缘种代表照片"
        if not donors:
            donors = [d for d in donors_cat.get(e["category"], []) if d != sid]
            note = "同类群代表照片"
        if donors:
            donor = donors[0]
            dean = plan[donor]
            src = fi.IMG_DIR / dean["tab"] / (donor + ".jpg")
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out)
            rec = dict(ledger[donor])
            rec["name"], rec["latin"] = e["name"], e["latin"]
            rec["note"] = note
            ledger[sid] = rec
            stats["genus" if note.startswith("同属") else "category"] += 1
        else:
            mp.make_placeholder(e, out)
            ledger[sid] = {
                "author": "自然图鉴（本站自绘）", "license": "cc0", "source": "本站原创占位图",
                "name": e["name"], "latin": e["latin"], "note": "原创占位图（CC0），非真实照片",
            }
            stats["placeholder"] += 1
    fi.write_credits(ledger)
    print("新增物种补图:", stats, "credits:", len(ledger))


if __name__ == "__main__":
    main()
