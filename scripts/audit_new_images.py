# -*- coding: utf-8 -*-
"""抽检 v3 新增物种图片：随机取 96 个新 id，生成 8x12 联系表。"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PLAN_GLOB = sorted((ROOT / "plan").glob("species-*add[456]*.json")) + sorted((ROOT / "plan").glob("species-plants-add[34].json"))
new_ids = []
for p in PLAN_GLOB:
    data = json.loads(p.read_text(encoding="utf-8"))
    for row in data["species"]:
        new_ids.append(row[0])
new_ids = list(dict.fromkeys(new_ids))
random.seed(42)
sample = random.sample(new_ids, min(96, len(new_ids)))

CELL_W, CELL_H = 180, 130
COLS, ROWS = 8, 12
sheet = Image.new("RGB", (CELL_W * COLS, CELL_H * ROWS + 30), (245, 241, 232))
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 11)
except Exception:
    font = ImageFont.load_default()

missing = []
for idx, sid in enumerate(sample):
    tab = "plants" if any(r[0] == sid and r[3] in {
        "trees", "shrubs", "flowers", "succulents", "aquatic", "ferns-gymnosperms", "crops", "fungi"
    } for p in PLAN_GLOB for r in json.loads(p.read_text(encoding="utf-8"))["species"]) else "animals"
    img_path = ROOT / "assets" / "images" / tab / (sid + ".jpg")
    if not img_path.exists():
        missing.append(sid)
        continue
    x = (idx % COLS) * CELL_W
    y = (idx // COLS) * CELL_H + 30
    try:
        im = Image.open(img_path).convert("RGB")
        im.thumbnail((CELL_W - 8, CELL_H - 26))
        sheet.paste(im, (x + 4, y + 4))
    except Exception:
        missing.append(sid)
        continue
    draw.text((x + 5, y + CELL_H - 20), sid[:26], fill=(30, 40, 34), font=font)

draw.text((6, 6), f"v3 new species image audit  sample={len(sample)}  missing={len(missing)}", fill=(22, 56, 42), font=font)
out = ROOT / "plan" / "shots" / "audit-v3-new.png"
sheet.save(out, quality=88)
print("saved", out, "missing", missing)
