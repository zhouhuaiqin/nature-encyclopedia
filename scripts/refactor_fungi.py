# -*- coding: utf-8 -*-
"""把菌物界从「植物与菌物」中拆出来：三标签（动物/植物/菌物）+ 相关 UI/构建/校验。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(p):
    return (ROOT / p).read_text(encoding="utf-8")


def write(p, s):
    (ROOT / p).write_text(s, encoding="utf-8")


def rep(p, a, b, count=1):
    s = read(p)
    if a not in s:
        print("MISS", p, a[:60])
        return
    s = s.replace(a, b, count)
    write(p, s)


# ---------- meta.js ----------
meta = read("data/meta.js")
start = meta.index("window.TABS = [")
end = meta.index("];", start) + 2
new_tabs = '''window.TABS = [
  {
    code: "animals",
    name: "动物界",
    short: "动物",
    icon: "🐾",
    blurb: "从平原到深海，从甲虫到蓝鲸——恒温的、变温的、会飞会游会打洞的动物邻居。"
  },
  {
    code: "plants",
    name: "植物界",
    short: "植物",
    icon: "🌿",
    blurb: "乔木、花草、多肉、水生与蕨类——不会移动，却供养着整个星球的生命。"
  },
  {
    code: "fungi",
    name: "菌物界",
    short: "菌物",
    icon: "🍄",
    blurb: "从食用菌、虫草到酵母与霉菌——独立于动植物的生命界，分解者与共生者。"
  }
];'''
meta = meta[:start] + new_tabs + meta[end:]
# fungi 分类 tab
lines = meta.split("\n")
for i, line in enumerate(lines):
    if 'code: "fungi"' in line:
        lines[i] = line.replace('tab: "plants"', 'tab: "fungi"')
meta = "\n".join(lines)
write("data/meta.js", meta)

# ---------- data-core.js ----------
s = read("js/data-core.js")
s = s.replace('var store = { animals: [], plants: [], loaded: false };',
              'var store = { animals: [], plants: [], fungi: [], loaded: false };')
s = s.replace('if (tab !== "animals" && tab !== "plants") {',
              'if (tab !== "animals" && tab !== "plants" && tab !== "fungi") {')
s = s.replace('var tab = entry && entry.tab === "plants" ? "plants" : "animals";',
              'var tab = entry && entry.tab === "animals" ? "animals" : "plants";')
write("js/data-core.js", s)

# ---------- 真菌数据文件改为 fungi 标签 ----------
for f in ["data/plants/08-fungi.js", "data/plants/08b-fungi-extra.js", "data/plants/08c-fungi-extra2.js"]:
    rep(f, 'registerSpecies("plants"', 'registerSpecies("fungi"')

# ---------- app.js ----------
app = read("js/app.js")
old_tabs_start = app.index("var TABS = window.TABS || [")
old_tabs_end = app.index("];", old_tabs_start) + 2
new_fallback = '''var TABS = window.TABS || [
    { code: "animals", name: "动物界" },
    { code: "plants", name: "植物界" },
    { code: "fungi", name: "菌物界" }
  ];'''
app = app[:old_tabs_start] + new_fallback + app[old_tabs_end:]
app = app.replace('var ALL = ENC.animals.concat(ENC.plants);',
                  'var ALL = ENC.animals.concat(ENC.plants, ENC.fungi || []);')
app = app.replace('var COUNTS_BY_TAB = { animals: ENC.animals.length, plants: ENC.plants.length };',
                  'var COUNTS_BY_TAB = { animals: ENC.animals.length, plants: ENC.plants.length, fungi: (ENC.fungi || []).length };')
app = app.replace('''  function imageOf(entry) {
    return typeof window.speciesImage === "function" ? window.speciesImage(entry)
      : "assets/images/" + (entry.tab === "plants" ? "plants" : "animals") + "/" + entry.id + ".webp";
  }
  function thumbOf(entry) {
    return "assets/thumbs/" + (entry.tab === "plants" ? "plants" : "animals") + "/" + entry.id + ".webp";
  }''',
'''  function imageOf(entry) {
    return typeof window.speciesImage === "function" ? window.speciesImage(entry)
      : "assets/images/" + (entry.tab === "animals" ? "animals" : "plants") + "/" + entry.id + ".webp";
  }
  function thumbOf(entry) {
    return "assets/thumbs/" + (entry.tab === "animals" ? "animals" : "plants") + "/" + entry.id + ".webp";
  }''')
app = app.replace('"assets/images/placeholder-" + (entry.tab === "plants" ? "plant" : "animal") + ".svg"',
                  '"assets/images/placeholder-" + (entry.tab === "animals" ? "animal" : "plant") + ".svg"')
app = app.replace('if (raw === "/animals" || raw === "/plants") return { view: "tab", tab: raw.slice(1) };',
                  'if (raw === "/animals" || raw === "/plants" || raw === "/fungi") return { view: "tab", tab: raw.slice(1) };')
app = app.replace('statPlants: $("#stat-plants"),', 'statPlants: $("#stat-plants"),\n    statFungi: $("#stat-fungi"),')
app = app.replace('''      [el.statTotal, el.statAnimals, el.statPlants, el.statFamilies].forEach(function (node, i) {
        if (node) node.textContent = [total, COUNTS_BY_TAB.animals, COUNTS_BY_TAB.plants, families][i];
      });''',
'''      [el.statTotal, el.statAnimals, el.statPlants, el.statFungi, el.statFamilies].forEach(function (node, i) {
        if (node) node.textContent = [total, COUNTS_BY_TAB.animals, COUNTS_BY_TAB.plants, COUNTS_BY_TAB.fungi, families][i];
      });''')
app = app.replace('''      animateNumber(el.statTotal, total);
      animateNumber(el.statAnimals, COUNTS_BY_TAB.animals);
      animateNumber(el.statPlants, COUNTS_BY_TAB.plants);
      animateNumber(el.statFamilies, families);''',
'''      animateNumber(el.statTotal, total);
      animateNumber(el.statAnimals, COUNTS_BY_TAB.animals);
      animateNumber(el.statPlants, COUNTS_BY_TAB.plants);
      animateNumber(el.statFungi, COUNTS_BY_TAB.fungi);
      animateNumber(el.statFamilies, families);''')
write("js/app.js", app)

# ---------- 静态构建 ----------
bs = read("scripts/build_static.cjs")
bs = bs.replace('const ALL = ENC.animals.concat(ENC.plants);',
                'const ALL = ENC.animals.concat(ENC.plants, ENC.fungi || []);')
bs = bs.replace('return "assets/images/" + (e.tab === "plants" ? "plants" : "animals") + "/" + e.id + ".webp";',
                'return "assets/images/" + (e.tab === "animals" ? "animals" : "plants") + "/" + e.id + ".webp";')
write("scripts/build_static.cjs", bs)

print("refactor done")
