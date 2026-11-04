# -*- coding: utf-8 -*-
"""检查 JS 数据文件的括号平衡，找出未闭合的 registerSpecies 批次。"""
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
depth = 0
last_top = 0
for i, line in enumerate(lines, 1):
    in_s = None
    esc = False
    for ch in line:
        if in_s:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_s:
                in_s = None
            continue
        if ch in ("'", '"'):
            in_s = ch
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
    if line.strip() in ("});", "]);", ");") and depth == 0:
        last_top = i
        print(f"line {i}: 顶层批次结束（depth=0）")
print("final depth =", depth, "last clean top-level line =", last_top, "total lines =", len(lines))
