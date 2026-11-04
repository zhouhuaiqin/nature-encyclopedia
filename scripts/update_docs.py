# -*- coding: utf-8 -*-
"""更新 SPEC.md 与 index.html meta 中的物种数量到 2400。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "SPEC.md"
s = p.read_text(encoding="utf-8")

repl = {
    "共收录 **2000 个物种**：动物 1180 种（10 个分类）+ 植物与菌物 820 种（8 个分类）。":
        "共收录 **2400 个物种**：动物 1372 种（10 个分类）+ 植物与菌物 1028 种（8 个分类）。",
    "├─ data/animals/06d-insects-extra2.js [扩编·昆虫续 3]":
        "├─ data/animals/06d-insects-extra2.js [扩编·昆虫续 3]\n├─ data/animals/06e-insects-extra3.js [扩编·昆虫续 4]",
    "├─ data/plants/08b-fungi-extra.js    [扩编·真菌续]":
        "├─ data/plants/08b-fungi-extra.js    [扩编·真菌续]\n├─ data/plants/08c-fungi-extra2.js   [扩编·真菌续 2]",
    "├─ plan/species-animals-add4/5/6.json [Lead，v3.0 扩编分表，只读]":
        "├─ plan/species-animals-add4/5/6.json [Lead，v3.0 扩编分表，只读]\n├─ plan/species-animals-add7/8/9.json [Lead，v3.1 扩编分表，只读]",
    "├─ plan/species-plants-add3/4.json   [Lead，v3.0 扩编分表，只读]":
        "├─ plan/species-plants-add3/4.json   [Lead，v3.0 扩编分表，只读]\n├─ plan/species-plants-add5/6.json   [Lead，v3.1 扩编分表，只读]",
    "| mammals | 哺乳动物 | animals | 01-mammals.js | 170 |": "| mammals | 哺乳动物 | animals | 01-mammals.js | 202 |",
    "| birds | 鸟类 | animals | 02-birds.js | 170 |": "| birds | 鸟类 | animals | 02-birds.js | 190 |",
    "| reptiles | 爬行动物 | animals | 03-reptiles.js | 90 |": "| reptiles | 爬行动物 | animals | 03-reptiles.js | 99 |",
    "| amphibians | 两栖动物 | animals | 04-amphibians.js | 70 |": "| amphibians | 两栖动物 | animals | 04-amphibians.js | 77 |",
    "| fish | 鱼类 | animals | 05-fish.js | 115 |": "| fish | 鱼类 | animals | 05-fish.js | 133 |",
    "| insects | 昆虫 | animals | 06-insects.js + 06b + 06c + 06d | 260 |": "| insects | 昆虫 | animals | 06-insects.js + 06b + 06c + 06d + 06e | 311 |",
    "| arachnids | 蛛形动物 | animals | 07-arachnids.js | 50 |": "| arachnids | 蛛形动物 | animals | 07-arachnids.js | 60 |",
    "| crustaceans | 甲壳动物 | animals | 08-crustaceans.js | 65 |": "| crustaceans | 甲壳动物 | animals | 08-crustaceans.js | 68 |",
    "| mollusks | 软体动物 | animals | 09-mollusks.js | 90 |": "| mollusks | 软体动物 | animals | 09-mollusks.js | 108 |",
    "| other-invertebrates | 其他无脊椎动物 | animals | 10-other-invertebrates.js | 100 |": "| other-invertebrates | 其他无脊椎动物 | animals | 10-other-invertebrates.js | 124 |",
    "| trees | 乔木 | plants | 01-trees.js | 140 |": "| trees | 乔木 | plants | 01-trees.js | 165 |",
    "| shrubs | 灌木与花木 | plants | 02-shrubs.js | 110 |": "| shrubs | 灌木与花木 | plants | 02-shrubs.js | 129 |",
    "| flowers | 花卉与草本 | plants | 03-flowers.js | 120 |": "| flowers | 花卉与草本 | plants | 03-flowers.js | 146 |",
    "| succulents | 多肉植物 | plants | 04-succulents.js | 70 |": "| succulents | 多肉植物 | plants | 04-succulents.js | 90 |",
    "| aquatic | 水生植物 | plants | 05-aquatic.js | 60 |": "| aquatic | 水生植物 | plants | 05-aquatic.js | 79 |",
    "| ferns-gymnosperms | 蕨类与裸子植物 | plants | 06-ferns-gymnosperms.js | 70 |": "| ferns-gymnosperms | 蕨类与裸子植物 | plants | 06-ferns-gymnosperms.js | 80 |",
    "| crops | 农作物与经济植物 | plants | 07-crops.js | 110 |": "| crops | 农作物与经济植物 | plants | 07-crops.js | 133 |",
    "| fungi | 真菌（菌物界） | plants | 08-fungi.js + 08b | 140 |": "| fungi | 真菌（菌物界） | plants | 08-fungi.js + 08b + 08c | 206 |",
    "扩编分表 `species-animals-add1~add6.json`、`species-plants-add1~add4.json`（合计 2000 种）":
        "扩编分表 `species-animals-add1~add9.json`、`species-plants-add1~add6.json`（合计 2400 种）",
}
for a, b in repl.items():
    if a not in s:
        print("NOT FOUND:", a[:60])
    s = s.replace(a, b)
p.write_text(s, encoding="utf-8")

idx = ROOT / "index.html"
t = idx.read_text(encoding="utf-8")
t = t.replace("收录 2000 个物种", "收录 2400 个物种")
idx.write_text(t, encoding="utf-8")
print("SPEC/meta updated; SPEC chars:", len(s))
