# -*- coding: utf-8 -*-
"""为新增物种下载合法许可照片，保存 900px 原图与 600px 缩略 WebP。"""
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
LEGAL = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}

ENTRIES = [
    {"id": "mammal-tibetan-fox", "name": "藏狐", "latin": "Vulpes ferrilata", "tab": "animals"},
    {"id": "flower-venus-flytrap", "name": "捕蝇草", "latin": "Dionaea muscipula", "tab": "plants"},
    {"id": "flower-tropical-pitcher", "name": "猪笼草", "latin": "Nepenthes mirabilis", "tab": "plants"},
    {"id": "fungus-puffball", "name": "马勃", "latin": "Lycoperdon perlatum", "tab": "fungi"},
    {"id": "fungus-termitomyces", "name": "鸡枞", "latin": "Termitomyces albuminosus", "tab": "fungi"},
    {"id": "fungus-red-russula", "name": "大红菌", "latin": "Russula vinosa", "tab": "fungi"},
]


def get_json(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nature-atlas-new"})
        with OPENER.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def fetch(url, timeout=45):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nature-atlas-new"})
        with OPENER.open(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def iit(url):
    for v in ("square", "small", "medium"):
        if "/" + v + "." in url:
            return url.replace("/" + v + ".", "/large.")
    return url


def main():
    ledger = fi.load_json(fi.LEDGER, {})
    for e in ENTRIES:
        q = urllib.parse.quote(e["latin"])
        data = get_json(fi.API + "/observations?taxon_name=" + q +
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
        raw = fetch(iit(photo.get("url") or ""))
        if not raw:
            print("DOWNLOAD FAIL", e["id"], flush=True)
            continue
        im = Image.open(io.BytesIO(raw))
        im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        w, h = im.size
        if w > 900:
            im = im.resize((900, max(1, round(h * 900 / w))), Image.LANCZOS)
        folder = "animals" if e["tab"] == "animals" else "plants"
        out = ROOT / "assets" / "images" / folder / (e["id"] + ".webp")
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "WEBP", quality=85, method=6)
        tw, th = im.size
        if tw > 600:
            tim = im.resize((600, max(1, round(th * 600 / tw))), Image.LANCZOS)
        else:
            tim = im
        tout = ROOT / "assets" / "thumbs" / folder / (e["id"] + ".webp")
        tout.parent.mkdir(parents=True, exist_ok=True)
        tim.save(tout, "WEBP", quality=78, method=4)
        lic = (photo.get("license_code") or "").lower()
        ledger[e["id"]] = {
            "author": photo.get("attribution") or "iNaturalist contributor",
            "license": lic,
            "source": "https://www.inaturalist.org/photos/" + str(photo.get("id")),
            "name": e["name"], "latin": e["latin"], "photoId": photo.get("id"),
            "note": "新增物种补图（本种、合法许可）",
        }
        print("OK", e["id"], im.size, lic, flush=True)
    fi.write_credits(ledger)
    print("done", flush=True)


if __name__ == "__main__":
    main()
