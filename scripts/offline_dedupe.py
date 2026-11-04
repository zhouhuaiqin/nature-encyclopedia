# -*- coding: utf-8 -*-
"""离线去重：一个重复图片组只保留第一个物种的图，其余改为明确标注的占位图。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi
import make_placeholders as mp

ROOT = Path(__file__).resolve().parent.parent


def main():
    audit = json.loads((ROOT / "plan" / "image-species-audit.json").read_text(encoding="utf-8"))
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    changed = 0
    for group in audit["duplicateGroups"]:
        for item in group[1:]:
            e = plan[item["id"]]
            p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
            mp.make_placeholder(e, p)
            ledger[e["id"]] = {
                "author": "自然图鉴（本站自绘）", "license": "cc0", "source": "本站原创占位图",
                "name": e["name"], "latin": e["latin"],
                "note": "原创占位图（CC0），非真实照片（重复图片已移除）",
            }
            changed += 1
    fi.write_credits(ledger)
    print("duplicate -> placeholder:", changed, "credits:", len(ledger))


if __name__ == "__main__":
    main()
