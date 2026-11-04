# -*- coding: utf-8 -*-
"""把一段 registerSpecies(...) 代码安全追加到数据文件末尾 sentinel 之前。

用法：
    python scripts/append_batch.py data/animals/02-birds.js plan/tmp/batch1.js

- 目标文件必须存在且含 FILE-END sentinel；
- 片段文件为 UTF-8 文本，内容以 registerSpecies(...) 开头；
- 只做文本插入，不读取/重写其余内容，避免大文件上下文问题。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = "/* ==== FILE-END: 在此行之前追加新的 registerSpecies 调用 ==== */"


def resolve(p):
    path = Path(p)
    return path if path.is_absolute() else ROOT / path


def main():
    if len(sys.argv) < 3:
        print("用法: python scripts/append_batch.py <目标数据文件> <片段文件>")
        raise SystemExit(2)
    target = resolve(sys.argv[1])
    snippet_path = resolve(sys.argv[2])
    if not target.exists():
        print("目标文件不存在:", target)
        raise SystemExit(2)
    if not snippet_path.exists():
        print("片段文件不存在:", snippet_path)
        raise SystemExit(2)
    text = target.read_text(encoding="utf-8")
    snippet = snippet_path.read_text(encoding="utf-8").strip()
    # 去掉写文件时可能带入的 BOM
    while snippet.startswith("\ufeff"):
        snippet = snippet[1:].lstrip()
    if SENTINEL not in text:
        print("目标文件缺少 sentinel:", target)
        raise SystemExit(2)
    if "registerSpecies(" not in snippet:
        print("片段未包含 registerSpecies(...)")
        raise SystemExit(2)
    if "FILE-END" in snippet:
        print("片段中请勿包含 sentinel")
        raise SystemExit(2)
    idx = text.index(SENTINEL)
    before = text[:idx].rstrip()
    after = text[idx:]
    new_text = before + "\n\n" + snippet + "\n\n" + after
    target.write_text(new_text, encoding="utf-8")
    print("OK appended ->", target.relative_to(ROOT), "| snippet chars:", len(snippet))


if __name__ == "__main__":
    main()
