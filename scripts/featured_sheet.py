# -*- coding: utf-8 -*-
"""生成策展精选物种图片联系表，用于挑选首页封面拼贴。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ids = [
    "mammal-giant-panda", "bird-green-peafowl", "insect-blue-morpho",
    "aquatic-giant-water-lily", "mammal-snow-leopard", "fungus-fly-agaric",
    "bird-crested-ibis", "tree-ginkgo", "fish-whale-shark", "flower-common-sunflower",
]
tabs = {"tree-ginkgo": "plants", "flower-common-sunflower": "plants", "fungus-fly-agaric": "plants", "aquatic-giant-water-lily": "plants"}
cell = 300
sheet = Image.new("RGB", (cell * 5, cell * 2 + 28), (245, 241, 232))
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13)
for i, sid in enumerate(ids):
    tab = tabs.get(sid, "animals")
    p = ROOT / "assets" / "images" / tab / (sid + ".jpg")
    im = Image.open(p).convert("RGB")
    im.thumbnail((cell - 8, cell - 30))
    x = (i % 5) * cell
    y = (i // 5) * cell + 28
    sheet.paste(im, (x + 4, y + 4))
    draw.text((x + 6, y + cell - 22), sid, fill=(20, 30, 24), font=font)
sheet.save(ROOT / "plan" / "shots" / "featured-sheet.jpg", quality=88)
print("ok")
