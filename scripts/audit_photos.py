# -*- coding: utf-8 -*-
"""审计现有图片质量：低分辨率、极端长宽比、文件过小，生成候选清单与联系表。"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "plan" / "shots"


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    bad = []
    for sid, e in plan.items():
        p = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
        if not p.exists():
            bad.append((sid, e, "missing", 0, 0, 0))
            continue
        rec = ledger.get(sid) or {}
        note = rec.get("note") or ""
        try:
            im = Image.open(p)
            w, h = im.size
        except Exception:
            bad.append((sid, e, "corrupt", 0, 0, p.stat().st_size))
            continue
        size = p.stat().st_size
        ratio = max(w, h) / max(1, min(w, h))
        reason = []
        if "原创占位图" in note:
            reason.append("placeholder")
        if min(w, h) < 620:
            reason.append(f"small({w}x{h})")
        if ratio > 2.1:
            reason.append(f"ratio({ratio:.2f})")
        if size < 26000:
            reason.append(f"bytes({size // 1024}KB)")
        if reason:
            bad.append((sid, e, ",".join(reason), w, h, size))

    print("候选:", len(bad))
    by_reason = {}
    for b in bad:
        for r in b[2].split(","):
            key = r.split("(")[0]
            by_reason[key] = by_reason.get(key, 0) + 1
    print(by_reason)
    (ROOT / "plan" / "photo-audit.json").write_text(json.dumps(
        [{"id": b[0], "name": b[1]["name"], "reason": b[2]} for b in bad],
        ensure_ascii=False, indent=2), encoding="utf-8")

    # 联系表（最多 96 张）
    sample = bad[:96]
    CELL_W, CELL_H = 200, 150
    COLS, ROWS = 8, 12
    sheet = Image.new("RGB", (CELL_W * COLS, CELL_H * ROWS + 26), (245, 241, 232))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 11)
    except Exception:
        font = ImageFont.load_default()
    draw.text((6, 5), f"photo audit candidates: {len(bad)}", fill=(22, 56, 42), font=font)
    for i, (sid, e, reason, w, h, size) in enumerate(sample):
        p = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
        if not p.exists():
            continue
        x = (i % COLS) * CELL_W
        y = (i // COLS) * CELL_H + 26
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail((CELL_W - 8, CELL_H - 26))
            sheet.paste(im, (x + 4, y + 4))
        except Exception:
            continue
        draw.text((x + 4, y + CELL_H - 20), e["name"][:10] + " " + sid[:18], fill=(30, 40, 34), font=font)
    SHOTS.mkdir(parents=True, exist_ok=True)
    sheet.save(SHOTS / "audit-lowquality.png", quality=88)
    print("saved", SHOTS / "audit-lowquality.png")


if __name__ == "__main__":
    main()
