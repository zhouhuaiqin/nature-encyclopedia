# -*- coding: utf-8 -*-
"""为占位图物种恢复本种照片（严格学名匹配 + 合法许可 + 全站唯一）；失败则保持占位图。"""
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi
import improve_photos as ip

ROOT = Path(__file__).resolve().parent.parent


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
    targets = [e for e in plan.values()
               if "原创占位图" in ((ledger.get(e["id"]) or {}).get("note") or "")]
    print("占位图待恢复:", len(targets), flush=True)
    lock = threading.Lock()
    stats = {"restored": 0, "still": 0}

    def process(e):
        sid = e["id"]
        p = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
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
                used[h] = {sid}
                ledger[sid] = {
                    "author": ph.get("attribution") or "iNaturalist contributor",
                    "license": (ph.get("license_code") or "cc0").lower(),
                    "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                    "name": e["name"], "latin": e["latin"], "photoId": ph.get("id"),
                    "note": "本种照片（恢复补图，可合法用于非商业展示）",
                }
            return "restored"
        return "still"

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(process, e): e for e in targets}
        done = 0
        for fut in as_completed(futures):
            e = futures[fut]
            try:
                kind = fut.result()
            except Exception:  # noqa: BLE001
                kind = "still"
            stats[kind] += 1
            done += 1
            if done % 10 == 0:
                with lock:
                    fi.write_credits(ledger)
                print(f"[{done}/{len(targets)}] restored={stats['restored']} still={stats['still']}",
                      flush=True)
    with lock:
        fi.write_credits(ledger)
    print("完成:", stats, flush=True)


if __name__ == "__main__":
    main()
