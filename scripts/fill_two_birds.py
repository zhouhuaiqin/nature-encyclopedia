# -*- coding: utf-8 -*-
import io, json, sys, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_images as fi

OPENER = urllib.request.build_opener()
ITEMS = [
    {"id": "bird-yellow-bellied-tit", "name": "黄腹山雀", "latin": "Pardaliparus venustulus"},
    {"id": "bird-white-bellied-sea-eagle", "name": "白腹海雕", "latin": "Haliaeetus leucogaster"},
]

def getj(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "ne-birds2"})
        with OPENER.open(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

def fetch(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "ne-birds2"})
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
    im.save(ROOT / "assets/images/animals" / (e["id"] + ".webp"), "WEBP", quality=85, method=6)
    t = im if im.width <= 600 else im.resize((600, max(1, round(im.height * 600 / im.width))), Image.LANCZOS)
    t.save(ROOT / "assets/thumbs/animals" / (e["id"] + ".webp"), "WEBP", quality=78, method=4)
    return {"author": author, "license": lic, "source": source, "name": e["name"], "latin": e["latin"],
            **({"photoId": photo_id} if photo_id else {}),
            "note": "新增鸟类补图（分类页/GBIF，未核验许可，仅个人学习参考）"}

ledger = fi.load_json(fi.LEDGER, {})
for e in ITEMS:
    q = urllib.parse.quote(e["latin"])
    done = False
    taxa = getj(fi.API + "/taxa?q=" + q + "&per_page=5")
    for t in (taxa or {}).get("results") or []:
        name = (t.get("name") or "").lower()
        if not name:
            continue
        detail = getj(fi.API + "/taxa/" + str(t.get("id")))
        for p in (detail or {}).get("taxon_photos") or []:
            ph = p.get("photo") or p
            raw = fetch((ph.get("url") or "").replace("/square.", "/large."))
            if raw:
                ledger[e["id"]] = save(e, raw, ph.get("attribution") or "iNaturalist contributor",
                                       (ph.get("license_code") or "").lower() or "arr",
                                       "https://www.inaturalist.org/photos/" + str(ph.get("id")), ph.get("id"))
                print("OK taxa", e["id"], flush=True); done = True; break
        if done: break
    if done: continue
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
print("done")
