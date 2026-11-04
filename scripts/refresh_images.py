#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对少量图片质量不佳的物种换用同分类单元的另一张照片。
用法：python scripts/refresh_images.py tree-nanmu tree-jacaranda flower-babys-breath
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi  # noqa: E402


def candidate_photos(taxon_id):
    photos = fi.taxon_photos(taxon_id)
    if not photos:
        return []

    def score(ph):
        w, h = fi.photo_dims(ph)
        base = min(w, h) if min(w, h) else 300
        if w >= h:
            base += 250
        if w * h < 400 * 300:
            base -= 2000
        return base

    cc = [p for p in photos if p.get("license_code")]
    pool = cc if cc else photos
    pool = sorted(pool, key=score, reverse=True)
    return pool


def main(ids):
    entries = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    for sid in ids:
        entry = entries.get(sid)
        if not entry:
            print(f"未知物种：{sid}")
            continue
        taxon = fi.find_taxon(entry)
        if not taxon:
            print(f"未找到分类单元：{sid}")
            continue
        photos = candidate_photos(taxon["id"])
        current_photo = ledger.get(sid, {}).get("photoId")
        print(f"{sid} {entry['name']}：共 {len(photos)} 张候选（跳过当前 {current_photo}）")
        saved = False
        for idx, ph in enumerate(photos):
            if ph.get("id") == current_photo:
                continue
            urls = fi.variant_urls(ph)
            if not urls:
                continue
            raw = None
            for url in urls:
                raw = fi.download(url)
                if raw:
                    break
            if not raw:
                continue
            saved_info, error = fi.save_image(entry, raw)
            if error:
                print(f"  [{idx}] 失败：{error}")
                continue
            ledger[sid] = {
                "author": ph.get("attribution") or "iNaturalist contributor",
                "license": ph.get("license_code") or "all rights reserved",
                "source": f"https://www.inaturalist.org/photos/{ph.get('id')}",
                "name": entry["name"],
                "latin": entry["latin"],
                "photoId": ph.get("id"),
            }
            fi.write_credits(ledger)
            print(f"  [{idx}] OK {saved_info['width']}x{saved_info['height']} {saved_info['bytes'] // 1024}KB "
                  f"{ledger[sid]['license']}")
            saved = True
            break
        if not saved:
            print(f"  {sid} 未替换成功，保留原图")


if __name__ == "__main__":
    ids = sys.argv[1:]
    if not ids:
        print("请提供物种 id")
        raise SystemExit(1)
    main(ids)
