# -*- coding: utf-8 -*-
"""最后 15 个占位图：GBIF 文本搜索 + iNat 属级回退（标注为近缘参考）。"""
import json
import sys
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
IDS = ['insect-biting-midge', 'mollusk-subcrenata-ark', 'insect-sand-fly', 'insect-firefly-3',
       'insect-elwesi-swallowtail', 'mollusk-octopus-2', 'tree-banana-shrub', 'succulent-red-flame',
       'succulent-letizia', 'insect-chouioia-wasp', 'insect-protura', 'mollusk-goulds-jackknife',
       'invertebrate-cyclospora', 'invertebrate-acanthamoeba', 'fern-archangiopteris']


def get_json(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-fill"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def fetch(url, timeout=45):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-fill"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    lock = threading.Lock()
    stats = {"ok": 0, "none": 0}

    def process(sid):
        e = plan[sid]
        # 1) GBIF 文本搜索
        data = get_json("https://api.gbif.org/v1/occurrence/search?q=" + urllib.parse.quote(e["latin"]) +
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
                                       "note": "外部补图（GBIF，未核验许可，仅个人学习参考）"}
                        fi.write_credits(ledger)
                        stats["ok"] += 1
                    print("ok(gbif) " + sid, flush=True)
                    return
        # 2) iNat 文本搜索，接受属级
        genus = e["latin"].split()[0]
        data = get_json(fi.API + "/observations?q=" + urllib.parse.quote(genus) +
                        "&photos=true&order_by=votes&per_page=10")
        for obs in (data or {}).get("results") or []:
            tax = (obs.get("taxon") or {}).get("name") or ""
            if not tax.lower().startswith(genus.lower()):
                continue
            for ph in obs.get("photos") or []:
                url = ph.get("url") or ""
                for v in ("large", "medium"):
                    u = url.replace("/square.", "/" + v + ".").replace("/small.", "/" + v + ".").replace("/medium.", "/" + v + ".")
                    raw = fetch(u)
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
                            fi.write_credits(ledger)
                            stats["ok"] += 1
                        print("ok(genus) " + sid, flush=True)
                        return
        with lock:
            stats["none"] += 1
        print("none " + sid, flush=True)

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(process, sid) for sid in IDS]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                print("ERR", exc, flush=True)
    fi.write_credits(ledger)
    print("完成:", stats, flush=True)


if __name__ == "__main__":
    main()
