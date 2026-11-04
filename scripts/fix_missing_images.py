# -*- coding: utf-8 -*-
"""为抓取失败的 10 个物种补图：优先找原分类单元的大图，其次用近缘分类单元兜底。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi  # noqa: E402

FALLBACKS = {
    "insect-biting-midge": ["Culicoides imicola", "Culicoides"],
    "mollusk-subcrenata-ark": ["Anadara broughtonii", "Anadara"],
    "invertebrate-bancroft-filaria": ["Caenorhabditis elegans", "Ascaris lumbricoides"],
    "succulent-titubans": ["Echeveria elegans", "Echeveria"],
    "succulent-douglas-huth": ["Graptopetalum paraguayense", "Graptopetalum"],
    "fungus-indian-truffle": ["Tuber brumale", "Tuber aestivum"],
    "fungus-bailing-mushroom": ["Pleurotus nebrodensis", "Pleurotus eryngii"],
    "fungus-fission-yeast": ["Schizosaccharomyces pombe", "Saccharomyces cerevisiae"],
    "fungus-yarrowia": ["Yarrowia lipolytica", "Saccharomyces cerevisiae"],
    "fungus-hanseniaspora": ["Hanseniaspora uvarum", "Saccharomyces cerevisiae"],
}


def choose_largest(photos):
    def score(ph):
        w, h = fi.photo_dims(ph)
        return min(w, h) if min(w, h) else 0
    cc = [p for p in photos if p.get("license_code")]
    pool = cc if cc else photos
    return sorted(pool, key=score, reverse=True)


def taxon_by_query(q):
    params = __import__("urllib.parse", fromlist=["urlencode"]).urlencode(
        {"q": q, "per_page": 5, "locale": "zh-CN"}
    )
    data = fi.api_get(f"{fi.API}/taxa?{params}")
    return (data or {}).get("results") or []


def fetch_for(entry):
    candidates = []
    taxon = fi.find_taxon(entry)
    if taxon:
        candidates.extend(fi.taxon_photos(taxon["id"]))
    for q in FALLBACKS.get(entry["id"], []):
        for r in taxon_by_query(q)[:2]:
            candidates.extend(fi.taxon_photos(r["id"]))
            if candidates:
                break
        if candidates:
            break
    for ph in choose_largest(candidates):
        urls = fi.variant_urls(ph)
        raw = None
        for u in urls:
            raw = fi.download(u)
            if raw:
                break
        if not raw:
            continue
        saved, error = fi.save_image(entry, raw)
        if error:
            print(f"  {entry['id']}: 尝试失败 {error}")
            continue
        return saved, ph
    return None, None


def main():
    entries = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    ok = 0
    for sid in FALLBACKS:
        entry = entries.get(sid)
        if not entry:
            print("未知物种", sid)
            continue
        saved, ph = fetch_for(entry)
        if not saved:
            print(f"x {sid} 仍失败")
            continue
        ledger[sid] = {
            "author": ph.get("attribution") or "iNaturalist contributor",
            "license": ph.get("license_code") or "all rights reserved",
            "source": f"https://www.inaturalist.org/photos/{ph.get('id')}",
            "name": entry["name"],
            "latin": entry["latin"],
            "photoId": ph.get("id"),
            "note": "同属/近缘类群代表照片",
        }
        fi.write_credits(ledger)
        ok += 1
        print(f"OK {sid} -> {saved['width']}x{saved['height']} {saved['bytes'] // 1024}KB {ledger[sid]['license']}")
    print("补充完成", ok, "/", len(FALLBACKS))


if __name__ == "__main__":
    main()
