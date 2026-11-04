# -*- coding: utf-8 -*-
"""重点物种照片优选 v2（先精选/封面/代表物种，先中图后大图，选中即写版权）。"""
import hashlib
import io
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
LEGAL = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
ICONS = [
    "大熊猫", "狮子", "虎", "雪豹", "小熊猫", "川金丝猴", "丹顶鹤", "朱鹮", "绿孔雀",
    "大蓝闪蝶", "鲸鲨", "非洲象", "亚洲象", "长颈鹿", "北极熊", "狼", "赤狐",
    "白头海雕", "雪鸮", "大红鹳", "树袋熊", "帝企鹅", "宽吻海豚", "虎鲸", "大鲵",
    "银杏", "向日葵", "荷花", "月季花", "樱花", "郁金香", "蝴蝶兰", "毒蝇伞",
]


def md5_bytes(data):
    return hashlib.md5(data).hexdigest()


def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def score(raw):
    im = Image.open(io.BytesIO(raw))
    im.load()
    ow, oh = im.size
    if min(ow, oh) < 400:
        return None
    a = np.asarray(im.convert("RGB").resize((320, 240))).astype(np.float32)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
    skin = ((cb >= 80) & (cb <= 125) & (cr >= 136) & (cr <= 172) & (y > 60)).astype(np.float32)
    h, w = skin.shape
    bottom = float(skin[int(h * 0.7):, :].mean())
    border = np.ones_like(skin)
    border[int(h * 0.12):int(h * 0.88), int(w * 0.12):int(w * 0.88)] = 0
    edge = float((skin * border).mean())
    gx = np.abs(np.diff(y, axis=1))[:-1, :]
    gy = np.abs(np.diff(y, axis=0))[:, :-1]
    mag = np.clip(gx + gy - (gx + gy).mean(), 0, None)
    total = mag.sum() + 1e-6
    ys, xs = np.mgrid[0:mag.shape[0], 0:mag.shape[1]]
    cx = (xs * mag).sum() / total
    cy = (ys * mag).sum() / total
    off = ((cx - (w - 1) / 2) ** 2 + (cy - (h - 1) / 2) ** 2) ** 0.5 / ((w / 2) ** 2 + (h / 2) ** 2) ** 0.5
    return {"score": round(float(off + bottom * 2.2 + edge * 2.2 - min(ow, oh) / 3000.0), 3),
            "off": round(float(off), 3), "bottom": round(bottom, 3), "w": ow, "h": oh}


def medium_url(ph):
    for v in ("square", "small", "medium"):
        if "/" + v + "." in (ph.get("url") or ""):
            return ph["url"].replace("/" + v + ".", "/medium.")
    return ph.get("url") or ""


def large_url(ph):
    for v in ("square", "small", "medium"):
        if "/" + v + "." in (ph.get("url") or ""):
            return ph["url"].replace("/" + v + ".", "/large.")
    return ph.get("url") or ""


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    meta = (ROOT / "data" / "meta.js").read_text(encoding="utf-8")
    featured = re.findall(r'"([a-z0-9-]+)"', re.search(r"window\.FEATURED = \[(.*?)\];", meta, re.S).group(1))
    cover_block = meta.split("window.CATEGORY_COVERS = {")[1].split("};")[0]
    covers = re.findall(r':\s*"([a-z0-9-]+)"', cover_block)
    by_name = {e["name"]: e["id"] for e in plan.values()}
    icons = [by_name[n] for n in ICONS if n in by_name]
    targets = list(dict.fromkeys(featured + covers + icons + ["mammal-giant-panda", "insect-blue-morpho", "aquatic-giant-water-lily"]))
    print("targets:", len(targets), flush=True)

    used = set()
    for e in plan.values():
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        if p.exists():
            used.add(md5_file(p))
    lock = threading.Lock()
    done_count = [0]

    def process(sid):
        e = plan[sid]
        import urllib.parse
        url = (fi.API + "/observations?taxon_name=" + urllib.parse.quote(e["latin"]) +
               "&photos=true&quality_grade=research&captive=false&order_by=votes&per_page=1&photo_license=" +
               ",".join(sorted(LEGAL)))
        data = fi.api_get(url)
        best = None
        for obs in ((data or {}).get("results") or [])[:1]:
            tax = (obs.get("taxon") or {}).get("name") or ""
            if tax and not tax.lower().startswith(e["latin"].lower()):
                continue
            for ph in obs.get("photos") or []:
                lic = (ph.get("license_code") or "").lower()
                if lic not in LEGAL:
                    continue
                raw = fi.download(medium_url(ph))
                if not raw:
                    continue
                sc = score(raw)
                if not sc:
                    raw = fi.download(large_url(ph))
                    if not raw:
                        continue
                    sc = score(raw)
                    if not sc:
                        continue
                if best is None or sc["score"] < best[0]["score"]:
                    best = (sc, raw, ph, lic)
        if not best:
            return "none"
        sc, raw, ph, lic = best
        saved, err = fi.save_image(e, raw)
        if err:
            return "fail"
        p = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
        h = md5_file(p)
        with lock:
            others = used - {h}
            if h in used:
                # 同图已被其它物种使用
                return "dup"
            used.add(h)
            ledger[sid] = {
                "author": ph.get("attribution") or "iNaturalist contributor",
                "license": lic,
                "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                "name": e["name"], "latin": e["latin"], "photoId": ph.get("id"),
                "note": "代表物种优选（本种、合法许可、主体优先）",
            }
            fi.write_credits(ledger)
            done_count[0] += 1
            print(f"[{done_count[0]}/{len(targets)}] {sid} {sc['score']}", flush=True)
        return "ok"

    stats = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(process, sid): sid for sid in targets}
        for fut in as_completed(futures):
            try:
                kind = fut.result()
            except Exception as exc:  # noqa: BLE001
                print("ERR", exc, flush=True)
                kind = "fail"
            stats[kind] = stats.get(kind, 0) + 1
    print("done:", stats, flush=True)


if __name__ == "__main__":
    main()
