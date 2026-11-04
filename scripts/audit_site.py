# -*- coding: utf-8 -*-
"""站点体检：图片许可分布、体积、数据体量、QA 概览。"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

s = (ROOT / "js" / "image-credits.js").read_text(encoding="utf-8")
lic = re.findall(r'"license":\s*"([^"]*)"', s)
c = Counter(x.lower() for x in lic)
print("credits total:", len(lic))
for k, v in c.most_common(15):
    print(f"  {k}: {v}")

imgs = list((ROOT / "assets" / "images" / "animals").glob("*.jpg")) + list(
    (ROOT / "assets" / "images" / "plants").glob("*.jpg")
)
sizes = sorted(x.stat().st_size for x in imgs)
print("images:", len(imgs), "total MB:", round(sum(sizes) / 1048576, 1),
      "median KB:", round(sizes[len(sizes) // 2] / 1024), "max KB:", round(sizes[-1] / 1024))
data = list((ROOT / "data").rglob("*.js"))
print("data JS total MB:", round(sum(x.stat().st_size for x in data) / 1048576, 2))
js = list((ROOT / "js").glob("*.js"))
print("app JS MB:", round(sum(x.stat().st_size for x in js) / 1048576, 2))

qa = json.loads((ROOT / "plan" / "qa-content.json").read_text(encoding="utf-8"))
print("qa issues:", len(qa.get("issues") or []), "warnings:", qa.get("warningCount"))
print("lengthStats:", json.dumps(qa.get("lengthStats"), ensure_ascii=False)[:300])
print("conservationKinds:", json.dumps(qa.get("conservationKinds"), ensure_ascii=False)[:300])
print("missingFields:", json.dumps(qa.get("missingFields"), ensure_ascii=False)[:300])
