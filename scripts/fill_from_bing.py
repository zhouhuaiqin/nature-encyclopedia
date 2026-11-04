# -*- coding: utf-8 -*-
"""用 Bing 图片搜索为已补图物种换上更美观的实景照片（记录来源；许可未核验）。"""
import hashlib
import json
import re
import sys
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent


def fetch(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            "Accept": "text/html,image/avif,image/webp,image/*,*/*;q=0.8"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def bing_urls(query):
    html = fetch("https://www.bing.com/images/search?q=" + urllib.parse.quote(query))
    if not html:
        return []
    text = html.decode("utf-8", "ignore")
    urls = re.findall(r'"murl":"(.*?)"', text) + re.findall(r"murl&quot;:&quot;(.*?)&quot;", text)
    out = []
    for u in urls:
        u = u.replace("\\u002f", "/").replace("\\/", "/").replace("&amp;", "&")
        if u.startswith("http") and u.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png", ".webp")):
            out.append(u)
    return list(dict.fromkeys(out))


def md5(b):
    return hashlib.md5(b).hexdigest()


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    targets = [e for e in plan.values() if "外部补图" in ((ledger.get(e["id"]) or {}).get("note") or "")]
    print("targets:", len(targets), flush=True)
    lock = threading.Lock()
    stats = {"ok": 0, "none": 0}

    def process(e):
        suffix = " 动物" if e.get("tab") == "animals" else " 植物"
        queries = [e["name"] + suffix + " " + e["latin"], e["name"] + " " + e["latin"], e["name"]]
        cands = []
        for q in queries:
            for u in bing_urls(q)[:5]:
                raw = fetch(u)
                if not raw or len(raw) < 12000:
                    continue
                try:
                    from PIL import Image
                    import io
                    im = Image.open(io.BytesIO(raw))
                    im.load()
                    w, h = im.size
                except Exception:
                    continue
                if min(w, h) < 500:
                    continue
                score = min(w, h) - abs((w / h) - 1.35) * 300
                cands.append((score, u, raw))
            if len(cands) >= 3:
                break
        if not cands:
            with lock:
                stats["none"] += 1
            print("none", e["id"], flush=True)
            return
        cands.sort(reverse=True)
        for score, u, raw in cands[:3]:
            saved, err = fi.save_image(e, raw)
            if err:
                continue
            with lock:
                ledger[e["id"]] = {
                    "author": "Bing 图片搜索（版权归原作者）",
                    "license": "unknown",
                    "source": u,
                    "name": e["name"], "latin": e["latin"],
                    "note": "网络图片（Bing 图片搜索，许可未核验，仅个人学习参考）",
                }
                fi.write_credits(ledger)
                stats["ok"] += 1
                print("ok", e["id"], flush=True)
            return
        with lock:
            stats["none"] += 1

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(process, e) for e in targets]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                print("ERR", exc, flush=True)
    fi.write_credits(ledger)
    print("完成:", stats, flush=True)


if __name__ == "__main__":
    main()
