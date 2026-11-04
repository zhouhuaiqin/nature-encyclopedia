# -*- coding: utf-8 -*-
"""重点物种照片优选：精选、分类封面、代表性物种、占位图。
优先选择：本种学名、合法许可、野生观察（captive=false）、社区投票靠前；
再按“主体居中 + 少人手 + 分辨率”评分选图，并保证全站唯一。
"""
import hashlib
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


def score_image_bytes(raw):
    import io
    im = Image.open(io.BytesIO(raw))
    im.load()
    ow, oh = im.size
    if min(ow, oh) < 480:
        return None
    small = im.convert("RGB").resize((320, 240))
    a = np.asarray(small).astype(np.float32)
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
    score = off + (bottom * 2.2 + edge * 2.2) - min(ow, oh) / 3000.0
    return {"score": round(float(score), 3), "off": round(float(off), 3),
            "bottom": round(bottom, 3), "edge": round(edge, 3), "w": ow, "h": oh}


def large_url(ph):
    url = ph.get("url") or ""
    for v in ("square", "small", "medium"):
        if "/" + v + "." in url:
            return url.replace("/" + v + ".", "/large.")
    return url


def candidates(entry, per_page=4):
    import urllib.parse
    base = ("/observations?taxon_name=" + urllib.parse.quote(entry["latin"]) +
            "&photos=true&quality_grade=research&captive=false&order_by=votes&per_page=" + str(per_page) +
            "&photo_license=" + ",".join(sorted(LEGAL)))
    data = fi.api_get(fi.API + base)
    out = []
    for obs in (data or {}).get("results") or []:
        tax = (obs.get("taxon") or {}).get("name") or ""
        if tax and not tax.lower().startswith(entry["latin"].lower()):
            continue
        for ph in obs.get("photos") or []:
            lic = (ph.get("license_code") or "").lower()
            if lic in LEGAL:
                out.append((ph, lic, large_url(ph)))
    return out


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    meta = (ROOT / "data" / "meta.js").read_text(encoding="utf-8")
    featured = re.findall(r'"([a-z0-9-]+)"', re.search(r"window\.FEATURED = \[(.*?)\];", meta, re.S).group(1))
    cover_block = meta.split("window.CATEGORY_COVERS = {")[1].split("};")[0]
    covers = re.findall(r':\s*"([a-z0-9-]+)"', cover_block)
    by_name = {e["name"]: e["id"] for e in plan.values()}
    icons = [by_name[n] for n in ICONS if n in by_name]
    targets = list(dict.fromkeys(featured + covers + icons))
    placeholders = [e["id"] for e in plan.values()
                    if "原创占位图" in ((ledger.get(e["id"]) or {}).get("note") or "")]
    targets += [t for t in placeholders if t not in targets]
    print("重点物种:", len(targets), "其中占位图:", len(placeholders), flush=True)

    used = set()
    for e in plan.values():
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        if p.exists():
            used.add(md5_file(p))
    lock = threading.Lock()
    report = []

    def process(sid):
        e = plan[sid]
        p = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
        old_hash = md5_file(p) if p.exists() else None
        best = None
        for ph, lic, url in candidates(e):
            if not url:
                continue
            raw = fi.download(url)
            if not raw or len(raw) < 12000:
                continue
            sc = score_image_bytes(raw)
            if not sc:
                continue
            h = md5_bytes(raw)
            with lock:
                if h in used and h != old_hash:
                    continue
            if best is None or sc["score"] < best[0]["score"]:
                best = (sc, raw, ph, lic)
        if not best:
            return ("none", sid)
        sc, raw, ph, lic = best
        saved, err = fi.save_image(e, raw)
        if err:
            return ("fail", sid)
        h = md5_file(p)
        with lock:
            if h in used and h != old_hash:
                return ("dup", sid)
            if old_hash and old_hash in used:
                used.discard(old_hash)
            used.add(h)
            ledger[sid] = {
                "author": ph.get("attribution") or "iNaturalist contributor",
                "license": lic,
                "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                "name": e["name"], "latin": e["latin"], "photoId": ph.get("id"),
                "note": "代表物种优选（本种、合法许可、主体优先）",
            }
            report.append({"id": sid, "name": e["name"], "license": lic, **sc})
        return ("ok", sid)

    stats = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(process, sid): sid for sid in targets}
        done = 0
        for fut in as_completed(futures):
            try:
                kind = fut.result()[0]
            except Exception:  # noqa: BLE001
                kind = "fail"
            stats[kind] = stats.get(kind, 0) + 1
            done += 1
            if done % 10 == 0:
                fi.write_credits(ledger)
                print(f"[{done}/{len(targets)}]", stats, flush=True)
    fi.write_credits(ledger)
    (ROOT / "plan" / "key-photo-refresh-report.json").write_text(
        json.dumps({"stats": stats, "photos": report}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成:", stats, flush=True)


if __name__ == "__main__":
    main()
