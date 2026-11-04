# -*- coding: utf-8 -*-
"""为物种数超过 96 的类群生成后续联系表（第 2、3 批），用于继续目检。"""
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "plan" / "audit"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    by_cat = defaultdict(list)
    for e in fi.load_plan():
        by_cat[e["category"]].append(e)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 11)
    except Exception:
        font = ImageFont.load_default()
    totals = 0
    for cat, entries in by_cat.items():
        if len(entries) <= 96:
            continue
        chunk = 96
        part = 2
        for start in range(96, len(entries), chunk):
            part_entries = entries[start:start + chunk]
            CW, CH = 200, 152
            cols = 8
            rows = (len(part_entries) + cols - 1) // cols
            sheet = Image.new("RGB", (CW * cols, CH * rows + 24), (245, 241, 232))
            d = ImageDraw.Draw(sheet)
            d.text((6, 4), f"{cat} part {part}  ({len(part_entries)} shown)",
                   fill=(22, 56, 42), font=font)
            for i, e in enumerate(part_entries):
                p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
                if not p.exists():
                    continue
                x = (i % cols) * CW
                y = (i // cols) * CH + 24
                try:
                    im = Image.open(p).convert("RGB")
                    im.thumbnail((CW - 8, CH - 28))
                    sheet.paste(im, (x + 4, y + 4))
                except Exception:
                    continue
                d.text((x + 4, y + CH - 22), e["name"][:10] + " " + e["id"][:20],
                       fill=(30, 40, 34), font=font)
            out = OUT / f"{cat}-{part}.jpg"
            sheet.save(out, quality=85)
            totals += 1
            print("sheet:", out.name, len(part_entries))
            part += 1
    print("total extra sheets:", totals)


if __name__ == "__main__":
    main()
