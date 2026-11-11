# -*- coding: utf-8 -*-
"""为新增鸟类抓取合法许可照片 + 600px 缩略图。"""
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
OPENER = urllib.request.build_opener()
LEGAL = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
ENTRIES = [
    {"id": "bird-heudes-parrotbill", "name": "震旦鸦雀", "latin": "Paradoxornis heudei"},
    {"id": "bird-silver-throated-bushtit", "name": "银喉长尾山雀", "latin": "Aegithalos glaucogularis"},
    {"id": "bird-daurian-redstart", "name": "北红尾鸲", "latin": "Phoenicurus auroreus"},
    {"id": "bird-yellow-bellied-tit", "name": "黄腹山雀", "latin": "Pardaliparus venustulus"},
    {"id": "bird-white-bellied-sea-eagle", "name": "白腹海雕", "latin": "Haliaeetus leucogaster"},
    {"id": "bird-black-naped-oriole", "name": "黑枕黄鹂", "latin": "Oriolus chinensis"},
]


def getj(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-birds"})
        with OPENER.open(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-birds"})
        with OPENER.open(req, timeout=40) as r:
            return r.read()
    except Exception:
        return None


def large(url):
    for v in ("square", "small", "medium"):
        if "/" + v + "." in url:
            return url.replace("/" + v + ".", "/large.")
    return url


def main():
    ledger = fi.load_json(fi.LEDGER, {})
    for e in ENTRIES:
        q = urllib.parse.quote(e["latin"])
        data = getj(fi.API + "/observations?taxon_name=" + q +
                    "&photos=true&quality_grade=research&order_by=votes&per_page=5&photo_license=" +
                    ",".join(sorted(LEGAL)))
        photo = None
        for obs in (data or {}).get("results") or []:
            tax = (obs.get("taxon") or {}).get("name") or ""
            if tax and not tax.lower().startswith(e["latin"].lower()):
                continue
            for ph in obs.get("photos") or []:
                if (ph.get("license_code") or "").lower() in LEGAL:
                    photo = ph
                    break
            if photo:
                break
        if not photo:
            print("NO PHOTO", e["id"], flush=True)
            continue
        raw = fetch(large(photo.get("url") or ""))
        if not raw:
            print("DOWNLOAD FAIL", e["id"], flush=True)
            continue
        im = Image.open(io.BytesIO(raw)); im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        w, h = im.size
        if w > 900:
            im = im.resize((900, max(1, round(h * 900 / w))), Image.LANCZOS)
        out = ROOT / "assets/images/animals" / (e["id"] + ".webp")
        im.save(out, "WEBP", quality=85, method=6)
        t = im if im.width <= 600 else im.resize((600, max(1, round(im.height * 600 / im.width))), Image.LANCZOS)
        tout = ROOT / "assets/thumbs/animals" / (e["id"] + ".webp")
        t.save(tout, "WEBP", quality=78, method=4)
        lic = (photo.get("license_code") or "").lower()
        ledger[e["id"]] = {
            "author": photo.get("attribution") or "iNaturalist contributor",
            "license": lic,
            "source": "https://www.inaturalist.org/photos/" + str(photo.get("id")),
            "name": e["name"], "latin": e["latin"], "photoId": photo.get("id"),
            "note": "新增鸟类补图（本种、合法许可）",
        }
        print("OK", e["id"], im.size, lic, flush=True)
    fi.write_credits(ledger)
    print("done", flush=True)


if __name__ == "__main__":
    main()
