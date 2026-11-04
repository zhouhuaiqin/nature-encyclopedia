# -*- coding: utf-8 -*-
"""用社区投票靠前的「本种」观测照片，替换不清晰/过小/占位的图片。
只接受 CC0/PD/CC BY/CC BY-SA/CC BY-NC/CC BY-NC-SA；学名必须与本种一致。"""
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
REPORT = ROOT / "plan" / "photo-improve-report.json"


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def species_key(latin):
    s = latin.replace("×", "").strip()
    s = re.split(r"'", s)[0]
    parts = [p for p in s.split() if p]
    return " ".join(parts[:2]).lower()


def dims(ph):
    od = ph.get("original_dimensions") or {}
    w, h = od.get("width") or 0, od.get("height") or 0
    return w, h


def candidates(plan, ledger):
    out = []
    for e in plan:
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        note = (ledger.get(e["id"]) or {}).get("note") or ""
        ph = "原创占位图" in note
        w = h = 0
        size = 0
        if p.exists():
            try:
                from PIL import Image
                im = Image.open(p)
                w, h = im.size
                size = p.stat().st_size
            except Exception:
                pass
        if ph or not p.exists() or min(w, h) < 480 or size < 18000:
            out.append(e)
    return out


def query_best(latin):
    key = species_key(latin)
    url = (fi.API + "/observations?taxon_name=" + quote(latin) +
           "&photos=true&quality_grade=research&order_by=votes&per_page=5"
           "&photo_license=cc0,cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa")
    data = fi.api_get(url)
    best = []
    for rank, obs in enumerate((data or {}).get("results") or []):
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
            w, h = dims(ph)
            # 优先横图、长边足够，投票排序靠前者优先
            score = (1000 - rank * 10) + (min(w, h) if w and h else 0) / 4 + (200 if w >= h else 0)
            ph["_score"] = score
            best.append(ph)
    best.sort(key=lambda p: p["_score"], reverse=True)
    return best


def process(entry, ledger, lock):
    sid = entry["id"]
    for ph in query_best(entry["latin"])[:6]:
        raw = fi.download(ph.get("medium_url") or "")
        if not raw:
            continue
        saved, err = fi.save_image(entry, raw)
        if err:
            continue
        lic = (ph.get("license_code") or "").lower()
        with lock:
            ledger[sid] = {
                "author": ph.get("attribution") or "iNaturalist contributor",
                "license": lic,
                "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                "name": entry["name"],
                "latin": entry["latin"],
                "photoId": ph.get("id"),
                "note": "本种照片（社区推荐，可合法用于非商业展示）",
            }
        return "ok", sid, {"w": saved["width"], "h": saved["height"]}
    return "fail", sid, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    fi.API_LIMITER = fi.RateLimiter(1.0)

    plan = fi.load_plan()
    ledger = fi.load_json(fi.LEDGER, {})
    lock = threading.Lock()
    targets = candidates(plan, ledger)
    if args.limit:
        targets = targets[: args.limit]
    print("待替换:", len(targets), flush=True)

    stats = {"ok": 0, "fail": 0}
    fails = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process, e, ledger, lock): e for e in targets}
        done = 0
        for fut in as_completed(futures):
            e = futures[fut]
            try:
                kind, sid, info = fut.result()
            except Exception as exc:  # noqa: BLE001
                kind, sid, info = "fail", e["id"], str(exc)
            stats[kind] += 1
            if kind == "fail":
                fails.append([sid, e["name"]])
            done += 1
            if done % 20 == 0:
                with lock:
                    fi.write_credits(ledger)
                print(f"[{done}/{len(targets)}] ok={stats['ok']} fail={stats['fail']}", flush=True)

    with lock:
        fi.write_credits(ledger)
    REPORT.write_text(json.dumps({"targets": len(targets), "stats": stats, "fails": fails},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成:", stats, flush=True)


if __name__ == "__main__":
    main()
