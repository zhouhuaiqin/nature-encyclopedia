# -*- coding: utf-8 -*-
"""把无照片的牛樟芝替换为马勃。"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "data/plants/10-new-fungi.js"
s = p.read_text(encoding="utf-8")
start = s.index('  {\n    id: "fungus-antrodia-cinnamomea"')
end = s.index('  {\n    id: "fungus-termitomyces"')
new = '''  {
    id: "fungus-puffball",
    name: "马勃",
    latin: "Lycoperdon perlatum",
    kingdom: "真菌界",
    category: "fungi",
    aliases: ["网纹马勃", "灰包"],
    taxonomy: { phylum: "担子菌门", class: "伞菌纲", order: "伞菌目", family: "蘑菇科", genus: "马勃属" },
    summary: "常见于草地与林地的球形真菌，成熟后顶端开孔，轻触即喷出大量褐色孢子。",
    description: "马勃的子实体幼时近球形或梨形，表面灰白至淡褐色，布满细小疣状突起；内部初期白色、质地紧实，成熟后逐渐变为黄褐色粉末状孢子团。此时顶端会裂开一个小孔，雨滴、动物踩踏或轻触都会让孢子像烟雾一样喷出，借风力传播。\\n\\n马勃广泛分布于温带草地、林缘和牧场，夏秋雨后常见，营腐生生活，分解土壤中的有机质。幼嫩时在部分地区被当作食用菌，但必须与有毒的硬皮马勃、鹅膏菌幼体等严格区分；成熟后孢子粉不宜食用。孢子粉末细小，过敏体质者应避免吸入。",
    habitat: "草地、林缘、牧场与落叶层，夏秋雨后常见",
    distribution: "北半球温带地区广泛分布，中国多地常见",
    conservation: "未评估；常见腐生真菌",
    details: [
      { label: "子实体", value: "幼时球形或梨形，成熟后孢子团粉末状" },
      { label: "孢子传播", value: "顶端开孔，触碰或雨滴触发喷出" },
      { label: "生态", value: "腐生，分解草地与林地有机质" },
      { label: "食用性", value: "幼体在部分地区食用，须严格鉴别" },
      { label: "风险", value: "孢子粉可致过敏，成熟后不宜食用" }
    ],
    facts: [
      "马勃成熟后像“烟包”，轻触就会喷出一团褐色孢子雾。",
      "它幼时内部是白色海绵状，成熟后才变成粉末状孢子团。",
      "马勃与有毒的硬皮马勃外形相似，野外采食必须谨慎。"
    ],
    tags: ["腐生真菌", "孢子传播", "草地", "食用风险"],
    featured: false
  },
'''
s = s[:start] + new + s[end:]
p.write_text(s, encoding="utf-8")

p = ROOT / "plan/species-new-plants.json"
s = p.read_text(encoding="utf-8")
s = s.replace('["fungus-antrodia-cinnamomea", "牛樟芝", "Antrodia cinnamomea", "fungi", "10-new-fungi.js"]',
              '["fungus-puffball", "马勃", "Lycoperdon perlatum", "fungi", "10-new-fungi.js"]')
p.write_text(s, encoding="utf-8")

p = ROOT / "scripts/fetch_new_species_images.py"
s = p.read_text(encoding="utf-8")
s = s.replace('{"id": "fungus-antrodia-cinnamomea", "name": "牛樟芝", "latin": "Antrodia cinnamomea", "tab": "fungi"}',
              '{"id": "fungus-puffball", "name": "马勃", "latin": "Lycoperdon perlatum", "tab": "fungi"}')
p.write_text(s, encoding="utf-8")
print("swapped")
