# -*- coding: utf-8 -*-
"""删除「同属近缘/占位图」等非本种照片，并登记待重新抓取清单。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent


def main():
    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    removed = []
    for sid, rec in list(ledger.items()):
        note = rec.get("note") or ""
        if "原创占位图" in note or "同属近缘种" in note or "同类群代表照片" in note:
            e = plan.get(sid)
            if not e:
                continue
            p = fi.IMG_DIR / e["tab"] / (sid + ".jpg")
            if p.exists():
                p.unlink()
            ledger.pop(sid, None)
            removed.append(sid)
    fi.write_credits(ledger)
    (ROOT / "plan" / "refetch-ids.json").write_text(
        json.dumps(removed, ensure_ascii=False, indent=2), encoding="utf-8")
    print("删除非本种/占位图片:", len(removed), "剩余 credits:", len(ledger))


if __name__ == "__main__":
    main()
