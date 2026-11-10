# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
app = ROOT / "js" / "app.js"
s = app.read_text(encoding="utf-8")
old1 = 'escapeHtml(coverEntry ? thumbOf(coverEntry) : "")'
new1 = 'escapeHtml(coverEntry ? imageOf(coverEntry) : "")'
old2 = '<span class="feat-card__img"><img src="\' + escapeHtml(thumbOf(e))'
new2 = '<span class="feat-card__img"><img src="\' + escapeHtml(imageOf(e))'
old3 = 'var img = cover ? thumbOf(cover) : "";'
new3 = 'var img = cover ? imageOf(cover) : "";'
for old, new in [(old1, new1), (old2, new2), (old3, new3)]:
    if old not in s:
        print("MISS", old[:60])
    s = s.replace(old, new)
app.write_text(s, encoding="utf-8")

p = ROOT / "scripts" / "make_thumbs.py"
t = p.read_text(encoding="utf-8")
t = t.replace("if w > 420:", "if w > 600:")
t = t.replace("im.resize((420, max(1, round(h * 420 / w)))", "im.resize((600, max(1, round(h * 600 / w)))")
t = t.replace("quality=72", "quality=78")
p.write_text(t, encoding="utf-8")
print("patched")
