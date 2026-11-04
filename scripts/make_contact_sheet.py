#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成物种图片检查用拼图（只读 QA 工具，不修改数据）"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "plan" / "shots"
OUT.mkdir(parents=True, exist_ok=True)

plan = json.loads((ROOT / "plan" / "species-animals.json").read_text(encoding="utf-8"))
plan2 = json.loads((ROOT / "plan" / "species-plants.json").read_text(encoding="utf-8"))
rows = [("animals", r) for r in plan["species"]] + [("plants", r) for r in plan2["species"]]

try:
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
    font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)
except Exception:
    font = ImageFont.load_default()
    font_small = font

TW, TH = 210, 158
COLS = 8
PER_SHEET = 64
PAD = 8

sheets = []
batch = []
for tab, row in rows:
    sid, name, latin, cat = row
    path = ROOT / "assets" / "images" / tab / f"{sid}.jpg"
    batch.append((sid, name, path))
    if len(batch) == PER_SHEET:
        sheets.append(batch)
        batch = []
if batch:
    sheets.append(batch)

for si, batch in enumerate(sheets):
    n_rows = (len(batch) + COLS - 1) // COLS
    W = COLS * (TW + PAD) + PAD
    H = n_rows * (TH + 40 + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (247, 245, 239))
    draw = ImageDraw.Draw(sheet)
    for i, (sid, name, path) in enumerate(batch):
        cx = PAD + (i % COLS) * (TW + PAD)
        cy = PAD + (i // COLS) * (TH + 40 + PAD)
        if path.exists():
            try:
                im = Image.open(path).convert("RGB")
                im.thumbnail((TW, TH), Image.LANCZOS)
                sheet.paste(im, (cx + (TW - im.width) // 2, cy + (TH - im.height) // 2))
            except Exception as exc:
                draw.text((cx + 4, cy + 60), f"坏图 {exc}", font=font_small, fill=(180, 40, 40))
        else:
            draw.rectangle([cx, cy, cx + TW, cy + TH], outline=(210, 80, 80), width=2)
            draw.text((cx + 8, cy + 60), "缺图", font=font_small, fill=(180, 40, 40))
        draw.text((cx + 2, cy + TH + 4), name, font=font, fill=(31, 42, 36))
        draw.text((cx + 2, cy + TH + 22), sid, font=font_small, fill=(120, 128, 120))
    out = OUT / f"contact-{si + 1}.jpg"
    sheet.save(out, "JPEG", quality=82)
    print(out, sheet.size)
