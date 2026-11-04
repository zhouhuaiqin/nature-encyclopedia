# -*- coding: utf-8 -*-
"""Bing 图片（拉丁学名查询 + 标题/页面相关性过滤），失败回退 iNat/GBIF。"""
import html as htmlmod
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def bing_results(query):
    raw = fetch("https://www.bing.com/images/search?q=" + urllib.parse.quote(query) + "&form=HDRSC2")
    if not raw:
        return []
    text = raw.decode("utf-8", "ignore")
    out = []
    for m in re.findall(r'class="iusc"[^>]*?m="([^"]+)"', text):
        try:
            obj = json.loads(htmlmod.unescape(m))
        except Exception:
            continue
        url = obj.get("murl") or ""
        title = obj.get("t") or ""
        page = obj.get("purl") or ""
        if url.startswith("http"):
            out.append((url, title, page))
    if not out:
        urls = re.findall(r'"murl":"(.*?)"', text)
        out = [(u.replace("\\u002f", "/").replace("\\/", "/"), "", "") for u in urls if u.startswith("http")]
    return out


def relevant(item, latin):
    url, title, page = item
    hay = (title + " " + page + " " + url).lower()
    genus = latin.split()[0].lower()
    epithet = latin.split()[1].lower() if len(latin.split()) > 1 else ""
    return genus in hay or (epithet and len(epithet) > 3 and epithet in hay)


def inat_photos(latin):
    q = urllib.parse.quote(latin)
    data = None
    try:
        req = urllib.request.Request(fi.API + "/observations?taxon_name=" + q + "&photos=true&order_by=votes&per_page=5",
                                     headers={"User-Agent": "ne-fill"})
        data = json.loads(urllib.request.urlopen(req, timeout=25).read())
    except Exception:
        return []
    out = []
    for obs in (data or {}).get("results") or []:
        tax = (obs.get("taxon") or {}).get("name") or ""
        if tax and not tax.lower().startswith(latin.lower()):
            continue
        for ph in obs.get("photos") or []:
            out.append(ph)
    return out


def gbif_photos(latin):
    try:
        req = urllib.request.Request("https://api.gbif.org/v1/species/match?name=" + urllib.parse.quote(latin),
                                     headers={"User-Agent": "ne-fill"})
        match = json.loads(urllib.request.urlopen(req, timeout=20).read())
        key = match.get("usageKey")
        if not key:
            return []
        req = urllib.request.Request("https://api.gbif.org/v1/occurrence/search?taxonKey=" + str(key) +
                                     "&mediaType=StillImage&limit=8", headers={"User-Agent": "ne-fill"})
        data = json.loads(urllib.request.urlopen(req, timeout=25).read())
        out = []
        for occ in (data or {}).get("results") or []:
            for m in occ.get("media") or []:
                if m.get("identifier"):
                    out.append(m)
        return out
    except Exception:
        return []


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    targets = [e for e in plan.values()
               if ("外部补图" in ((ledger.get(e["id"]) or {}).get("note") or "")
                   or "网络图片" in ((ledger.get(e["id"]) or {}).get("note") or ""))]
    print("targets:", len(targets), flush=True)
    lock = threading.Lock()
    stats = {"bing": 0, "inat": 0, "gbif": 0, "none": 0}

    def process(e):
        latin = e["latin"].replace("'", "").replace("×", " ").strip()
        genus = latin.split()[0]
        # Bing：拉丁名 + 相关性过滤
        cands = []
        for q in (latin, genus + " species"):
            for url, title, page in bing_results(q)[:10]:
                if not relevant((url, title, page), latin):
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
                if min(w, h) < 500:
                    continue
                score = min(w, h) - abs((w / h) - 1.35) * 300
                cands.append((score, url, raw))
            if len(cands) >= 2:
                break
        if cands:
            cands.sort(reverse=True)
            score, url, raw = cands[0]
            saved, err = fi.save_image(e, raw)
            if not err:
                with lock:
                    ledger[e["id"]] = {"author": "Bing 图片（版权归原作者）", "license": "unknown",
                                       "source": url, "name": e["name"], "latin": e["latin"],
                                       "note": "网络图片（Bing 拉丁名检索，许可未核验，仅个人学习参考）"}
                    fi.write_credits(ledger); stats["bing"] += 1
                print("bing", e["id"], flush=True)
                return
        # iNat
        for ph in inat_photos(e["latin"])[:3]:
            url = (ph.get("url") or "").replace("/square.", "/large.").replace("/small.", "/large.").replace("/medium.", "/large.")
            raw = fetch(url)
            if not raw:
                continue
            saved, err = fi.save_image(e, raw)
            if not err:
                with lock:
                    ledger[e["id"]] = {"author": ph.get("attribution") or "iNaturalist contributor",
                                       "license": (ph.get("license_code") or "").lower() or "arr",
                                       "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                                       "name": e["name"], "latin": e["latin"],
                                       "note": "外部补图（iNaturalist，未核验许可，仅个人学习参考）"}
                    fi.write_credits(ledger); stats["inat"] += 1
                print("inat", e["id"], flush=True)
                return
        # GBIF
        for m in gbif_photos(e["latin"])[:3]:
            raw = fetch(m.get("identifier"))
            if not raw:
                continue
            saved, err = fi.save_image(e, raw)
            if not err:
                with lock:
                    ledger[e["id"]] = {"author": m.get("rightsHolder") or "GBIF 数据提供者",
                                       "license": (m.get("license") or "unknown").lower(),
                                       "source": m.get("identifier"), "name": e["name"], "latin": e["latin"],
                                       "note": "外部补图（GBIF，未核验许可，仅个人学习参考）"}
                    fi.write_credits(ledger); stats["gbif"] += 1
                print("gbif", e["id"], flush=True)
                return
        with lock:
            stats["none"] += 1
        print("none", e["id"], flush=True)

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
