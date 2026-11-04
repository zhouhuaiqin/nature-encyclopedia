# -*- coding: utf-8 -*-
"""为占位图物种准备外部导入素材：
- 从 iNaturalist 观测记录中选「本种 + 合法许可」照片；
- 下载原图到 plan/external-images/<id>.jpg；
- 生成 plan/external-images.csv（id,file,source,author,license,note）。
之后由 scripts/import_external_images.py 统一压缩/去重/入库。
"""
import csv
import hashlib
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi
import improve_photos as ip

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "plan" / "external-images"
MANIFEST = ROOT / "plan" / "external-images.csv"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    targets = [e for e in plan.values()
               if "原创占位图" in ((ledger.get(e["id"]) or {}).get("note") or "")]
    SRC.mkdir(parents=True, exist_ok=True)
    print("占位图物种:", len(targets), flush=True)

    used = set()
    for e in plan.values():
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        if p.exists():
            used.add(md5(p))

    lock = threading.Lock()
    rows = []

    def process(e):
        sid = e["id"]
        for ph in ip.query_best(e["latin"])[:10]:
            url = ph.get("medium_url") or ""
            if not url:
                continue
            raw = fi.download(url)
            if not raw or len(raw) < 8000:
                continue
            tmp = SRC / (sid + ".jpg")
            tmp.write_bytes(raw)
            h = md5(tmp)
            with lock:
                if h in used:
                    tmp.unlink(missing_ok=True)
                    continue
                used.add(h)
                rows.append({
                    "id": sid,
                    "file": "external-images/" + sid + ".jpg",
                    "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                    "author": ph.get("attribution") or "iNaturalist contributor",
                    "license": (ph.get("license_code") or "cc0").upper(),
                    "note": "iNaturalist 本种观测照片（自动匹配，备用导入）",
                })
            return "ok"
        return "none"

    stats = {"ok": 0, "none": 0}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(process, e): e for e in targets}
        done = 0
        for fut in as_completed(futures):
            try:
                kind = fut.result()
            except Exception:  # noqa: BLE001
                kind = "none"
            stats[kind] += 1
            done += 1
            if done % 10 == 0:
                print(f"[{done}/{len(targets)}] ok={stats['ok']} none={stats['none']}", flush=True)

    rows.sort(key=lambda r: r["id"])
    with MANIFEST.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "file", "source", "author", "license", "note"])
        w.writeheader()
        w.writerows(rows)
    print("清单写入:", MANIFEST, "行数:", len(rows), "| 仍无合法照片:", stats["none"])


if __name__ == "__main__":
    main()
