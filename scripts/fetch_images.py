#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自然图鉴 · 物种图片抓取（iNaturalist 公开 API）

两阶段设计（S3 单连接较慢，用并发下载解决）：
  phase resolve  —— 逐个物种解析 iNaturalist 分类单元与代表照片，写入 plan/image-tasks.json
  phase download —— 多线程并发下载、缩放、压缩、登记版权

用法（项目根目录执行）：
  python scripts/fetch_images.py --phase all --limit 8
  python scripts/fetch_images.py --phase resolve
  python scripts/fetch_images.py --phase download --download-workers 16
  python scripts/fetch_images.py --retry-failed
  python scripts/fetch_images.py                 # 全量补齐（已存在的跳过）

输出：
  assets/images/{animals,plants}/<id>.jpg
  js/image-credits.js
  plan/image-tasks.json      （解析结果缓存）
  plan/image-credits.json    （版权账本，断点续跑）
  plan/image-report.json
"""

import argparse
import concurrent.futures
import io
import json
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("需要 Pillow，请使用项目自带的 Python 运行时", file=sys.stderr)
    raise SystemExit(1)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

socket.setdefaulttimeout(40)

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "assets" / "images"
CREDITS_JS = ROOT / "js" / "image-credits.js"
LEDGER = ROOT / "plan" / "image-credits.json"
TASKS = ROOT / "plan" / "image-tasks.json"
REPORT = ROOT / "plan" / "image-report.json"
API = "https://api.inaturalist.org/v1"
UA = "NatureEncyclopedia/1.0 (personal educational project; contact: local)"
API_INTERVAL = 1.0
MAX_WIDTH = 900
JPEG_QUALITY = 82
MIN_BYTES = 6000

PRINT_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()


def log(msg: str) -> None:
    with PRINT_LOCK:
        print(msg, flush=True)


class RateLimiter:
    def __init__(self, interval: float):
        self.interval = interval
        self.lock = threading.Lock()
        self.next_time = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.time()
            if now < self.next_time:
                time.sleep(self.next_time - now)
                now = time.time()
            self.next_time = max(now, self.next_time) + self.interval


API_LIMITER = RateLimiter(API_INTERVAL)


def api_get(url: str, tries: int = 3):
    last = None
    for attempt in range(tries):
        API_LIMITER.wait()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:  # noqa: PERF203
            last = exc
            if exc.code == 429:
                wait = 12 * (attempt + 1)
                log(f"    ! 429 限速，等待 {wait}s")
                time.sleep(wait)
            else:
                time.sleep(1.5 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    log(f"    x API 放弃: {url} ({last})")
    return None


def download(url: str, tries: int = 2):
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=50) as resp:
                raw = resp.read()
            if len(raw) < 3000:
                raise ValueError(f"文件过小 {len(raw)} bytes")
            return raw
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.0 * (attempt + 1))
    return None


def load_plan():
    entries = []
    seen = set()
    plan_files = sorted((ROOT / "plan").glob("species*.json"))
    for path in plan_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        tab = data.get("tab")
        if tab not in ("animals", "plants"):
            continue
        for row in data.get("species") or []:
            if not row or len(row) < 4 or row[0] in seen:
                continue
            seen.add(row[0])
            entries.append({
                "id": row[0],
                "name": row[1],
                "latin": row[2],
                "category": row[3],
                "tab": tab,
            })
    return entries


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return default
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def photo_dims(ph: dict):
    od = ph.get("original_dimensions") or {}
    w = od.get("width") or ph.get("width") or 0
    h = od.get("height") or ph.get("height") or 0
    return int(w), int(h)


def _search_results(query: str, ranked: bool = True):
    params = {"q": query, "per_page": 10, "locale": "zh-CN"}
    if ranked:
        params["rank"] = "species"
    data = api_get(f"{API}/taxa?{urllib.parse.urlencode(params)}")
    return (data.get("results") or []) if data else []


def find_taxon(entry: dict):
    """先精确学名，再中文名；兼容 iNaturalist 的学名异名（synonym）与属级兜底。"""
    latin = entry["latin"].strip()
    latin_lower = latin.lower()
    genus = latin_lower.split()[0]

    for ranked in (True, False):
        for qi, q in enumerate((latin, entry["name"])):
            results = _search_results(q, ranked=ranked)
            if not results:
                continue
            for r in results:
                if (r.get("name") or "").strip().lower() == latin_lower:
                    return r
            # 异名 / 杂交种 / 亚种等：查询只返回一个结果时直接接受
            if len(results) == 1:
                return results[0]
            for r in results:
                name = (r.get("name") or "").lower()
                if name.startswith(genus + " ") and r.get("rank") == "species":
                    return r
            if qi == 0 and ranked:
                for r in results:
                    if r.get("rank") == "species":
                        return r

    # 属名兜底：取同属的某个物种照片（最后手段，尽量少用）
    results = _search_results(genus.split()[0], ranked=True)
    for r in results:
        name = (r.get("name") or "").lower()
        if r.get("rank") == "species" and name.startswith(genus + " "):
            return r
    return None


def taxon_photos(taxon_id: int):
    data = api_get(f"{API}/taxa/{taxon_id}?locale=zh-CN")
    if not data or not data.get("results"):
        return []
    taxon = data["results"][0]
    photos = []
    for tp in taxon.get("taxon_photos") or []:
        ph = tp.get("photo") or {}
        if ph.get("medium_url"):
            photos.append(ph)
    dp = taxon.get("default_photo")
    if dp and dp.get("medium_url"):
        photos.append(dp)
    return photos


def choose_photo(photos):
    if not photos:
        return None

    def score(ph):
        w, h = photo_dims(ph)
        base = min(w, h) if min(w, h) else 300
        if w >= h:
            base += 250
        if w * h < 400 * 300:
            base -= 2000
        return base

    cc = [p for p in photos if p.get("license_code")]
    pool = cc if cc else photos
    pool.sort(key=score, reverse=True)
    return pool[0]


def variant_urls(ph: dict):
    medium = ph.get("medium_url") or ""
    if not medium:
        return []
    urls = []
    if "/medium." in medium:
        urls.append(re.sub(r"/medium\.(jpe?g)$", r"/large.\1", medium, flags=re.I))
    urls.append(medium)
    return urls


def photos_from_taxon(taxon):
    dp = taxon.get("default_photo") or {}
    w, h = photo_dims(dp)
    if dp.get("medium_url") and dp.get("license_code") and min(w, h) >= 500:
        return dp
    return choose_photo(taxon_photos(taxon["id"]))


def resolve_one(entry: dict):
    """解析 → {"urls": [...], "credit": {...}}"""
    taxon = find_taxon(entry)
    ph = photos_from_taxon(taxon) if taxon else None
    if not ph:
        # 最后兜底：同属其它有照片的物种（只用于极冷门物种）
        genus = entry["latin"].split()[0].lower()
        for r in _search_results(genus, ranked=True):
            name = (r.get("name") or "").lower()
            if not name.startswith(genus + " "):
                continue
            ph = photos_from_taxon(r)
            if ph:
                break
    if not ph:
        return {"id": entry["id"], "error": "iNaturalist 未找到有照片的对应分类单元"}
    urls = variant_urls(ph)
    if not urls:
        return {"id": entry["id"], "error": "照片地址为空"}
    return {
        "id": entry["id"],
        "urls": urls,
        "credit": {
            "author": ph.get("attribution") or "iNaturalist contributor",
            "license": ph.get("license_code") or "all rights reserved",
            "source": f"https://www.inaturalist.org/photos/{ph.get('id')}",
            "name": entry["name"],
            "latin": entry["latin"],
            "photoId": ph.get("id"),
        },
    }


def save_image(entry: dict, raw: bytes):
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:  # noqa: BLE001
        return None, f"图片解码失败 {exc}"
    w, h = img.size
    if w < 400:
        return None, f"分辨率过低 {w}x{h}"
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if w > MAX_WIDTH:
        nh = max(1, round(h * MAX_WIDTH / w))
        img = img.resize((MAX_WIDTH, nh), Image.LANCZOS)
    out = IMG_DIR / entry["tab"] / f"{entry['id']}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    try:
        check = Image.open(out)
        check.load()
        fw, fh = check.size
    except Exception as exc:  # noqa: BLE001
        return None, f"保存后校验失败 {exc}"
    size = out.stat().st_size
    if size < MIN_BYTES:
        return None, f"压缩后过小 {size} bytes"
    return {"width": fw, "height": fh, "bytes": size, "path": str(out.relative_to(ROOT))}, None


def download_one(entry: dict, task: dict):
    raw = None
    for url in task["urls"]:
        raw = download(url)
        if raw:
            break
    if not raw:
        return {"id": entry["id"], "name": entry["name"], "error": "照片下载失败"}
    saved, error = save_image(entry, raw)
    if error:
        return {"id": entry["id"], "name": entry["name"], "error": error}
    return {"id": entry["id"], "name": entry["name"], **saved, "credit": task["credit"]}


def write_placeholders() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    animal = """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <rect width="800" height="600" fill="#f2efe6"/><circle cx="400" cy="300" r="150" fill="#e5e0d2"/>
  <path d="M330 330 q0-90 70-90 q70 0 70 90 q0 40-30 45 l0 25 q-40 20-80 0 l0-25 q-30-5-30-45z" fill="#8ba888"/>
  <circle cx="360" cy="300" r="10" fill="#f2efe6"/><circle cx="400" cy="296" r="10" fill="#f2efe6"/>
  <path d="M385 335 q15 12 30 0" stroke="#f2efe6" stroke-width="6" fill="none" stroke-linecap="round"/>
  <text x="400" y="520" text-anchor="middle" font-family="serif" font-size="30" fill="#7a8a76">图片整理中 · 动物</text>
