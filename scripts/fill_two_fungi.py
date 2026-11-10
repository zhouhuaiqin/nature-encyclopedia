# -*- coding: utf-8 -*-
"""为牛樟芝/鸡枞尝试 iNat 分类页照片与 GBIF 图像。"""
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_images as fi

PROXY = "http://127.0.0.1:7877"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
ITEMS = [
    {"id": "fungus-antrodia-cinnamomea", "name": "牛樟芝", "latin": "Antrodia cinnamomea"},
    {"id": "fungus-termitomyces", "name": "鸡枞", "latin": "Termitomyces albuminosus"},
]


def getj(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-two"})
        with OPENER.open(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-two"})
        with OPENER.open(req, timeout=40) as r:
            return r.read()
    except Exception:
        return None


def save(e, raw, author, lic, source, photo_id=None):
    im = Image.open(io.BytesIO(raw)); im.load()
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    w, h = im.size
    if w > 900:
        im = im.resize((900, max(1, round(h * 900 / w))), Image.LANCZOS)
    out = ROOT / "assets/images/plants" / (e["id"] + ".webp")
    im.save(out, "WEBP", quality=85, method=6)
    t = im if im.width <= 600 else im.resize((600, max(1, round(im.height * 600 / im.width))), Image.LANCZOS)
    tout = ROOT / "assets/thumbs/plants" / (e["id"] + ".webp")
    t.save(tout, "WEBP", quality=78, method=4)
    return {"author": author, "license": lic, "source": source, "name": e["name"],
            "latin": e["latin"], **({"photoId": photo_id} if photo_id else {}),
            "note": "新增物种补图（分类页/GBIF，未核验许可，仅个人学习参考）"}


def main():
    ledger = fi.load_json(fi.LEDGER, {})
    for e in ITEMS:
        done = False
        q = urllib.parse.quote(e["latin"])
        taxa = getj(fi.API + "/taxa?q=" + q + "&per_page=5")
        for t in (taxa or {}).get("results") or []:
            name = (t.get("name") or "").lower()
            if not name or not (name.startswith(e["latin"].split()[0].lower()) or e["latin"].lower() in name):
                continue
            detail = getj(fi.API + "/taxa/" + str(t.get("id")))
            for p in (detail or {}).get("taxon_photos") or []:
                ph = p.get("photo") or p
                raw = fetch((ph.get("url") or "").replace("/square.", "/large."))
                if raw:
                    ledger[e["id"]] = save(e, raw, ph.get("attribution") or "iNaturalist contributor",
                                           (ph.get("license_code") or "").lower() or "arr",
                                           "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                                           ph.get("id"))
                    print("OK taxa", e["id"], flush=True); done = True; break
            if done: break
        if done: continue
        # GBIF
        m = getj("https://api.gbif.org/v1/species/match?name=" + q)
        key = (m or {}).get("usageKey")
        if key:
            d = getj("https://api.gbif.org/v1/occurrence/search?taxonKey=" + str(key) + "&mediaType=StillImage&limit=10")
            for occ in (d or {}).get("results") or []:
                for md in occ.get("media") or []:
                    raw = fetch(md.get("identifier"))
                    if raw:
                        ledger[e["id"]] = save(e, raw, md.get("rightsHolder") or "GBIF 数据提供者",
                                               (md.get("license") or "unknown").lower(), md.get("identifier"))
                        print("OK gbif", e["id"], flush=True); done = True; break
                if done: break
        if not done: print("NONE", e["id"], flush=True)
    fi.write_credits(ledger)
    print("done", flush=True)


if __name__ == "__main__":
    main()
