# -*- coding: utf-8 -*-
"""从图片版权记录里的原始来源重新下载更大版本，提升低分辨率图片清晰度。"""
import io
import json
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "images"
LEDGER = json.loads((ROOT / "plan" / "image-credits.json").read_text(encoding="utf-8"))


def fetch(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nature-atlas-upscale"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def process(item):
    sid, path, cur_w, cur_h, src = item
    if not src.startswith("http"):
        return ("skip", sid)
    raw = fetch(src)
    if not raw:
        return ("fail", sid)
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:
        return ("fail", sid)
    w, h = im.size
    if w <= cur_w * 1.15 and h <= cur_h * 1.15:
        return ("same", sid)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    # 统一到站点展示宽度 900（原图更宽则缩到 900；比原来大但不到 900 则保留）
    if w > 900:
        im = im.resize((900, max(1, round(h * 900 / w))), Image.LANCZOS)
    im.save(path, "WEBP", quality=88, method=6)
    return ("ok", sid, w, h, path.stat().st_size)


def main():
    targets = []
    for p in IMG.rglob("*.webp"):
        try:
            im = Image.open(p)
            w, h = im.size
        except Exception:
            continue
        if w >= 800:
            continue
        src = (LEDGER.get(p.stem) or {}).get("source", "")
        if src.startswith("http"):
            targets.append((p.stem, p, w, h, src))
    print("targets:", len(targets), flush=True)
    stats = {"ok": 0, "same": 0, "fail": 0, "skip": 0}
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(process, t) for t in targets]
        done = 0
        for fut in as_completed(futures):
            try:
                res = fut.result()
            except Exception:
                res = ("fail", "?")
            done += 1
            with lock:
                stats[res[0]] = stats.get(res[0], 0) + 1
            if res[0] == "ok":
                print("ok", res[1], f"{res[2]}x{res[3]}", res[4], flush=True)
            if done % 50 == 0:
                print(f"[{done}/{len(targets)}]", stats, flush=True)
    print("done:", stats, flush=True)


if __name__ == "__main__":
    main()
