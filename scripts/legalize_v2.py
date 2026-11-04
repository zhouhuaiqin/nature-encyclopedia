# -*- coding: utf-8 -*-
"""图片合法化 v2：同属合法图复用 + 联网只抓可商用许可（CC0/PD/CC BY/CC BY-SA）medium 图。
用法：python scripts/legalize_v2.py --workers 8 [--limit N]
"""
import argparse
import json
import shutil
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

LEGAL = {"cc0", "pd", "cc-by", "cc-by-sa"}
ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "plan" / "legalize-report.json"


def genus_of(entry):
    return (entry["latin"].split() or [""])[0]


def dims(ph):
    w, h = fi.photo_dims(ph)
    return min(w, h) if w and h else 0


def collect_legal(taxon_id, limit=20):
    data = fi.api_get(
        fi.API + "/observations?taxon_id=" + str(taxon_id) +
        "&photos=true&photo_license=cc0,cc-by,cc-by-sa&per_page=" + str(limit) + "&order_by=votes"
    )
    photos = []
    for obs in (data or {}).get("results") or []:
        for ph in obs.get("photos") or []:
            if (ph.get("license_code") or "").lower() in LEGAL:
                url = ph.get("url", "")
                ph["medium_url"] = url.replace("/square.", "/medium.") if "/square." in url else url
                photos.append(ph)
    return photos


def find_photos(entry):
    photos = []
    taxon = fi.find_taxon(entry)
    if taxon:
        photos = collect_legal(taxon["id"])
        if not photos:
            photos = [p for p in fi.taxon_photos(taxon["id"]) if (p.get("license_code") or "").lower() in LEGAL]
    if not photos:
        g = genus_of(entry)
        if g:
            res = fi.api_get(fi.API + "/taxa?q=" + quote(g) + "&rank=genus&per_page=3") or {}
            for t in res.get("results") or []:
                photos = collect_legal(t["id"], 10)
                if photos:
                    break
    photos.sort(key=dims, reverse=True)
    return photos


def process(entry, legal_index, ledger, lock):
    sid = entry["id"]
    tab = entry.get("tab") or "animals"
    out = fi.IMG_DIR / tab / (sid + ".jpg")
    if out.exists() and (ledger.get(sid, {}).get("license") or "").lower() in LEGAL:
        return "kept", sid, None
    g = genus_of(entry)
    if g in legal_index:
        donor = legal_index[g][0]
        src = fi.IMG_DIR / donor["tab"] / (donor["id"] + ".jpg")
        if src.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out)
            rec = dict(ledger[donor["id"]])
            rec["name"], rec["latin"] = entry["name"], entry["latin"]
            rec["note"] = "同属近缘种代表照片（可商用许可）"
            with lock:
                ledger[sid] = rec
            return "reused", sid, rec.get("license")

    for ph in find_photos(entry)[:6]:
        url = ph.get("medium_url") or ""
        if not url:
            continue
        raw = fi.download(url)
        if not raw:
            continue
        saved, err = fi.save_image(entry, raw)
        if err:
            continue
        rec = {
            "author": ph.get("attribution") or "iNaturalist contributor",
            "license": (ph.get("license_code") or "cc0").lower(),
            "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
            "name": entry["name"],
            "latin": entry["latin"],
            "photoId": ph.get("id"),
            "note": "可商用许可（CC0/公有领域/CC BY/CC BY-SA）",
        }
        with lock:
            ledger[sid] = rec
        return "replaced", sid, rec["license"]
    if out.exists():
        out.unlink()
    ledger.pop(sid, None)
    return "placeholder", sid, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    fi.API_LIMITER = fi.RateLimiter(0.6)

    plan = fi.load_plan()
    ledger = fi.load_json(fi.LEDGER, {})
    lock = threading.Lock()

    legal_index = defaultdict(list)
    for e in plan:
        rec = ledger.get(e["id"]) or {}
        if (rec.get("license") or "").lower() in LEGAL:
            if (fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")).exists():
                legal_index[genus_of(e)].append(e)

    if args.limit:
        plan = plan[: args.limit]

    stats = defaultdict(int)
    placeholders, failures = [], []
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process, e, legal_index, ledger, lock): e for e in plan}
        for fut in as_completed(futures):
            entry = futures[fut]
            try:
                kind, sid, extra = fut.result()
            except Exception as exc:  # noqa: BLE001
                kind, sid, extra = "failed", entry["id"], str(exc)
            stats[kind] += 1
            if kind == "placeholder":
                placeholders.append(sid)
            elif kind == "failed":
                failures.append([sid, extra])
            done += 1
            if done % 20 == 0:
                with lock:
                    fi.write_credits(ledger)
                print(f"[{done}/{len(plan)}] kept={stats['kept']} reused={stats['reused']} "
                      f"replaced={stats['replaced']} placeholder={stats['placeholder']} failed={stats['failed']}",
                      flush=True)

    with lock:
        fi.write_credits(ledger)
    REPORT.write_text(json.dumps({
        "legalLicenses": sorted(LEGAL),
        "total": len(plan),
        "stats": dict(stats),
        "placeholders": placeholders,
        "failures": failures,
        "credits": len(ledger),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成:", json.dumps(dict(stats), ensure_ascii=False),
          "占位图:", len(placeholders), "失败:", len(failures), flush=True)


if __name__ == "__main__":
    main()
