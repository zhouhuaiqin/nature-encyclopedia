# -*- coding: utf-8 -*-
"""最后一批（18 个）坏图：iNat 属级 / GBIF 文本搜索；再不行用占位图，绝不保留无关图。"""
import json
import sys
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi
import make_placeholders as mp

ROOT = Path(__file__).resolve().parent.parent
BAD_IDS = ['insect-biting-midge', 'mollusk-subcrenata-ark', 'mammal-common-eland', 'insect-sand-fly',
           'insect-firefly-3', 'mollusk-clam-2', 'mollusk-octopus-2', 'tree-banana-shrub',
           'flower-rangoon-creeper', 'succulent-red-flame', 'crop-brussels-sprouts', 'crop-kohlrabi',
           'succulent-letizia', 'insect-protura', 'mollusk-goulds-jackknife', 'invertebrate-cyclospora',
           'invertebrate-acanthamoeba', 'fern-archangiopteris']


def get_json(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-last"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def fetch(url, timeout=45):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-last"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    lock = threading.Lock()
    stats = {"photo": 0, "placeholder": 0}

    def process(sid):
        e = plan[sid]
        genus = e["latin"].split()[0]
        # iNat 属级
        data = get_json(fi.API + "/taxa?q=" + urllib.parse.quote(genus) + "&per_page=3")
        for t in (data or {}).get("results") or []:
            if not (t.get("name") or "").lower().startswith(genus.lower()):
                continue
            detail = get_json(fi.API + "/taxa/" + str(t.get("id")))
            phs = (detail or {}).get("taxon_photos") or []
            for p in phs[:2]:
                ph = p.get("photo") or p
                url = (ph.get("url") or "").replace("/square.", "/large.").replace("/small.", "/large.")
                raw = fetch(url)
                if not raw:
                    continue
                saved, err = fi.save_image(e, raw)
                if not err:
                    with lock:
                        ledger[sid] = {"author": ph.get("attribution") or "iNaturalist contributor",
                                       "license": (ph.get("license_code") or "").lower() or "arr",
                                       "source": "https://www.inaturalist.org/photos/" + str(ph.get("id")),
                                       "name": e["name"], "latin": e["latin"],
                                       "note": "外部补图（同属参考图，未核验许可，仅个人学习参考）"}
                        fi.write_credits(ledger); stats["photo"] += 1
                    print("inat", sid, flush=True)
                    return
        # GBIF 文本
        data = get_json("https://api.gbif.org/v1/occurrence/search?q=" + urllib.parse.quote(genus) +
                        "&mediaType=StillImage&limit=10")
        for occ in (data or {}).get("results") or []:
            for m in occ.get("media") or []:
                raw = fetch(m.get("identifier"))
                if not raw:
                    continue
                saved, err = fi.save_image(e, raw)
                if not err:
                    with lock:
                        ledger[sid] = {"author": m.get("rightsHolder") or "GBIF 数据提供者",
                                       "license": (m.get("license") or "unknown").lower(),
                                       "source": m.get("identifier"), "name": e["name"], "latin": e["latin"],
                                       "note": "外部补图（同属参考图，未核验许可，仅个人学习参考）"}
                        fi.write_credits(ledger); stats["photo"] += 1
                    print("gbif", sid, flush=True)
                    return
        # 占位图
        p = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
        mp.make_placeholder(e, p)
        with lock:
            ledger[sid] = {"author": "自然图鉴（本站自绘）", "license": "cc0", "source": "本站原创占位图",
                           "name": e["name"], "latin": e["latin"], "note": "原创占位图（CC0），非真实照片"}
            fi.write_credits(ledger); stats["placeholder"] += 1
        print("placeholder", sid, flush=True)

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(process, sid) for sid in BAD_IDS]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                print("ERR", exc, flush=True)
    fi.write_credits(ledger)
    print("完成:", stats, flush=True)


if __name__ == "__main__":
    main()
