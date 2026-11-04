# -*- coding: utf-8 -*-
"""查看皮肤/居中评分最高的图片，校准“人手/不居中”阈值。"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
rows = json.loads((ROOT / "plan" / "photo-quality.json").read_text(encoding="utf-8"))
rows = [r for r in rows if not r.get("placeholder")]
rows.sort(key=lambda r: max(r.get("bottomSkin", 0), r.get("edgeSkin", 0)), reverse=True)
rows = rows[:96]
plan = {e["id"]: e for e in fi.load_plan()}
CW, CH = 200, 152
sheet = Image.new("RGB", (CW * 8, CH * 12 + 24), (245, 241, 232))
d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 11)
except Exception:
    font = ImageFont.load_default()
d.text((6, 4), "top skin scores (check hands)", fill=(120, 20, 20), font=font)
for i, r in enumerate(rows):
    e = plan[r["id"]]
    p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
    x = (i % 8) * CW
    y = (i // 8) * CH + 24
    try:
        im = Image.open(p).convert("RGB")
        im.thumbnail((CW - 8, CH - 28))
        sheet.paste(im, (x + 4, y + 4))
    except Exception:
        continue
    d.text((x + 4, y + CH - 22), f'{e["name"][:6]} {r.get("bottomSkin",0):.2f}/{r.get("edgeSkin",0):.2f}',
           fill=(30, 40, 34), font=font)
out = ROOT / "plan" / "shots" / "skin-audit.jpg"
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, quality=85)
print("saved", out)
