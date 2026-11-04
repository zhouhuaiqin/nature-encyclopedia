# -*- coding: utf-8 -*-
"""图片质量评分 v2：人手（底部皮肤区域）、主体居中、原始分辨率。"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "plan" / "photo-quality.json"


def score_image(p):
    im = Image.open(p)
    ow, oh = im.size
    img = im.convert("RGB").resize((320, 240))
    a = np.asarray(img).astype(np.float32)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
    skin_mask = ((cb >= 80) & (cb <= 125) & (cr >= 136) & (cr <= 172) & (y > 60)).astype(np.float32)
    skin = float(skin_mask.mean())
    # 底部 30% 区域的皮肤比例（手持照片大多在下方/边缘）
    h, w = skin_mask.shape
    bottom = float(skin_mask[int(h * 0.7):, :].mean())
    # 边缘皮肤比例
    border = np.ones_like(skin_mask)
    border[int(h * 0.12):int(h * 0.88), int(w * 0.12):int(w * 0.88)] = 0
    edge_skin = float((skin_mask * border).mean())
    # 主体居中：边缘能量重心偏移
    gray = y
    gx = np.abs(np.diff(gray, axis=1))[:-1, :]
    gy = np.abs(np.diff(gray, axis=0))[:, :-1]
    mag = np.clip(gx + gy - (gx + gy).mean(), 0, None)
    total = mag.sum() + 1e-6
    ys, xs = np.mgrid[0:mag.shape[0], 0:mag.shape[1]]
    cx = (xs * mag).sum() / total
    cy = (ys * mag).sum() / total
    off = ((cx - (w - 1) / 2) ** 2 + (cy - (h - 1) / 2) ** 2) ** 0.5 / ((w / 2) ** 2 + (h / 2) ** 2) ** 0.5
    return {"skin": round(skin, 3), "bottomSkin": round(bottom, 3), "edgeSkin": round(edge_skin, 3),
            "centerOffset": round(float(off), 3), "w": ow, "h": oh}


def main():
    plan = fi.load_plan()
    ledger = fi.load_json(fi.LEDGER, {})
    rows = []
    for e in plan:
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        if not p.exists():
            continue
        note = (ledger.get(e["id"]) or {}).get("note") or ""
        if "原创占位图" in note:
            rows.append({"id": e["id"], "name": e["name"], "category": e["category"],
                         "placeholder": True, "reason": "placeholder"})
            continue
        try:
            s = score_image(p)
        except Exception:
            continue
        reasons = []
        if s["bottomSkin"] > 0.16 or s["edgeSkin"] > 0.10 or s["skin"] > 0.22:
            reasons.append("hands")
        if s["centerOffset"] > 0.30:
            reasons.append("offcenter")
        if min(s["w"], s["h"]) < 480:
            reasons.append("small")
        if reasons:
            rows.append({"id": e["id"], "name": e["name"], "category": e["category"],
                         "placeholder": False, **s, "reason": ",".join(reasons)})
    REPORT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    c = Counter()
    for r in rows:
        for reason in r["reason"].split(","):
            c[reason] += 1
    print("待优化图片:", len(rows), dict(c))
    print("hands 示例:", [r["id"] for r in rows if "hands" in r["reason"]][:10])
    print("offcenter 示例:", [r["id"] for r in rows if "offcenter" in r["reason"]][:10])


if __name__ == "__main__":
    main()
