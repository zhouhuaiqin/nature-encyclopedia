# -*- coding: utf-8 -*-
"""图片-物种对应审计：重复图片、占位图、每类群联系表（用于人工核对）。"""
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "plan" / "audit"
OUT.mkdir(parents=True, exist_ok=True)


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    plan = fi.load_plan()
    ledger = fi.load_json(fi.LEDGER, {})
    hashes = defaultdict(list)
    placeholders = []
    missing = []
    by_cat = defaultdict(list)
    for e in plan:
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        rec = ledger.get(e["id"]) or {}
        if "原创占位图" in (rec.get("note") or ""):
            placeholders.append({"id": e["id"], "name": e["name"]})
        if not p.exists():
            missing.append({"id": e["id"], "name": e["name"]})
            continue
        hashes[md5(p)].append({"id": e["id"], "name": e["name"], "category": e["category"]})
        by_cat[e["category"]].append(e)

    dups = [v for v in hashes.values() if len(v) > 1]
    print("物种:", len(plan), "图片:", sum(len(v) for v in hashes.values()),
          "占位图:", len(placeholders), "缺失:", len(missing), "重复图片组:", len(dups))
    for group in dups[:30]:
        print("  DUP:", " | ".join(x["id"] + " " + x["name"] for x in group))

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 11)
    except Exception:
        font = ImageFont.load_default()

    sheets = []
    for cat, entries in by_cat.items():
        entries = entries[:96]
        CW, CH = 200, 152
        cols = 8
        rows = (len(entries) + cols - 1) // cols
        sheet = Image.new("RGB", (CW * cols, CH * rows + 24), (245, 241, 232))
        d = ImageDraw.Draw(sheet)
        d.text((6, 4), f"{cat}  ({len(entries)} shown)", fill=(22, 56, 42), font=font)
        for i, e in enumerate(entries):
            p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
            x = (i % cols) * CW
            y = (i // cols) * CH + 24
            try:
                im = Image.open(p).convert("RGB")
                im.thumbnail((CW - 8, CH - 28))
                sheet.paste(im, (x + 4, y + 4))
            except Exception:
                continue
            d.text((x + 4, y + CH - 22), e["name"][:10] + " " + e["id"][:20], fill=(30, 40, 34), font=font)
        out = OUT / f"{cat}.jpg"
        sheet.save(out, quality=85)
        sheets.append(str(out))
        print("sheet:", out.name, len(entries))

    report = {
        "totalSpecies": len(plan),
        "images": sum(len(v) for v in hashes.values()),
        "placeholders": placeholders,
        "missing": missing,
        "duplicateGroups": dups,
        "sheets": sheets,
        "note": "逐张人工核对联系表，记录与物种不符的 id；重复图片组需重点核对。",
    }
    (ROOT / "plan" / "image-species-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("report saved")


if __name__ == "__main__":
    main()
