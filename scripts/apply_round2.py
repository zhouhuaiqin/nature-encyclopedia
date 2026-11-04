# -*- coding: utf-8 -*-
"""应用第二轮人工挑选的候选图。"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
CHOICES = {
    "mammal-snow-leopard": 4,
    "mammal-gorilla": 2,
    "bird-red-crowned-crane": 2,
    "bird-crested-ibis": 3,
    "bird-green-peafowl": 1,
    "bird-bald-eagle": 6,
    "bird-snowy-owl": 1,
    "bird-greater-flamingo": 4,
    "bird-emperor-penguin": 4,
    "mammal-pere-davids-deer": 1,
    "mammal-tibetan-antelope": 3,
}


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-curate2"})
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read()
    except Exception:
        return None


def main():
    cands = json.loads((ROOT / "plan" / "curate2" / "candidates.json").read_text(encoding="utf-8"))
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    for sid, idx in CHOICES.items():
        e = plan[sid]
        rows = cands.get(sid) or []
        if idx > len(rows):
            print("no candidate", sid, idx)
            continue
        row = rows[idx - 1]
        saved = False
        for variant in ("medium", "large"):
            raw = fetch(row["url"].replace("/small.", "/" + variant + "."))
            if not raw:
                continue
            saved_ok, err = fi.save_image(e, raw)
            print(sid, variant, err)
            if not err:
                saved = True
                break
        if saved:
            ledger[sid] = {
                "author": row.get("attribution") or "iNaturalist contributor",
                "license": row.get("license") or "cc-by-nc",
                "source": "https://www.inaturalist.org/photos/" + str(row.get("photoId")),
                "name": e["name"], "latin": e["latin"], "photoId": row.get("photoId"),
                "note": "代表物种人工优选（第二轮，本种、合法许可）",
            }
    fi.write_credits(ledger)
    print("done")


if __name__ == "__main__":
    main()
