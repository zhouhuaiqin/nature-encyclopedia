# -*- coding: utf-8 -*-
"""把 assets/images 下的 JPG 批量转为 WebP（宽 ≤900，质量 80），先保留原图。"""
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "images"


def convert(p):
    src = Path(p)
    dst = src.with_suffix(".webp")
    try:
        im = Image.open(src)
        im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        w, h = im.size
        if w > 900:
            im = im.resize((900, max(1, round(h * 900 / w))), Image.LANCZOS)
        im.save(dst, "WEBP", quality=80, method=6)
        return (str(src), src.stat().st_size, dst.stat().st_size)
    except Exception as exc:  # noqa: BLE001
        return (str(src), -1, str(exc))


def main():
    files = sorted(IMG.rglob("*.jpg"))
    print("jpg files:", len(files), flush=True)
    old = new = 0
    done = 0
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(convert, p) for p in files]
        for fut in as_completed(futures):
            src, a, b = fut.result()
            done += 1
            if a >= 0 and isinstance(b, int):
                old += a
                new += b
            else:
                print("FAIL", src, b, flush=True)
            if done % 200 == 0:
                print(f"[{done}/{len(files)}] {old/1048576:.1f}MB -> {new/1048576:.1f}MB", flush=True)
    print(f"done: {old/1048576:.1f}MB -> {new/1048576:.1f}MB", flush=True)


if __name__ == "__main__":
    main()
