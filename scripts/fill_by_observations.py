# -*- coding: utf-8 -*-
"""用 iNaturalist 观测记录（按许可过滤）为本种补齐照片。
只接受 CC0 / 公有领域 / CC BY / CC BY-SA / CC BY-NC / CC BY-NC-SA；
只接受 taxon 学名与本种一致的观测；不接受同属/近缘种、不接受 ND/ARR。
"""
import argparse
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ALLOWED = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "plan" / "photo-fill-report.json"


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def species_key(latin):
    """去掉栽培品种/亚种后的学名两词，用于匹配同种（允许亚种/品种照片）。"""
    s = latin.replace("×", "").strip()
    s = re.split(r"'", s)[0]
    parts = [p for p in s.split() if p]
    return " ".join(parts[:2]).lower()


def dims(ph):
    od = ph.get("original_dimensions") or {}
    w = od.get("width") or 0
    h = od.get("height") or 0
    return min(w, h) if w and h else 0


def query_photos(latin):
    key = species_key(latin)
    url = (fi.API + "/observations?taxon_name=" + quote(latin) +
           "&photos=true&photo_license=cc0,cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa"
           "&per_page=5&order_by=votes")
    data = fi.api_get(url)
    photos = []
    for obs in (data or {}).get("results") or []:
        taxon = obs.get("taxon") or {}
        tname = norm(taxon.get("name"))
        if not (tname == key or tname.startswith(key + " ")):
            continue
        for ph in obs.get("photos") or []:
            lic = (ph.get("license_code") or "").lower()
            if lic not in ALLOWED:
                continue
            url2 = ph.get("url", "")
            ph["medium_url"] = url2.replace("/square.", "/medium.") if "/square." in url2 else url2
            photos.append(ph)
    photos.sort(key=dims, reverse=True)
    return photos


def process(entry, ledger, lock):
    sid = entry["id"]
    photos = query_photos(entry["latin"])
    for ph in photos[:8]:
        url = ph.get("medium_url") or ""
        if not url:
            continue
        raw = fi.download(url)
        if not raw:
            continue
        saved, err = fi.save_image(entry, raw)
        if err:
            continue
        lic = (ph.get("license_code") or "").lower()
        rec = {
            "author": ph.get("attribution") or "iNaturalist contributor",
            "license": lic,
            "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
            "name": entry["name"],
            "latin": entry["latin"],
            "photoId": ph.get("id"),
            "note": "本种照片（可合法用于非商业展示）",
        }
        with lock:
            ledger[sid] = rec
        return "filled", sid, lic
    return "failed", sid, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    fi.API_LIMITER = fi.RateLimiter(1.0)

    plan = fi.load_plan()
    ledger = fi.load_json(fi.LEDGER, {})
    lock = threading.Lock()
    targets = [e for e in plan
               if "原创占位图" in ((ledger.get(e["id"]) or {}).get("note") or "")]
    if args.limit:
        targets = targets[: args.limit]
    print("待补图:", len(targets), flush=True)

    stats = {"filled": 0, "failed": 0}
    failed = []
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process, e, ledger, lock): e for e in targets}
        for fut in as_completed(futures):
            entry = futures[fut]
            try:
                kind, sid, lic = fut.result()
            except Exception as exc:  # noqa: BLE001
                kind, sid, lic = "failed", entry["id"], str(exc)
            stats[kind] += 1
            if kind == "failed":
                failed.append([sid, entry["name"], entry["latin"], lic])
            done += 1
            if done % 20 == 0:
                with lock:
                    fi.write_credits(ledger)
                print(f"[{done}/{len(targets)}] filled={stats['filled']} failed={stats['failed']}", flush=True)

    with lock:
        fi.write_credits(ledger)
    REPORT.write_text(json.dumps({"targets": len(targets), "stats": stats, "failed": failed},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成:", stats, "失败:", len(failed), flush=True)


if __name__ == "__main__":
    main()
