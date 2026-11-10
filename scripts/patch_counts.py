# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

p = ROOT / "data/meta.js"
s = p.read_text(encoding="utf-8")
old_intro = '"从雪线之上的雪豹到雨林深处的蓝闪蝶，从两亿年前的银杏到餐桌上的稻米——2658 份生命档案，按界、门、纲、目、科、属层层展开。这是一册可以慢慢翻的自然志，也是一座纸上的自然博物馆。"'
new_intro = '"从雪线之上的雪豹到雨林深处的蓝闪蝶，从两亿年前的银杏到餐桌上的稻米——2664 份生命档案，动物、植物与菌物三界并列，按界、门、纲、目、科、属层层展开。这是一册可以慢慢翻的自然志，也是一座纸上的自然博物馆。"'
s = s.replace(old_intro, new_intro)
s = s.replace('version: "3.5"', 'version: "3.9"')
s = s.replace("regions: 2658", "regions: 2664")
p.write_text(s, encoding="utf-8")

p = ROOT / "index.html"
s = p.read_text(encoding="utf-8")
s = s.replace("2658", "2664")
s = s.replace("动物 1534 种、植物与菌物 1124 种", "动物 1535 种、植物 913 种、菌物 216 种")
p.write_text(s, encoding="utf-8")
print("counts patched")
