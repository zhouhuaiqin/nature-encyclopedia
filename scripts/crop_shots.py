# -*- coding: utf-8 -*-
from PIL import Image

im = Image.open("plan/shots/v3-tall2.png")
print("size", im.size)
w, h = im.size
im.crop((0, 2050, w, 2900)).save("plan/shots/v3-featured-crop.png")
im.crop((0, 2750, w, min(h, 4800))).save("plan/shots/v3-browse-crop.png")
print("cropped")
