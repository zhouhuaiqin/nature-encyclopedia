# -*- coding: utf-8 -*-
"""把 72 个外部补图统一回退为 iNaturalist / GBIF 的物种图（避免 Bing 无关图）。"""
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
        req = urllib.request.Request(url, headers={"User-Agent": "ne-fix"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def fetch(url, timeout=45):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-fix"})
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
    data = get_json("https://api.gbif.org/v1/occurrence/search?taxonKey=" + str(match["usageKey"]) +
                    "&mediaType=StillImage&limit=8")
    out = []
    for occ in (data or {}).get("results") or []:
        for m in occ.get("media") or []:
            if m.get("identifier"):
                out.append(m)
    return out


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    targets = [e for e in plan.values()
               if "网络图片" in ((ledger.get(e["id"]) or {}).get("note") or "")]
    print("targets:", len(targets), flush=True)
    lock = threading.Lock()
    stats = {"inat": 0, "gbif": 0, "none": 0}

    def process(e):
        for ph in inat_photos(e["latin"])[:3]:
            for v in ("large", "medium"):
                raw = fetch(variant(ph, v))
                if not raw:
                    continue
                saved, err = fi.save_image(e, raw)
                if not err:
                    with lock:
                        ledger[e["id"]] = {"author": ph.get("attribution") or "iNaturalist contributor",
                                           "license": (ph.get("license_code") or "").lower() or "arr",
                                           "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                                           "name": e["name"], "latin": e["latin"],
                                           "note": "外部补图（iNaturalist，未核验许可，仅个人学习参考）"}
                        fi.write_credits(ledger); stats["inat"] += 1
                    print("inat", e["id"], flush=True)
                    return
        for m in gbif_photos(e["latin"])[:3]:
            raw = fetch(m.get("identifier"))
            if not raw:
                continue
            saved, err = fi.save_image(e, raw)
            if not err:
                with lock:
                    ledger[e["id"]] = {"author": m.get("rightsHolder") or "GBIF 数据提供者",
                                       "license": (m.get("license") or "unknown").lower(),
                                       "source": m.get("identifier"), "name": e["name"], "latin": e["latin"],
                                       "note": "外部补图（GBIF，未核验许可，仅个人学习参考）"}
                    fi.write_credits(ledger); stats["gbif"] += 1
                print("gbif", e["id"], flush=True)
                return
        with lock:
            stats["none"] += 1
        print("none", e["id"], flush=True)

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(process, e) for e in targets]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                print("ERR", exc, flush=True)
    fi.write_credits(ledger)
    print("完成:", stats, flush=True)


if __name__ == "__main__":
    main()
