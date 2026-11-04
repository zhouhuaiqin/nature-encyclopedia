# -*- coding: utf-8 -*-
"""补充候选：狮子、虎、鹦鹉螺、牡丹、金琥。"""
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "plan" / "curate"
LEGAL = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
IDS = ["mammal-lion", "mammal-tiger", "mollusk-chambered-nautilus", "shrub-tree-peony", "succulent-golden-barrel-cactus"]


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-curate"})
        with urllib.request.urlopen(req, timeout=50) as r:
            return r.read()
    except Exception:
        return None


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    cands = json.loads((OUT / "candidates.json").read_text(encoding="utf-8"))
    for sid in IDS:
        e = plan[sid]
        import urllib.parse
        url = (fi.API + "/observations?taxon_name=" + urllib.parse.quote(e["latin"]) +
               "&photos=true&quality_grade=research&order_by=votes&per_page=4&photo_license=" +
               ",".join(sorted(LEGAL)))
        data = fi.api_get(url)
        rows = []
        for obs in (data or {}).get("results") or []:
            tax = (obs.get("taxon") or {}).get("name") or ""
            if tax and not tax.lower().startswith(e["latin"].lower()):
                continue
            phs = [p for p in (obs.get("photos") or []) if (p.get("license_code") or "").lower() in LEGAL]
            if not phs:
                continue
            ph = phs[0]
            u = ph.get("url") or ""
            for v in ("square", "small", "medium"):
                if "/" + v + "." in u:
                    u = u.replace("/" + v + ".", "/small.")
                    break
            rows.append({"photoId": ph.get("id"), "license": (ph.get("license_code") or "").lower(),
                         "attribution": ph.get("attribution") or "", "url": u})
        cands[sid] = rows[:4]
        d = OUT / sid
        d.mkdir(parents=True, exist_ok=True)
        for i, row in enumerate(rows[:4]):
            raw = fetch(row["url"])
            if raw:
                (d / f"{i + 1}.jpg").write_bytes(raw)
        print(sid, len(rows))
    (OUT / "candidates.json").write_text(json.dumps(cands, ensure_ascii=False, indent=2), encoding="utf-8")

    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
    CW, CH = 200, 180
    sheet = Image.new("RGB", (CW * 4, CH * len(IDS) + 24), (245, 241, 232))
    d = ImageDraw.Draw(sheet)
    d.text((8, 4), "extra candidates (choose per row)", fill=(22, 56, 42), font=font)
    for r, sid in enumerate(IDS):
        e = plan[sid]
        d.text((8, 24 + r * CH + 4), e["name"] + "  " + sid, fill=(160, 40, 40), font=font)
        for i in range(4):
            p = OUT / sid / f"{i + 1}.jpg"
            if not p.exists():
                continue
            x = i * CW
            y = 24 + r * CH
            im = Image.open(p).convert("RGB")
            im.thumbnail((CW - 8, CH - 34))
            sheet.paste(im, (x + 4, y + 24))
            d.text((x + 6, y + CH - 22), str(i + 1), fill=(30, 40, 34), font=font)
    sheet.save(ROOT / "plan" / "shots" / "curate-extra.jpg", quality=88)
    print("sheet saved")


if __name__ == "__main__":
    main()
