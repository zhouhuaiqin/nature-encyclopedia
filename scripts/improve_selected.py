# -*- coding: utf-8 -*-
"""为重点展示物种（精选、分类封面、每类前 3、狮子等）换成社区投票靠前的本种照片。"""
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi
import improve_photos as ip

ROOT = Path(__file__).resolve().parent.parent


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    cat_first = {}
    order = []
    for e in fi.load_plan():
        c = e["category"]
        if c not in cat_first:
            cat_first[c] = 0
            order.append(e)
    # 每个分类前 3 个 + meta 精选与封面 + 指定重点
    ids = set()
    meta = (ROOT / "data" / "meta.js").read_text(encoding="utf-8")
    import re
    ids.update(re.findall(r'"([a-z0-9-]+)"', re.search(r"window\.FEATURED = \[(.*?)\];", meta, re.S).group(1)))
    cover_block = meta.split("window.CATEGORY_COVERS = {")[1].split("};")[0]
    ids.update(re.findall(r':\s*"([a-z0-9-]+)"', cover_block))
    seen = {}
    for e in fi.load_plan():
        seen.setdefault(e["category"], 0)
        if seen[e["category"]] < 3:
            ids.add(e["id"])
            seen[e["category"]] += 1
    ids.update(["mammal-lion", "mammal-tiger", "mammal-giant-panda", "bird-red-crowned-crane",
                "insect-blue-morpho", "fish-whale-shark", "fungus-fly-agaric", "tree-ginkgo"])
    targets = [plan[i] for i in ids if i in plan]
    print("selected:", len(targets), flush=True)

    lock = threading.Lock()
    stats = {"ok": 0, "fail": 0}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(ip.process, e, ledger, lock): e for e in targets}
        for fut in as_completed(futures):
            e = futures[fut]
            try:
                kind, sid, info = fut.result()
            except Exception:  # noqa: BLE001
                kind, sid = "fail", e["id"]
            stats["ok" if kind == "ok" else "fail"] += 1
    fi.write_credits(ledger)
    print("selected improve:", stats, flush=True)


if __name__ == "__main__":
    main()
