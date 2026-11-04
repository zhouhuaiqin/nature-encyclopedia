# -*- coding: utf-8 -*-
"""补齐剩余占位图 v2：iNaturalist 任意许可 → GBIF 图像。"""
import json
import sys
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent


def get_json(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nature-encyclopedia-fill"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def fetch(url, timeout=40):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nature-encyclopedia-fill"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def photo_rows(obs_list, latin):
    out = []
    for obs in obs_list or []:
        tax = (obs.get("taxon") or {}).get("name") or ""
        if tax and not tax.lower().startswith(latin.lower()):
            continue
        for ph in obs.get("photos") or []:
            out.append(ph)
    return out


def variant(ph, v):
    url = ph.get("url") or ""
    for cur in ("square", "small", "medium", "large"):
        if "/" + cur + "." in url:
            return url.replace("/" + cur + ".", "/" + v + ".")
    return url


def inat_photos(latin):
    q = urllib.parse.quote(latin)
    for extra in ("&quality_grade=research", ""):
        data = get_json(fi.API + "/observations?taxon_name=" + q +
                        "&photos=true&order_by=votes&per_page=5" + extra)
        rows = photo_rows((data or {}).get("results"), latin)
        if rows:
            return rows
        taxa = get_json(fi.API + "/taxa?q=" + q + "&per_page=5")
        for t in (taxa or {}).get("results") or []:
            name = (t.get("name") or "").lower()
            matched = (t.get("matched_term") or "").lower()
            if latin.lower() not in (name, matched) and not name.startswith(latin.lower()):
                continue
            detail = get_json(fi.API + "/taxa/" + str(t.get("id")))
            if detail:
                phs = detail.get("taxon_photos") or []
                rows = [p.get("photo") or p for p in phs if (p.get("photo") or p)]
                if rows:
                    return rows
            data = get_json(fi.API + "/observations?taxon_id=" + str(t.get("id")) +
                            "&photos=true&order_by=votes&per_page=5")
            rows = photo_rows((data or {}).get("results"), latin)
            if rows:
                return rows
    return []


def gbif_photos(latin):
    match = get_json("https://api.gbif.org/v1/species/match?name=" + urllib.parse.quote(latin))
    if not match or not match.get("usageKey"):
        return []
    key = match["usageKey"]
    data = get_json("https://api.gbif.org/v1/occurrence/search?taxonKey=" + str(key) +
                    "&mediaType=StillImage&limit=8")
    out = []
    for occ in (data or {}).get("results") or []:
        for m in occ.get("media") or []:
            if m.get("type") in (None, "StillImage") and m.get("identifier"):
                out.append(m)
    return out


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    targets = [e for e in plan.values()
               if "原创占位图" in ((ledger.get(e["id"]) or {}).get("note") or "")]
    print("待补齐:", len(targets), flush=True)
    lock = threading.Lock()
    stats = {"filled": 0, "none": 0}

    def process(e):
        # iNaturalist
        for ph in inat_photos(e["latin"])[:4]:
            for v in ("large", "medium", "original"):
                raw = fetch(variant(ph, v))
                if not raw:
                    continue
                saved, err = fi.save_image(e, raw)
                if err:
                    continue
                with lock:
                    ledger[e["id"]] = {
                        "author": ph.get("attribution") or "iNaturalist contributor",
                        "license": (ph.get("license_code") or "").lower() or "arr",
                        "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                        "name": e["name"], "latin": e["latin"], "photoId": ph.get("id"),
                        "note": "外部补图（未核验许可，仅个人学习参考）",
                    }
                    fi.write_credits(ledger)
                    stats["filled"] += 1
                    print("ok(inat) %s [%d]" % (e["id"], stats["filled"]), flush=True)
                return
        # GBIF
        for m in gbif_photos(e["latin"])[:4]:
            raw = fetch(m.get("identifier"))
            if not raw:
                continue
            saved, err = fi.save_image(e, raw)
            if err:
                continue
            with lock:
                ledger[e["id"]] = {
                    "author": m.get("rightsHolder") or m.get("creator") or "GBIF 数据提供者",
                    "license": (m.get("license") or "unknown").lower(),
                    "source": m.get("identifier"),
                    "name": e["name"], "latin": e["latin"],
                    "note": "外部补图（GBIF，未核验许可，仅个人学习参考）",
                }
                fi.write_credits(ledger)
                stats["filled"] += 1
                print("ok(gbif) %s [%d]" % (e["id"], stats["filled"]), flush=True)
            return
        with lock:
            stats["none"] += 1
            print("none " + e["id"], flush=True)

    with ThreadPoolExecutor(max_workers=6) as pool:
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
