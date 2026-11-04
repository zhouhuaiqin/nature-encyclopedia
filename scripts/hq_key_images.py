# -*- coding: utf-8 -*-
"""重点物种（精选/封面）从 iNaturalist 原图重新导出更高质量 WebP。"""
import io
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LEDGER = json.loads((ROOT / "plan" / "image-credits.json").read_text(encoding="utf-8"))


def fetch(url, timeout=45):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nature-atlas-hq"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def main():
    meta = (ROOT / "data" / "meta.js").read_text(encoding="utf-8")
    feat = re.findall(r'"([a-z0-9-]+)"', re.search(r"window\.FEATURED = \[(.*?)\];", meta, re.S).group(1))
    cov = re.findall(r':\s*"([a-z0-9-]+)"', meta.split("window.CATEGORY_COVERS = {")[1].split("};")[0])
    icons = ["mammal-lion", "mammal-tiger", "mammal-snow-leopard", "mammal-gorilla",
             "bird-red-crowned-crane", "bird-crested-ibis", "mammal-jaguar", "mammal-puma",
             "mammal-kiang", "mammal-sperm-whale"]
    ids = list(dict.fromkeys(feat + cov + icons))
    plan = {}
    print("targets:", len(ids), flush=True)

    def one(sid):
        credit = LEDGER.get(sid) or {}
        pid = credit.get("photoId")
        if not pid:
            return ("skip", sid)
        raw = fetch("https://inaturalist-open-data.s3.amazonaws.com/photos/" + str(pid) + "/original.jpg")
        if not raw:
            return ("fail", sid)
        try:
            im = Image.open(io.BytesIO(raw))
            im.load()
        except Exception:
            return ("fail", sid)
        w, h = im.size
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        if w > 900:
            im = im.resize((900, max(1, round(h * 900 / w))), Image.LANCZOS)
        p = ROOT / "assets" / "images" / ("plants" if sid.startswith(("tree-", "shrub-", "flower-", "succulent-", "aquatic-", "fern-", "crop-", "fungus-")) else "animals") / (sid + ".webp")
        if not p.exists():
            # 根据数据中的 tab 再判断
            p = next((ROOT / "assets" / "images").rglob(sid + ".webp"), None)
        if not p:
            return ("skip", sid)
        im.save(p, "WEBP", quality=92, method=6)
        return ("ok", sid, w, h, p.stat().st_size)

    stats = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(one, sid): sid for sid in ids}
        for fut in as_completed(futures):
            try:
                res = fut.result()
            except Exception:
                res = ("fail", "?")
            stats[res[0]] = stats.get(res[0], 0) + 1
            print(res, flush=True)
    print("done:", stats)


if __name__ == "__main__":
    main()
