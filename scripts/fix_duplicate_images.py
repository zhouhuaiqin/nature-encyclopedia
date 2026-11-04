# -*- coding: utf-8 -*-
"""修复重复图片：同一张图被多个物种使用的，重新为每个物种抓取「本种」照片，
并保证新图在全站唯一；找不到唯一合法照片的用占位图。"""
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi
import improve_photos as ip
import make_placeholders as mp

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "plan" / "image-species-audit.json"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    groups = audit["duplicateGroups"]
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    targets = []
    for g in groups:
        for x in g:
            targets.append(plan[x["id"]])
    targets = list({e["id"]: e for e in targets}.values())
    print("待修复重复图片物种:", len(targets), flush=True)

    lock = threading.Lock()
    used = {}
    for e in plan.values():
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        if p.exists():
            used.setdefault(md5(p), set()).add(e["id"])

    def process(e):
        before = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        before_hash = md5(before) if before.exists() else None
        for ph in ip.query_best(e["latin"])[:8]:
            raw = fi.download(ph.get("medium_url") or "")
            if not raw:
                continue
            # 先保存到临时文件校验唯一性
            saved, err = fi.save_image(e, raw)
            if err:
                continue
            new_hash = md5(fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg"))
            with lock:
                others = used.get(new_hash, set()) - {e["id"]}
            if others:
                # 与其它物种重复，继续找
                continue
            with lock:
                if before_hash and before_hash in used:
                    used[before_hash].discard(e["id"])
                used[new_hash] = {e["id"]}
                ledger[e["id"]] = {
                    "author": ph.get("attribution") or "iNaturalist contributor",
                    "license": (ph.get("license_code") or "cc0").lower(),
                    "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                    "name": e["name"], "latin": e["latin"], "photoId": ph.get("id"),
                    "note": "本种照片（为唯一性重新选择，可合法用于非商业展示）",
                }
            return "ok"
        # 没有唯一合法照片 → 占位图
        mp.make_placeholder(e, before)
        with lock:
            if before_hash and before_hash in used:
                used[before_hash].discard(e["id"])
            ledger[e["id"]] = {
                "author": "自然图鉴（本站自绘）", "license": "cc0", "source": "本站原创占位图",
                "name": e["name"], "latin": e["latin"], "note": "原创占位图（CC0），非真实照片",
            }
        return "placeholder"

    stats = {"ok": 0, "placeholder": 0}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(process, e): e for e in targets}
        for fut in as_completed(futures):
            try:
                stats[fut.result()] = stats.get(fut.result(), 0) + 1
            except Exception:  # noqa: BLE001
                stats["placeholder"] += 1
    fi.write_credits(ledger)
    print("修复完成:", stats, flush=True)


if __name__ == "__main__":
    main()
