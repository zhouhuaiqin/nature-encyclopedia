# -*- coding: utf-8 -*-
"""用 Bing 拉丁学名检索替换四种动物的图片（相关性过滤）。"""
import html as htmlmod
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
IDS = ["mammal-jaguar", "mammal-puma", "mammal-kiang", "mammal-sperm-whale"]


def fetch(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def bing(query):
    raw = fetch("https://www.bing.com/images/search?q=" + urllib.parse.quote(query))
    if not raw:
        return []
    text = raw.decode("utf-8", "ignore")
    out = []
    for m in re.findall(r'class="iusc"[^>]*?m="([^"]+)"', text):
        try:
            obj = json.loads(htmlmod.unescape(m))
        except Exception:
            continue
        if obj.get("murl"):
            out.append((obj["murl"], obj.get("t") or "", obj.get("purl") or ""))
    return out


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    for sid in IDS:
        e = plan[sid]
        latin = e["latin"]
        genus = latin.split()[0].lower()
        epithet = latin.split()[1].lower() if len(latin.split()) > 1 else ""
        best = None
        for q in (latin, latin + " animal", genus):
            for url, title, page in bing(q)[:12]:
                hay = (title + " " + page + " " + url).lower()
                if genus not in hay and not (epithet and epithet in hay):
                    continue
                raw = fetch(url)
                if not raw or len(raw) < 15000:
                    continue
                try:
                    from PIL import Image
                    import io
                    im = Image.open(io.BytesIO(raw)); im.load()
                    w, h = im.size
                except Exception:
                    continue
                if min(w, h) < 600:
                    continue
                score = min(w, h) - abs((w / h) - 1.4) * 250
                if best is None or score > best[0]:
                    best = (score, url, raw)
            if best:
                break
        if not best:
            print("none", sid, flush=True)
            continue
        score, url, raw = best
        saved, err = fi.save_image(e, raw)
        print(sid, "saved" if not err else err, flush=True)
        if not err:
            ledger[sid] = {"author": "Bing 图片（版权归原作者）", "license": "unknown", "source": url,
                           "name": e["name"], "latin": e["latin"],
                           "note": "网络图片（Bing 拉丁名检索，许可未核验，仅个人学习参考）"}
            fi.write_credits(ledger)
    print("done")


if __name__ == "__main__":
    main()
