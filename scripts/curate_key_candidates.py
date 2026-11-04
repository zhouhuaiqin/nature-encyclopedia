# -*- coding: utf-8 -*-
"""为精选/封面物种抓取候选缩略图，生成人工挑选用联系表。"""
import hashlib
import json
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "plan" / "curate"
LEGAL = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
IDS = ['mammal-giant-panda', 'bird-red-crowned-crane', 'insect-blue-morpho', 'aquatic-giant-water-lily',
       'mammal-tiger', 'fungus-fly-agaric', 'bird-crested-ibis', 'tree-ginkgo', 'fish-whale-shark',
       'flower-common-sunflower', 'reptile-komodo-dragon', 'amphibian-red-eyed-tree-frog',
       'arachnid-mexican-red-knee', 'crustacean-coconut-crab', 'mollusk-chambered-nautilus',
       'invertebrate-moon-jelly', 'shrub-tree-peony', 'succulent-golden-barrel-cactus',
       'aquatic-sacred-lotus', 'fern-spinulose-tree-fern', 'crop-asian-rice']


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": "nature-encyclopedia-curate"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def thumb_url(ph):
    for v in ("square", "small", "medium"):
        if "/" + v + "." in (ph.get("url") or ""):
            return ph["url"].replace("/" + v + ".", "/small.")
    return ph.get("url") or ""


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    OUT.mkdir(parents=True, exist_ok=True)
    cands = {}
    lock = threading.Lock()

    def one(sid):
        e = plan[sid]
        import urllib.parse
        url = (fi.API + "/observations?taxon_name=" + urllib.parse.quote(e["latin"]) +
               "&photos=true&quality_grade=research&order_by=votes&per_page=8&photo_license=" +
               ",".join(sorted(LEGAL)))
        data = fi.api_get(url)
        rows = []
        for obs in (data or {}).get("results") or []:
            tax = (obs.get("taxon") or {}).get("name") or ""
            if tax and not tax.lower().startswith(e["latin"].lower()):
                continue
            phs = [p for p in (obs.get("photos") or []) if (p.get("license_code") or "").lower() in LEGAL]
            if not phs:
                continue
            ph = phs[0]
            rows.append({"photoId": ph.get("id"), "license": (ph.get("license_code") or "").lower(),
                         "attribution": ph.get("attribution") or "", "url": thumb_url(ph)})
        return sid, rows[:6]

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(one, sid) for sid in IDS]
        for fut in as_completed(futures):
            try:
                sid, rows = fut.result()
            except Exception as exc:  # noqa: BLE001
                print("ERR", exc, flush=True)
                continue
            with lock:
                cands[sid] = rows
            d = OUT / sid
            d.mkdir(parents=True, exist_ok=True)
            for i, row in enumerate(rows):
                raw = fetch(row["url"])
                if raw:
                    (d / f"{i + 1}.jpg").write_bytes(raw)
    (OUT / "candidates.json").write_text(json.dumps(cands, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
    except Exception:
        font = ImageFont.load_default()
    CW, CH = 200, 170
    per_sheet = 6
    sids = list(IDS)
    for s in range(0, len(sids), per_sheet):
        group = sids[s:s + per_sheet]
        cols = 6
        sheet = Image.new("RGB", (CW * cols, CH * len(group) + 24), (245, 241, 232))
        d = ImageDraw.Draw(sheet)
        d.text((8, 4), f"candidates {s // per_sheet + 1} (choose best index per row)", fill=(22, 56, 42), font=font)
        for r, sid in enumerate(group):
            e = plan[sid]
            d.text((8, 24 + r * CH + 4), e["name"] + "  " + sid, fill=(160, 40, 40), font=font)
            for i in range(6):
                x = i * CW
                y = 24 + r * CH
                p = OUT / sid / f"{i + 1}.jpg"
                if not p.exists():
                    continue
                try:
                    im = Image.open(p).convert("RGB")
                    im.thumbnail((CW - 8, CH - 34))
                    sheet.paste(im, (x + 4, y + 24))
                except Exception:
                    continue
                d.text((x + 6, y + CH - 22), str(i + 1), fill=(30, 40, 34), font=font)
        out = ROOT / "plan" / "shots" / f"curate-{s // per_sheet + 1}.jpg"
        sheet.save(out, quality=88)
        print("sheet", out.name, len(group))
    print("candidates fetched")


if __name__ == "__main__":
    main()
