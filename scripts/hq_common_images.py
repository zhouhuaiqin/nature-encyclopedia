# -*- coding: utf-8 -*-
"""常见类群低清图回源：从 iNaturalist 原图重新导出 900px WebP（最多 300 张）。"""
import io
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LEDGER = json.loads((ROOT / "plan" / "image-credits.json").read_text(encoding="utf-8"))
CATS = {"mammals", "birds", "reptiles", "amphibians", "fish", "insects",
        "flowers", "trees", "crops", "succulents", "cacti"}
LIMIT = 300


def fetch(url, timeout=40):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nature-atlas-hq"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def main():
    import re
    # 从数据文件里提取 category
    cat_of = {}
    for d in ["data/animals", "data/plants"]:
        for f in Path(ROOT / d).glob("*.js"):
            text = f.read_text(encoding="utf-8")
            for m in re.finditer(r'id:\s*"([^"]+)".*?category:\s*"([^"]+)"', text, re.S):
                cat_of[m.group(1)] = m.group(2)
    targets = []
    for p in (ROOT / "assets" / "images").rglob("*.webp"):
        try:
            im = Image.open(p)
            w, h = im.size
        except Exception:
            continue
        if w >= 800:
            continue
        sid = p.stem
        if cat_of.get(sid) not in CATS:
            continue
        c = LEDGER.get(sid) or {}
        if not c.get("photoId"):
            continue
        targets.append((w, sid, p, c["photoId"]))
    targets.sort(key=lambda x: x[0])
    targets = targets[:LIMIT]
    print("targets:", len(targets), flush=True)
    stats = {"ok": 0, "fail": 0, "skip": 0}

    def one(t):
        w0, sid, p, pid = t
        raw = fetch("https://inaturalist-open-data.s3.amazonaws.com/photos/" + str(pid) + "/original.jpg")
        if not raw:
            return ("fail", sid)
        try:
            im = Image.open(io.BytesIO(raw))
            im.load()
        except Exception:
            return ("fail", sid)
        w, h = im.size
        if w <= w0 * 1.1:
            return ("skip", sid)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        if w > 900:
            im = im.resize((900, max(1, round(h * 900 / w))), Image.LANCZOS)
        im.save(p, "WEBP", quality=92, method=6)
        return ("ok", sid, w0, im.width, p.stat().st_size)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(one, t) for t in targets]
        done = 0
        for fut in as_completed(futures):
            try:
                res = fut.result()
            except Exception:
                res = ("fail", "?")
            done += 1
            stats[res[0]] = stats.get(res[0], 0) + 1
            if res[0] == "ok":
                print("ok", res[1], res[2], "->", res[3], flush=True)
            if done % 50 == 0:
                print(f"[{done}/{len(targets)}]", stats, flush=True)
    print("done:", stats, flush=True)


if __name__ == "__main__":
    main()
