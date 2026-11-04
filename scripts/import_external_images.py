# -*- coding: utf-8 -*-
"""外部图片导入：把豆包查找/人工收集的物种图片，按许可校验后导入站点。

流程：读取清单 CSV → 校验 id/来源/作者/许可 → 压缩为 900px JPEG → 全站去重
→ 写入 assets/images → 更新版权账本（js/image-credits.js + plan/image-credits.json）
→ 输出报告 plan/external-import-report.json。

清单列（UTF-8 CSV）：
  id,file,source,author,license,note
  - id: 站点物种 id（必须已存在于 plan/species*.json）
  - file: 图片路径（相对清单文件或绝对路径）
  - source: 图片所在网页 URL（不是搜索结果页）
  - author: 作者/摄影者
  - license: CC0 / PD / CC BY / CC BY-SA / CC BY-NC / CC BY-NC-SA（也接受 4.0 写法）
  - note: 备注（可空）

用法：
  python scripts/import_external_images.py --manifest plan/external-images.csv --dry-run
  python scripts/import_external_images.py --manifest plan/external-images.csv
  python scripts/import_external_images.py --manifest ... --commercial-only
"""
import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {"cc0", "pd", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
COMMERCIAL = {"cc0", "pd", "cc-by", "cc-by-sa"}
MAX_WIDTH = 900
MIN_SIDE = 400
JPEG_QUALITY = 82


def md5_bytes(data):
    return hashlib.md5(data).hexdigest()


def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_license(raw):
    s = (raw or "").strip().lower()
    s = s.replace("_", "-").replace(" ", "-")
    s = s.replace("creative-commons-", "").replace("creativecommons-", "")
    for suffix in ("-4.0", "-3.0", "-2.0", "-1.0", "-international", "-igo"):
        s = s.replace(suffix, "")
    mapping = {
        "cc0": "cc0", "pd": "pd", "public-domain": "pd", "公有领域": "pd", "公共领域": "pd",
        "cc-by": "cc-by", "ccby": "cc-by",
        "cc-by-sa": "cc-by-sa", "ccbysa": "cc-by-sa",
        "cc-by-nc": "cc-by-nc", "ccbync": "cc-by-nc",
        "cc-by-nc-sa": "cc-by-nc-sa", "ccbyncsa": "cc-by-nc-sa",
    }
    return mapping.get(s, s)


def process_row(row, plan, ledger, used_hashes, manifest_dir, args):
    sid = (row.get("id") or "").strip()
    errors = []
    entry = plan.get(sid)
    if not entry:
        return None, ["物种 id 不存在: " + (sid or "(空)")], sid
    raw_file = (row.get("file") or "").strip()
    if not raw_file:
        return None, ["缺少 file 列"], sid
    path = Path(raw_file)
    if not path.is_absolute():
        path = (manifest_dir / path).resolve()
    if not path.exists():
        return None, ["图片不存在: " + str(path)], sid
    source = (row.get("source") or "").strip()
    if not source.lower().startswith(("http://", "https://")):
        errors.append("source 必须是图片所在网页 URL")
    author = (row.get("author") or "").strip()
    if not author:
        errors.append("缺少作者 author")
    license_raw = row.get("license") or ""
    lic = norm_license(license_raw)
    if lic not in ALLOWED:
        errors.append(f"许可不允许: {license_raw!r}（允许 {sorted(ALLOWED)}）")
    if args.commercial_only and lic not in COMMERCIAL:
        errors.append(f"--commercial-only 要求可商用许可，当前为 {lic}")
    if errors:
        return None, errors, sid

    try:
        img = Image.open(path)
        img.load()
    except Exception as exc:  # noqa: BLE001
        return None, [f"图片无法解码: {exc}"], sid
    w, h = img.size
    if min(w, h) < MIN_SIDE:
        return None, [f"分辨率过低: {w}x{h}（最小边需 ≥ {MIN_SIDE}）"], sid
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if w > MAX_WIDTH:
        nh = max(1, round(h * MAX_WIDTH / w))
        img = img.resize((MAX_WIDTH, nh), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True)
    data = buf.getvalue()
    if len(data) < 8000:
        return None, ["压缩后过小，疑似无效图"], sid
    digest = md5_bytes(data)
    other = used_hashes.get(digest)
    if other and other != sid:
        errors.append(f"该图片已用于物种 {other}（全站唯一性校验失败，可用 --allow-duplicate 放宽）")
    if errors and not args.allow_duplicate:
        return None, errors, sid

    if not args.dry_run:
        out = fi.IMG_DIR / entry["tab"] / (sid + ".jpg")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        ledger[sid] = {
            "author": author,
            "license": lic,
            "source": source,
            "name": entry["name"],
            "latin": entry["latin"],
            "note": (row.get("note") or "").strip() or "外部导入（豆包查找/人工提供）",
        }
    # dry-run 也登记哈希，便于在同一份清单内发现重复图片
    used_hashes[digest] = sid
    return {"id": sid, "name": entry["name"], "license": lic, "bytes": len(data),
            "width": img.width, "height": img.height, "source": source, "author": author}, [], sid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "plan" / "external-images.csv"))
    ap.add_argument("--dry-run", action="store_true", help="只校验，不写入")
    ap.add_argument("--commercial-only", action="store_true", help="只接受 CC0/PD/CC BY/CC BY-SA")
    ap.add_argument("--allow-duplicate", action="store_true", help="允许与其他物种共用同一张图")
    args = ap.parse_args()

    manifest = Path(args.manifest)
    if not manifest.exists():
        print("找不到清单:", manifest)
        print("请先复制模板: plan/external-images.template.csv -> plan/external-images.csv 并填写。")
        raise SystemExit(2)

    plan = {e["id"]: e for e in fi.load_plan()}
    ledger = fi.load_json(fi.LEDGER, {})
    used_hashes = {}
    for e in plan.values():
        p = fi.IMG_DIR / e["tab"] / (e["id"] + ".jpg")
        if p.exists():
            used_hashes.setdefault(md5_file(p), e["id"])

    with manifest.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    print("清单行数:", len(rows), "| dry-run:", args.dry_run, "| commercial-only:", args.commercial_only)

    accepted, rejected = [], []
    for idx, row in enumerate(rows, start=2):
        if not any((v or "").strip() for v in row.values()):
            continue
        info, errs, sid = process_row(row, plan, ledger, used_hashes, manifest.parent, args)
        if errs:
            rejected.append({"row": idx, "id": sid, "errors": errs})
        else:
            accepted.append(info)

    if not args.dry_run and accepted:
        fi.write_credits(ledger)

    report = {
        "manifest": str(manifest),
        "dryRun": args.dry_run,
        "commercialOnly": args.commercial_only,
        "accepted": accepted,
        "rejected": rejected,
    }
    (ROOT / "plan" / "external-import-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n通过:", len(accepted), " 拒绝:", len(rejected))
    for a in accepted:
        print("  ✓", a["id"], a["name"], a["license"], f'{a["width"]}x{a["height"]}')
    for r in rejected:
        print("  ✗ 行", r["row"], r["id"], "；".join(r["errors"]))
    if accepted and not args.dry_run:
        print("\n版权账本已更新。建议随后运行：")
        print("  node scripts/validate-data.mjs --images")
        print("  python scripts/audit_correspondence.py")
    if rejected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
