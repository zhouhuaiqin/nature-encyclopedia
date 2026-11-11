# -*- coding: utf-8 -*-
import io, json, sys, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_images as fi

OPENER = urllib.request.build_opener()
ITEMS = [
    {"id": "bird-white-bellied-sea-eagle", "name": "白腹海雕", "latin": "Haliaeetus leucogaster"},
    {"id": "bird-silver-throated-bushtit", "name": "银喉长尾山雀", "latin": "Aegithalos glaucogularis"},
]

def getj(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "ne-birds3"})
        with OPENER.open(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

def fetch(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "ne-birds3"})
        with OPENER.open(req, timeout=40) as r:
            return r.read()
    except Exception:
        return None

ledger = fi.load_json(fi.LEDGER, {})
for e in ITEMS:
    q = urllib.parse.quote(e["latin"])
    d = getj(fi.API + "/observations?taxon_name=" + q + "&photos=true&per_page=5&order_by=votes")
    best = None
    for obs in (d or {}).get("results") or []:
        for ph in obs.get("photos") or []:
            raw = fetch((ph.get("url") or "").replace("/square.", "/large."))
            if not raw:
                continue
            try:
                im = Image.open(io.BytesIO(raw)); im.load()
            except Exception:
                continue
            w, h = im.size
            if min(w, h) < 400:
                continue
            score = min(w, h) - abs(w / h - 1.4) * 100
            if best is None or score > best[0]:
                best = (score, raw, ph, im)
    if not best:
        print("NONE", e["id"], flush=True); continue
    score, raw, ph, im = best
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    w, h = im.size
    if w > 900:
        im = im.resize((900, max(1, round(h * 900 / w))), Image.LANCZOS)
    im.save(ROOT / "assets/images/animals" / (e["id"] + ".webp"), "WEBP", quality=85, method=6)
    t = im if im.width <= 600 else im.resize((600, max(1, round(im.height * 600 / im.width))), Image.LANCZOS)
    t.save(ROOT / "assets/thumbs/animals" / (e["id"] + ".webp"), "WEBP", quality=78, method=4)
    ledger[e["id"]] = {"author": ph.get("attribution") or "iNaturalist contributor",
                       "license": (ph.get("license_code") or "").lower() or "arr",
                       "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                       "name": e["name"], "latin": e["latin"], "photoId": ph.get("id"),
                       "note": "新增鸟类补图（本种，许可未核验，仅个人学习参考）"}
    print("OK", e["id"], im.size, flush=True)
fi.write_credits(ledger)
print("done")
