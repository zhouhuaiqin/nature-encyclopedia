# -*- coding: utf-8 -*-
"""为「保留所有权利 / GFDL / ND」等不可用许可的图片生成站点自绘占位图（CC0 原创），
并登记版权，保证全站图片许可合法、校验可通过。"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
BAD = {"all rights reserved", "gfdl", "cc-by-nd", "cc-by-nc-nd"}
W, H = 900, 600
BG = (238, 232, 218)
INK = (46, 58, 50)
GOLD = (176, 140, 78)

FONT = "C:/Windows/Fonts/msyh.ttc"
try:
    f_title = ImageFont.truetype(FONT, 64)
    f_latin = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 30)
    f_note = ImageFont.truetype(FONT, 24)
except Exception:
    f_title = f_latin = f_note = ImageFont.load_default()


def make_placeholder(entry, out_path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for i in range(0, W, 24):
        d.line([(i, 0), (i + 240, H)], fill=(234, 228, 213), width=1)
    d.rectangle([26, 26, W - 26, H - 26], outline=(200, 188, 164), width=2)
    d.ellipse([W / 2 - 90, 120, W / 2 + 90, 300], outline=GOLD, width=3)
    d.arc([W / 2 - 90, 120, W / 2 + 90, 300], 200, 340, fill=GOLD, width=6)
    name = entry["name"]
    tw = d.textlength(name, font=f_title)
    d.text(((W - tw) / 2, 330), name, font=f_title, fill=INK)
    latin = entry["latin"]
    tw = d.textlength(latin, font=f_latin)
    d.text(((W - tw) / 2, 420), latin, font=f_latin, fill=(110, 110, 96))
    note = "示意占位图 · 本站自绘 (CC0)"
    tw = d.textlength(note, font=f_note)
    d.text(((W - tw) / 2, 492), note, font=f_note, fill=GOLD)
    img.save(out_path, "JPEG", quality=86, optimize=True)


def main():
    plan = fi.load_plan()
    ledger = fi.load_json(fi.LEDGER, {})
    made = 0
    for entry in plan:
        rec = ledger.get(entry["id"]) or {}
        lic = (rec.get("license") or "").lower()
        path = fi.IMG_DIR / entry["tab"] / (entry["id"] + ".jpg")
        if path.exists() and lic not in BAD and lic:
            continue
        if lic in BAD or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            make_placeholder(entry, path)
            ledger[entry["id"]] = {
                "author": "自然图鉴（本站自绘）",
                "license": "cc0",
                "source": "本站原创占位图",
                "name": entry["name"],
                "latin": entry["latin"],
                "note": "原创占位图（CC0），非真实照片",
            }
            made += 1
    fi.write_credits(ledger)
    print("生成占位图:", made, "当前版权条目:", len(ledger))


if __name__ == "__main__":
    main()
