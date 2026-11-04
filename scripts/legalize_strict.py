# -*- coding: utf-8 -*-
"""严格许可清理：只替换「保留所有权利 / GFDL / 禁止演绎(ND)」等确实不可用的图片。
NC（非商业）图片保留用于本站非商业学习用途，并保留署名与许可链接。
用法：python scripts/legalize_strict.py --workers 4
"""
import argparse
import json
import shutil
import sys
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

BAD = {"all rights reserved", "gfdl", "cc-by-nd", "cc-by-nc-nd"}
GOOD = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "plan" / "legalize-report.json"


def genus_of(e):
    return (e["latin"].split() or [""])[0]


def dims(ph):
    w, h = fi.photo_dims(ph)
    return min(w, h) if w and h else 0


def collect_legal(taxon_id, limit=20):
    data = fi.api_get(
        fi.API + "/observations?taxon_id=" + str(taxon_id) +
        "&photos=true&photo_license=cc0,cc-by,cc-by-sa&per_page=" + str(limit) + "&order_by=votes"
    )
    out = []
    for obs in (data or {}).get("results") or []:
        for ph in obs.get("photos") or []:
            if (ph.get("license_code") or "").lower() in {"cc0", "cc-by", "cc-by-sa"}:
                url = ph.get("url", "")
                ph["medium_url"] = url.replace("/square.", "/medium.") if "/square." in url else url
                out.append(ph)
    return out


def find_photos(entry):
    photos = []
    taxon = fi.find_taxon(entry)
    if taxon:
        photos = collect_legal(taxon["id"])
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
    out = fi.IMG_DIR / entry["tab"] / (sid + ".jpg")
    rec = ledger.get(sid) or {}
    lic = (rec.get("license") or "").lower()
    if lic not in BAD:
        return "kept", sid
    g = genus_of(entry)
    if g in legal_index:
        donor = legal_index[g][0]
        src = fi.IMG_DIR / donor["tab"] / (donor["id"] + ".jpg")
        if src.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out)
            new = dict(ledger[donor["id"]])
            new["name"], new["latin"] = entry["name"], entry["latin"]
            new["note"] = "同属近缘种代表照片（可商用许可）"
            with lock:
                ledger[sid] = new
            return "reused", sid
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
        with lock:
            ledger[sid] = {
                "author": ph.get("attribution") or "iNaturalist contributor",
                "license": (ph.get("license_code") or "cc0").lower(),
                "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                "name": entry["name"], "latin": entry["latin"], "photoId": ph.get("id"),
                "note": "可商用许可（CC0/公有领域/CC BY/CC BY-SA）",
            }
        return "replaced", sid
    if out.exists():
        out.unlink()
    ledger.pop(sid, None)
    return "placeholder", sid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    fi.API_LIMITER = fi.RateLimiter(0.8)

    plan = fi.load_plan()
    ledger = fi.load_json(fi.LEDGER, {})
    lock = threading.Lock()
    legal_index = defaultdict(list)
    for e in plan:
        rec = ledger.get(e["id"]) or {}
        if (rec.get("license") or "").lower() in GOOD and (fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")).exists():
            legal_index[genus_of(e)].append(e)

    targets = [e for e in plan if (ledger.get(e["id"], {}).get("license") or "").lower() in BAD]
    print("待处理图片:", len(targets))
    stats = Counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process, e, legal_index, ledger, lock): e for e in targets}
        for fut in as_completed(futures):
            try:
                kind, sid = fut.result()
            except Exception as exc:  # noqa: BLE001
                kind, sid = "failed", futures[fut]["id"]
                print("失败", sid, exc)
            stats[kind] += 1
            if sum(stats.values()) % 5 == 0:
                with lock:
                    fi.write_credits(ledger)
                print("进度", sum(stats.values()), dict(stats), flush=True)

    with lock:
        fi.write_credits(ledger)
    all_lic = Counter((v.get("license") or "none").lower() for v in ledger.values())
    REPORT.write_text(json.dumps({"strict": dict(stats), "licenseDistribution": dict(all_lic),
                                  "credits": len(ledger)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成", dict(stats))
    print("许可分布", dict(all_lic))


if __name__ == "__main__":
    main()
