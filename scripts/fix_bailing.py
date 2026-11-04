# -*- coding: utf-8 -*-
"""给白灵菇补一张可用照片：优先从该分类单元的观测记录里找大图。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi  # noqa: E402


def main():
    entry = {e["id"]: e for e in fi.load_plan()}["fungus-bailing-mushroom"]
    taxon = fi.find_taxon(entry)
    print("taxon", taxon and (taxon.get("name"), taxon.get("id")))
    photos = []
    if taxon:
        data = fi.api_get(
            fi.API + "/observations?taxon_id=" + str(taxon["id"]) + "&photos=true&per_page=30&order_by=votes"
        )
        obs = (data or {}).get("results") or []
        print("observations", len(obs))
        for o in obs:
            for ph in o.get("photos") or []:
                url = ph.get("url", "")
                photos.append({
                    "id": ph.get("id"),
                    "medium_url": url.replace("/square.", "/medium.") if "/square." in url else url,
                    "license_code": ph.get("license_code"),
                    "attribution": ph.get("attribution"),
                    "original_dimensions": ph.get("original_dimensions"),
                })
    print("candidates", len(photos))
    photos.sort(key=lambda p: min(fi.photo_dims(p)) if min(fi.photo_dims(p)) else 0, reverse=True)
    for ph in photos[:10]:
        raw = None
        for url in fi.variant_urls(ph):
            raw = fi.download(url)
            if raw:
                break
        if not raw:
            continue
        saved, err = fi.save_image(entry, raw)
        print("try", fi.photo_dims(ph), "error=", err, "saved=", saved)
        if not err:
            ledger = fi.load_json(fi.LEDGER, {})
            ledger[entry["id"]] = {
                "author": ph.get("attribution") or "iNaturalist contributor",
                "license": ph.get("license_code") or "all rights reserved",
                "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                "name": entry["name"],
                "latin": entry["latin"],
                "photoId": ph.get("id"),
            }
            fi.write_credits(ledger)
            print("saved 白灵菇")
            return
    print("failed")


if __name__ == "__main__":
    main()