</svg>
"""
    plant = """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <rect width="800" height="600" fill="#f2efe6"/><circle cx="400" cy="300" r="150" fill="#e5e0d2"/>
  <path d="M400 390 v-150" stroke="#7d9a78" stroke-width="10" stroke-linecap="round"/>
  <path d="M400 300 q-90-20-95-110 q80 10 95 110z" fill="#8ba888"/>
  <path d="M400 330 q90-20 95-110 q-80 10-95 110z" fill="#9db89a"/>
  <path d="M400 250 q-60-35-50-105 q60 25 50 105z" fill="#7d9a78"/>
  <text x="400" y="520" text-anchor="middle" font-family="serif" font-size="30" fill="#7a8a76">图片整理中 · 植物</text>
</svg>
"""
    (IMG_DIR / "placeholder-animal.svg").write_text(animal, encoding="utf-8")
    (IMG_DIR / "placeholder-plant.svg").write_text(plant, encoding="utf-8")


def write_credits(ledger: dict) -> None:
    CREDITS_JS.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "/* 图片来源与许可：iNaturalist 公开 API（https://www.inaturalist.org）",
        " * 由 scripts/fetch_images.py 自动生成，请勿手工修改。",
        " * 各照片版权归原作者所有；站点已尽可能选用 CC 许可照片并注明出处。 */",
        "window.IMAGE_CREDITS = {",
    ]
    for key in sorted(ledger.keys()):
        rec = ledger[key]
        value = {
            "author": rec.get("author", ""),
            "license": rec.get("license", ""),
            "source": rec.get("source", ""),
        }
        lines.append(f"  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},")
    lines.append("};")
    CREDITS_JS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    save_json(LEDGER, ledger)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["all", "resolve", "download"], default="all")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", type=str, default="")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--workers", type=int, default=6, help="解析阶段并发（API 受限）")
    parser.add_argument("--download-workers", type=int, default=16, help="下载阶段并发")
    args = parser.parse_args()

    entries = load_plan()
    ledger = load_json(LEDGER, {})
    tasks = load_json(TASKS, {})

    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        entries = [e for e in entries if e["id"] in wanted]
    if args.retry_failed and REPORT.exists():
        try:
            failed = {x["id"] for x in load_json(REPORT, {}).get("failed", [])}
            entries = [e for e in entries if e["id"] in failed]
        except Exception:  # noqa: BLE001
            pass
    if args.limit:
        entries = entries[: args.limit]

    write_placeholders()
    started = time.time()
    failed = []

    def image_ok(entry):
        out = IMG_DIR / entry["tab"] / f"{entry['id']}.jpg"
        return out.exists() and out.stat().st_size >= MIN_BYTES

    # ---------- 解析阶段 ----------
    if args.phase in ("all", "resolve"):
        need = [
            e
            for e in entries
            if args.force or not (image_ok(e) and e["id"] in ledger)
        ]
        log(f"解析阶段：{len(need)} 个物种待解析（共 {len(entries)}）")
        resolved = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {pool.submit(resolve_one, e): e for e in need}
            for fut in concurrent.futures.as_completed(futures):
                entry = futures[fut]
                try:
                    result = fut.result()
                except Exception as exc:  # noqa: BLE001
                    result = {"id": entry["id"], "error": f"未捕获异常 {exc}"}
                if result.get("error"):
                    failed.append({"id": entry["id"], "name": entry["name"], "latin": entry["latin"],
                                   "status": "resolve", "reason": result["error"]})
                    log(f"  x 解析失败 {entry['id']} {entry['name']}：{result['error']}")
                else:
                    with STATE_LOCK:
                        tasks[entry["id"]] = {"urls": result["urls"], "credit": result["credit"]}
                        resolved += 1
                    log(f"  · 解析 {entry['id']} {entry['name']}")
                if resolved and resolved % 30 == 0:
                    save_json(TASKS, tasks)
        save_json(TASKS, tasks)
        log(f"解析完成：{resolved} 个，失败 {len(failed)} 个")

    # ---------- 下载阶段 ----------
    downloaded = skipped = 0
    download_entries = []
    for entry in entries:
        if entry["id"] in {x["id"] for x in failed if x.get("status") == "resolve"}:
            continue
        if image_ok(entry) and not args.force:
            if entry["id"] in ledger:
                skipped += 1
                continue
        if entry["id"] not in tasks:
            failed.append({"id": entry["id"], "name": entry["name"], "latin": entry["latin"],
                           "status": "download", "reason": "缺少解析结果"})
            continue
        download_entries.append(entry)

    if args.phase in ("all", "download") and download_entries:
        log(f"下载阶段：{len(download_entries)} 个物种待下载，并发 {args.download_workers}")
        done = 0
        total = len(download_entries)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.download_workers)) as pool:
            futures = {pool.submit(download_one, e, tasks[e["id"]]): e for e in download_entries}
            for fut in concurrent.futures.as_completed(futures):
                entry = futures[fut]
                done += 1
                try:
                    result = fut.result()
                except Exception as exc:  # noqa: BLE001
                    result = {"id": entry["id"], "name": entry["name"], "error": f"未捕获异常 {exc}"}
                if result.get("error"):
                    failed.append({"id": entry["id"], "name": entry["name"], "latin": entry["latin"],
                                   "status": "download", "reason": result["error"]})
                    log(f"[{done}/{total}] x {entry['id']} {entry['name']}：{result['error']}")
                else:
                    downloaded += 1
                    with STATE_LOCK:
                        ledger[entry["id"]] = result["credit"]
                    log(f"[{done}/{total}] OK {entry['id']} {entry['name']} "
                        f"{result['width']}x{result['height']} {result['bytes'] // 1024}KB "
                        f"{result['credit']['license']}")
                if downloaded and downloaded % 20 == 0:
                    write_credits(ledger)
        write_credits(ledger)

    write_credits(ledger)
    elapsed = round(time.time() - started, 1)
    prev_reasons = {}
    if REPORT.exists():
        for x in load_json(REPORT, {}).get("failed", []):
            prev_reasons[x.get("id")] = x
    for item in failed:
        prev_reasons[item["id"]] = item
    all_entries = load_plan()
    merged = []
    for e in all_entries:
        if image_ok(e) and e["id"] in ledger:
            continue
        prev = prev_reasons.get(e["id"], {})
        merged.append({
            "id": e["id"],
            "name": e["name"],
            "latin": e["latin"],
            "status": prev.get("status", "unresolved"),
            "reason": prev.get("reason", "未完成"),
        })
    report = {
        "total": len(all_entries),
        "downloaded": downloaded,
        "skipped": skipped,
        "failedCount": len(merged),
        "elapsedSec": elapsed,
        "failed": merged,
    }
    save_json(REPORT, report)
    log("")
    log(f"完成：新下载 {downloaded}，跳过 {skipped}，失败/未完成 {len(merged)}，耗时 {elapsed}s")
    for item in merged[:30]:
        log(f"  - {item['id']} / {item.get('name','')}：{item.get('reason')}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
