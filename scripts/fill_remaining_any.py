# -*- coding: utf-8 -*-
"""补齐剩余占位图：不筛选许可，尽量找到真实照片；记录作者/来源与许可状态。
注意：这些图片未核验授权，仅适合个人学习参考，不应公开商用。"""
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
KNOWN = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}


def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def variant(ph, v):
    url = ph.get("url") or ""
    for cur in ("square", "small", "medium", "large"):
        if "/" + cur + "." in url:
            return url.replace("/" + cur + ".", "/" + v + ".")
    return url


def photo_rows(obs_list, latin):
    out = []
    for obs in obs_list or []:
        tax = (obs.get("taxon") or {}).get("name") or ""
        if tax and not tax.lower().startswith(latin.lower()):
            continue
        for ph in obs.get("photos") or []:
            out.append(ph)
    return out


def find_photos(latin):
    import urllib.parse
    q = urllib.parse.quote(latin)
    data = fi.api_get(fi.API + "/observations?taxon_name=" + q +
                      "&photos=true&quality_grade=research&order_by=votes&per_page=5")
    rows = photo_rows((data or {}).get("results"), latin)
    if rows:
        return rows
    # 放宽到任意质量
    data = fi.api_get(fi.API + "/observations?taxon_name=" + q +
                      "&photos=true&order_by=votes&per_page=5")
    rows = photo_rows((data or {}).get("results"), latin)
    if rows:
        return rows
    # 通过 taxon 搜索 + taxon_photos
    taxa = fi.api_get(fi.API + "/taxa?q=" + q + "&per_page=5")
    for t in (taxa or {}).get("results") or []:
        name = (t.get("name") or "").lower()
        if not name or not (name.startswith(latin.lower()) or latin.lower().startswith(name)):
            continue
        detail = fi.api_get(fi.API + "/taxa/" + str(t.get("id")))
        if detail:
            phs = (detail.get("taxon_photos") or [])
            rows = [p.get("photo") or p for p in phs if (p.get("photo") or p)]
            if rows:
                return rows
        data = fi.api_get(fi.API + "/observations?taxon_id=" + str(t.get("id")) +
                          "&photos=true&order_by=votes&per_page=5")
        rows = photo_rows((data or {}).get("results"), latin)
        if rows:
            return rows
    return []


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    targets = [e for e in plan.values()
               if "原创占位图" in ((ledger.get(e["id"]) or {}).get("note") or "")]
    print("待补齐:", len(targets), flush=True)
    lock = threading.Lock()
    stats = {"filled": 0, "none": 0}

    def process(e):
        photos = find_photos(e["latin"])
        for ph in photos[:4]:
            for v in ("large", "medium", "original"):
                url = variant(ph, v)
                if not url:
                    continue
                raw = fi.download(url)
                if not raw:
                    continue
                saved, err = fi.save_image(e, raw)
                if err:
                    continue
                lic = (ph.get("license_code") or "").lower()
                with lock:
                    ledger[e["id"]] = {
                        "author": ph.get("attribution") or "iNaturalist contributor",
                        "license": lic or "arr",
                        "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                        "name": e["name"], "latin": e["latin"], "photoId": ph.get("id"),
                        "note": "外部补图（未核验许可，仅个人学习参考）",
                    }
                    fi.write_credits(ledger)
                    stats["filled"] += 1
                    print("[%d/%d] ok %s %s" % (stats["filled"], len(targets), e["id"], lic or "arr"), flush=True)
                return "ok"
        with lock:
            stats["none"] += 1
            print("[none] " + e["id"], flush=True)
        return "none"

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(process, e): e for e in targets}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                print("ERR", exc, flush=True)
    fi.write_credits(ledger)
    print("完成:", stats, flush=True)


if __name__ == "__main__":
    main()
