# -*- coding: utf-8 -*-
"""修正人工审计发现的「图物种不符」图片：按学名严格匹配重新抓取本种照片；
找不到可用照片时改为占位图（避免继续展示错误图片）。"""
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi
import improve_photos as ip
import make_placeholders as mp

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "plan" / "image-species-audit.json"
IDS = [
    "mammal-jaguar",
    "fish-dabry-weatherfish", "fish-northern-snakehead", "fish-beluga-sturgeon",
    "fish-pond-loach", "fish-asiatic-snakehead", "fish-blunt-snout-bream",
    "fish-black-carp", "fish-european-eel",
    "reptile-american-alligator",
    "amphibian-tiger-salamander",
    "succulent-living-stones",
    "crustacean-japanese-spiny-lobster",
]


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    used = {}
    for e in plan.values():
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        if p.exists():
            used.setdefault(md5(p), set()).add(e["id"])
    lock = threading.Lock()

    def process(sid):
        e = plan[sid]
        p = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
        old = md5(p) if p.exists() else None
        for ph in ip.query_best(e["latin"])[:8]:
            raw = fi.download(ph.get("medium_url") or "")
            if not raw:
                continue
            saved, err = fi.save_image(e, raw)
            if err:
                continue
            h = md5(p)
            with lock:
                others = used.get(h, set()) - {sid}
            if others:
                continue
            with lock:
                if old and old in used:
                    used[old].discard(sid)
                used[h] = {sid}
                ledger[sid] = {
                    "author": ph.get("attribution") or "iNaturalist contributor",
                    "license": (ph.get("license_code") or "cc0").lower(),
                    "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                    "name": e["name"], "latin": e["latin"], "photoId": ph.get("id"),
                    "note": "本种照片（审计修正，可合法用于非商业展示）",
                }
            return "fixed"
        mp.make_placeholder(e, p)
        with lock:
            if old and old in used:
                used[old].discard(sid)
            ledger[sid] = {
                "author": "自然图鉴（本站自绘）", "license": "cc0", "source": "本站原创占位图",
                "name": e["name"], "latin": e["latin"], "note": "原创占位图（CC0），非真实照片",
            }
        return "placeholder"

    stats = {"fixed": 0, "placeholder": 0}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(process, sid): sid for sid in IDS}
        for fut in as_completed(futures):
            try:
                stats[fut.result()] += 1
            except Exception:  # noqa: BLE001
                stats["placeholder"] += 1
    fi.write_credits(ledger)
    print("审计修正:", stats, flush=True)


if __name__ == "__main__":
    main()
