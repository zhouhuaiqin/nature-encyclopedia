# -*- coding: utf-8 -*-
"""图片合法化：把 NC/ND/ARR/GFDL 等不利于商用的图片，替换成 CC0 / 公有领域 / CC BY / CC BY-SA
（允许商业使用，需署名；SA 需相同方式共享）的照片。找不到合法照片时删除图片与版权记录，
前端会显示站点自绘的合法占位图。

用法：
    python scripts/legalize_images.py --workers 6
    python scripts/legalize_images.py --workers 6 --limit 50    # 先试跑
"""
import argparse
from urllib.parse import quote
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi  # noqa: E402

LEGAL = {"cc0", "pd", "cc-by", "cc-by-sa"}
REPORT = Path(__file__).resolve().parent.parent / "plan" / "legalize-report.json"


def legal_photo_dims(ph):
    w, h = fi.photo_dims(ph)
    return min(w, h) if w and h else 0


def collect_from_taxon(taxon_id, limit=20):
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


def find_legal_for(entry):
    photos = []
    taxon = fi.find_taxon(entry)
    if taxon:
        photos = collect_from_taxon(taxon["id"])
        if not photos:
            photos = [p for p in fi.taxon_photos(taxon["id"]) if (p.get("license_code") or "").lower() in LEGAL]
    if not photos:
        # 同属兜底（仍为合法许可）
        parts = entry["latin"].split()
        if len(parts) >= 2:
            genus = parts[0]
            results = fi.api_get(fi.API + "/taxa?q=" + quote(genus) + "&rank=genus&per_page=3") or {}
            for t in results.get("results") or []:
                photos = collect_from_taxon(t["id"], 10)
                if photos:
                    break
    if not photos:
        return None
    photos.sort(key=legal_photo_dims, reverse=True)
    return photos


def process(entry, ledger, lock):
    sid = entry["id"]
    tab = entry.get("tab") or ("plants" if entry.get("category") in {
        "trees", "shrubs", "flowers", "succulents", "aquatic", "ferns-gymnosperms", "crops", "fungi"
    } else "animals")
    path = fi.IMG_DIR / tab / (sid + ".jpg")
    rec = ledger.get(sid)
    if path.exists() and rec and (rec.get("license") or "").lower() in LEGAL:
        return "kept", sid, None
    photos = find_legal_for(entry)
    if not photos:
        # 没有合法图片：删除旧图与旧版权记录，前端显示自绘占位图
        if path.exists():
            path.unlink()
        ledger.pop(sid, None)
        return "placeholder", sid, None
    for ph in photos[:8]:
        raw = None
        for url in fi.variant_urls(ph):
            raw = fi.download(url)
            if raw:
                break
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
    return "failed", sid, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    plan = fi.load_plan()
    ledger = fi.load_json(fi.LEDGER, {})
    import threading
    lock = threading.Lock()

    if args.limit:
        plan = plan[: args.limit]

    stats = {"kept": 0, "replaced": 0, "placeholder": 0, "failed": 0}
    placeholders, failures = [], []
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process, e, ledger, lock): e for e in plan}
        for fut in as_completed(futures):
            entry = futures[fut]
            try:
                kind, sid, extra = fut.result()
            except Exception as exc:  # noqa: BLE001
                kind, sid, extra = "failed", entry["id"], str(exc)
            stats[kind] = stats.get(kind, 0) + 1
            if kind == "placeholder":
                placeholders.append(sid)
            elif kind == "failed":
                failures.append([sid, extra])
            done += 1
            if done % 25 == 0:
                with lock:
                    fi.write_credits(ledger)
                print(f"[{done}/{len(plan)}] kept={stats['kept']} replaced={stats['replaced']} "
                      f"placeholder={stats['placeholder']} failed={stats['failed']}", flush=True)

    with lock:
        fi.write_credits(ledger)
    report = {
        "legalLicenses": sorted(LEGAL),
        "total": len(plan),
        "stats": stats,
        "placeholders": placeholders,
        "failures": failures,
        "credits": len(ledger),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成:", json.dumps(stats, ensure_ascii=False), "占位图:", len(placeholders), "失败:", len(failures))


if __name__ == "__main__":
    main()
