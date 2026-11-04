#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扩编图片抽检拼图：从 plan/species*.json 读取全部物种，抽取新增物种生成联系表。"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "plan" / "shots"
OUT.mkdir(parents=True, exist_ok=True)


def load_entries():
    entries = []
    seen = set()
    for path in sorted((ROOT / "plan").glob("species*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        tab = data.get("tab")
        for row in data.get("species") or []:
            if not row or len(row) < 4 or row[0] in seen:
                continue
            seen.add(row[0])
            entries.append({
                "id": row[0],
                "name": row[1],
                "latin": row[2],
                "category": row[3],
                "tab": tab,
                "is_new": len(row) >= 5,
            })
    return entries


def main(argv):
    every = int(argv[1]) if len(argv) > 1 else 0
    entries = [e for e in load_entries() if e["is_new"] and e["tab"] == "animals"]
    plants = [e for e in load_entries() if e["is_new"] and e["tab"] == "plants"]
    if every > 0:
        entries = entries[::every]
        plants = plants[::every]
    rows = entries + plants
    print(f"抽检物种：{len(rows)} 个（动物 {len(entries)}，植物/菌物 {len(plants)}）")

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
        font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 11)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()
        font_small = font

    TW, TH = 200, 150
    COLS = 8
    PER_SHEET = 64
    PAD = 8
    for si in range(0, len(rows), PER_SHEET):
        batch = rows[si:si + PER_SHEET]
        n_rows = (len(batch) + COLS - 1) // COLS
        W = COLS * (TW + PAD) + PAD
        H = n_rows * (TH + 42 + PAD) + PAD
        sheet = Image.new("RGB", (W, H), (247, 245, 239))
        draw = ImageDraw.Draw(sheet)
        for i, entry in enumerate(batch):
            sid = entry["id"]
            path = ROOT / "assets" / "images" / entry["tab"] / f"{sid}.jpg"
            cx = PAD + (i % COLS) * (TW + PAD)
            cy = PAD + (i // COLS) * (TH + 42 + PAD)
            if path.exists():
                try:
                    im = Image.open(path).convert("RGB")
                    im.thumbnail((TW, TH), Image.LANCZOS)
                    sheet.paste(im, (cx + (TW - im.width) // 2, cy + (TH - im.height) // 2))
                except Exception as exc:  # noqa: BLE001
                    draw.text((cx + 4, cy + 50), f"坏图 {exc}", font=font_small, fill=(180, 40, 40))
            else:
                draw.rectangle([cx, cy, cx + TW, cy + TH], outline=(210, 80, 80), width=2)
                draw.text((cx + 8, cy + 55), "缺图", font=font_small, fill=(180, 40, 40))
            draw.text((cx + 2, cy + TH + 4), entry["name"], font=font, fill=(31, 42, 36))
            draw.text((cx + 2, cy + TH + 23), sid, font=font_small, fill=(120, 128, 120))
        out = OUT / f"contact-v2-{si // PER_SHEET + 1}.jpg"
        sheet.save(out, "JPEG", quality=80)
        print(out, sheet.size)


if __name__ == "__main__":
    main(sys.argv)
