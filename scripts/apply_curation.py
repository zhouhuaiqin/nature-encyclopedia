# -*- coding: utf-8 -*-
"""应用人工挑选的候选图（下载中大图、写入版权）。"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
CHOICES = {
    "mammal-giant-panda": 2,
    "bird-red-crowned-crane": 3,
    "insect-blue-morpho": 4,
    "aquatic-giant-water-lily": 1,
    "fungus-fly-agaric": 2,
    "bird-crested-ibis": 2,
    "tree-ginkgo": 1,
    "fish-whale-shark": 5,
    "flower-common-sunflower": 1,
    "reptile-komodo-dragon": 1,
    "amphibian-red-eyed-tree-frog": 3,
    "arachnid-mexican-red-knee": 1,
    "crustacean-coconut-crab": 3,
    "invertebrate-moon-jelly": 2,
    "aquatic-sacred-lotus": 5,
    "fern-spinulose-tree-fern": 2,
    "crop-asian-rice": 2,
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nature-encyclopedia-curate"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except Exception:
        return None


def main():
    cands = json.loads((ROOT / "plan" / "curate" / "candidates.json").read_text(encoding="utf-8"))
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    for sid, idx in CHOICES.items():
        e = plan[sid]
        rows = cands.get(sid) or []
        if idx - 1 >= len(rows):
            print("no candidate", sid, idx)
            continue
        row = rows[idx - 1]
        url = row["url"].replace("/small.", "/medium.")
        raw = fetch(url)
        if not raw:
            raw = fetch(row["url"].replace("/small.", "/large."))
        if not raw:
            print("download fail", sid)
            continue
        saved, err = fi.save_image(e, raw)
        if err:
            print("save fail", sid, err)
            continue
        ledger[sid] = {
            "author": row.get("attribution") or "iNaturalist contributor",
            "license": row.get("license") or "cc-by-nc",
            "source": "https://www.inaturalist.org/photos/" + str(row.get("photoId")),
            "name": e["name"], "latin": e["latin"], "photoId": row.get("photoId"),
            "note": "代表物种人工优选（本种、合法许可）",
        }
        print("ok", sid, idx)
    fi.write_credits(ledger)
    print("done")


if __name__ == "__main__":
    main()
