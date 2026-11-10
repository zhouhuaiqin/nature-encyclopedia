# -*- coding: utf-8 -*-
"""为移动端生成 420px 缩略 WebP（卡片/封面/星图用），详情页仍用 900px 原图。"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "images"
DST = ROOT / "assets" / "thumbs"


def one(p):
    src = Path(p)
    rel = src.relative_to(SRC)
    dst = DST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        im = Image.open(src)
        im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        w, h = im.size
        if w > 600:
            im = im.resize((600, max(1, round(h * 600 / w))), Image.LANCZOS)
        im.save(dst, "WEBP", quality=78, method=4)
        return (True, src.stat().st_size, dst.stat().st_size)
    except Exception as exc:  # noqa: BLE001
        return (False, str(src), str(exc))


def main():
    files = sorted(SRC.rglob("*.webp"))
    print("images:", len(files), flush=True)
    total = 0
    done = 0
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(one, p) for p in files]
        for fut in as_completed(futures):
            ok, _a, b = fut.result()
            done += 1
            if ok:
                total += b
            else:
                print("FAIL", _a, b, flush=True)
            if done % 300 == 0:
                print(f"[{done}/{len(files)}] thumbs {total/1048576:.1f} MB", flush=True)
    print(f"done: {len(files)} thumbs, {total/1048576:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
