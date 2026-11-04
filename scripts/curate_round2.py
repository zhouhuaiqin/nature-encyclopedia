# -*- coding: utf-8 -*-
"""第二轮代表物种候选图：雪豹、大猩猩、丹顶鹤、朱鹮、绿孔雀、长颈鹿、白头海雕、雪鸮、大红鹳、帝企鹅、银杏、麋鹿、藏羚羊、大鲵。"""
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "plan" / "curate2"
LEGAL = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
NAMES = ["雪豹", "大猩猩", "丹顶鹤", "朱鹮", "绿孔雀", "长颈鹿", "白头海雕", "雪鸮",
         "大红鹳", "帝企鹅", "银杏", "麋鹿", "藏羚羊", "大鲵"]


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ne-curate2"})
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.read()
    except Exception:
        return None


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    by_name = {e["name"]: e for e in plan.values()}
    ids = [by_name[n]["id"] for n in NAMES if n in by_name]
    OUT.mkdir(parents=True, exist_ok=True)
    cands = {}
    for sid in ids:
        e = plan[sid]
        import urllib.parse
        url = (fi.API + "/observations?taxon_name=" + urllib.parse.quote(e["latin"]) +
               "&photos=true&quality_grade=research&order_by=votes&per_page=6&photo_license=" +
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
        cands[sid] = rows[:6]
        d = OUT / sid
        d.mkdir(parents=True, exist_ok=True)
        for i, row in enumerate(rows[:6]):
            raw = fetch(row["url"])
            if raw:
                (d / f"{i + 1}.jpg").write_bytes(raw)
        print(e["name"], len(rows), flush=True)
    (OUT / "candidates.json").write_text(json.dumps(cands, ensure_ascii=False, indent=2), encoding="utf-8")

    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13)
    CW, CH = 190, 170
    per_sheet = 7
    for s in range(0, len(ids), per_sheet):
        group = ids[s:s + per_sheet]
        sheet = Image.new("RGB", (CW * 6, CH * len(group) + 24), (245, 241, 232))
        d = ImageDraw.Draw(sheet)
        d.text((8, 4), f"round2 candidates {s // per_sheet + 1}", fill=(22, 56, 42), font=font)
        for r, sid in enumerate(group):
            e = plan[sid]
            d.text((8, 24 + r * CH + 4), e["name"] + " " + sid, fill=(160, 40, 40), font=font)
            for i in range(6):
                p = OUT / sid / f"{i + 1}.jpg"
                if not p.exists():
                    continue
                x = i * CW
                y = 24 + r * CH
                im = Image.open(p).convert("RGB")
                im.thumbnail((CW - 8, CH - 32))
                sheet.paste(im, (x + 4, y + 22))
                d.text((x + 6, y + CH - 20), str(i + 1), fill=(30, 40, 34), font=font)
        out = ROOT / "plan" / "shots" / f"round2-{s // per_sheet + 1}.jpg"
        sheet.save(out, quality=88)
        print("sheet", out.name, flush=True)


if __name__ == "__main__":
    main()
