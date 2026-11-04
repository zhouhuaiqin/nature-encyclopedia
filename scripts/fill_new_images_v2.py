# -*- coding: utf-8 -*-
"""v2：新增物种补图 —— 仅使用同属已有照片（注明同属近缘种），否则使用本站自绘 CC0 占位图；
不再使用同科/同类群照片，避免展示错误物种。"""
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
    new_ids = []
    for name in NEW_PLAN:
        d = json.loads((ROOT / "plan" / name).read_text(encoding="utf-8"))
        for r in d["species"]:
            new_ids.append(r[0])

    donors_genus = defaultdict(list)
    for e in plan.values():
        if e["id"] in new_ids:
            continue
        rec = ledger.get(e["id"]) or {}
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        if not p.exists():
            continue
        if "原创占位图" in (rec.get("note") or ""):
            continue
        if (rec.get("license") or "").lower() in BAD:
            continue
        donors_genus[genus_of(e)].append(e["id"])

    stats = {"genus": 0, "placeholder": 0}
    for sid in new_ids:
        e = plan[sid]
        out = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
        donors = [d for d in donors_genus.get(genus_of(e), []) if d != sid]
        if donors:
            donor = donors[0]
            dean = plan[donor]
            src = fi.IMG_DIR / dean["tab"] / (donor + ".jpg")
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out)
            rec = dict(ledger[donor])
            rec["name"], rec["latin"] = e["name"], e["latin"]
            rec["note"] = "同属近缘种代表照片"
            ledger[sid] = rec
            stats["genus"] += 1
        else:
            mp.make_placeholder(e, out)
            ledger[sid] = {
                "author": "自然图鉴（本站自绘）", "license": "cc0", "source": "本站原创占位图",
                "name": e["name"], "latin": e["latin"], "note": "原创占位图（CC0），非真实照片",
            }
            stats["placeholder"] += 1
    fi.write_credits(ledger)
    print("新增物种补图 v2:", stats, "credits:", len(ledger))


if __name__ == "__main__":
    main()
