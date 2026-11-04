# -*- coding: utf-8 -*-
"""构建生态关系数据：按中文名解析物种 id，输出 data/relations.js。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_images as fi

ROOT = Path(__file__).resolve().parent.parent

TYPES = {
    "predation": {"label": "捕食", "color": "#a34a2a"},
    "mutualism": {"label": "共生", "color": "#2f6b4f"},
    "parasitism": {"label": "寄生", "color": "#7a4b8f"},
    "competition": {"label": "竞争", "color": "#b07a45"},
    "pollination": {"label": "传粉", "color": "#c9a227"},
    "dispersal": {"label": "传播", "color": "#3d6f8e"},
    "habitat": {"label": "栖息", "color": "#6f7a71"},
}

# (捕食者/一方, 被食者/另一方, 类型, 备注)
EDGES = [
    ("虎", "梅花鹿", "predation", "虎的主要猎物之一"),
    ("虎", "野猪", "predation", "虎会捕食野猪"),
    ("狮子", "细纹斑马", "predation", "草原上的典型捕食关系"),
    ("狮子", "山斑马", "predation", "狮子捕食斑马"),
    ("狼", "欧洲野兔", "predation", "狼追捕野兔"),
    ("狼", "马鹿", "predation", "狼群围猎马鹿"),
    ("雪豹", "岩羊", "predation", "雪豹最典型的猎物"),
    ("棕熊", "大马哈鱼", "predation", "秋季棕熊捕食洄游鲑鱼"),
    ("北极熊", "环斑海豹", "predation", "北极熊依赖海豹脂肪"),
    ("虎鲸", "环斑海豹", "predation", "虎鲸捕食海豹"),
    ("虎鲸", "帽带企鹅", "predation", "南极虎鲸的猎物"),
    ("大白鲨", "北海狮", "predation", "大白鲨捕食海狮"),
    ("金雕", "旱獭", "predation", "金雕捕食旱獭"),
    ("金雕", "北美鼠兔", "predation", "鼠兔是金雕的食物"),
    ("雕鸮", "北美鼠兔", "predation", "夜行猛禽捕食鼠兔"),
    ("黑眉锦蛇", "泽蛙", "predation", "蛇类捕食蛙类"),
    ("短尾蝮", "泽蛙", "predation", "蝮蛇捕食蛙与鼠"),
    ("广斧螳", "中华蚱蜢", "predation", "螳螂伏击蝗虫"),
    ("碧伟蜓", "淡色库蚊", "predation", "蜻蜓捕食蚊虫"),
    ("七星瓢虫", "棉蚜", "predation", "瓢虫是蚜虫的天敌"),
    ("大腹园蛛", "家蝇", "predation", "结网捕食飞虫"),
    ("美洲豹", "小鼷鹿", "predation", "美洲豹捕食小型有蹄类"),
    ("绿水蚺", "小鼷鹿", "predation", "森蚺捕食小型哺乳动物"),
    ("尼罗鳄", "角马", "predation", "鳄鱼伏击饮水角马"),
    ("太平洋清洁虾", "龙胆石斑", "mutualism", "清洁虾为石斑鱼清除寄生虫"),
    ("榕小蜂", "榕树", "mutualism", "榕树依赖榕小蜂传粉"),
    ("榕小蜂", "无花果", "mutualism", "专性传粉共生"),
    ("黄猄蚁", "相思树", "mutualism", "蚂蚁保护植物、植物提供食物与住所"),
    ("西方蜜蜂", "向日葵", "pollination", "蜜蜂为向日葵传粉"),
    ("中华蜜蜂", "油菜", "pollination", "重要农业传粉者"),
    ("明亮熊蜂", "番茄", "pollination", "熊蜂为番茄振动传粉"),
    ("黑毛蚁", "棉蚜", "mutualism", "蚂蚁取食蜜露并保护蚜虫"),
    ("美味牛肝菌", "马尾松", "mutualism", "外生菌根共生"),
    ("周氏啮小蜂", "美国白蛾", "parasitism", "寄生蜂防治美国白蛾"),
    ("日本血吸虫", "湖北钉螺", "parasitism", "钉螺是日本血吸虫的中间宿主"),
    ("恶性疟原虫", "中华按蚊", "parasitism", "按蚊传播疟疾"),
    ("狮子", "斑鬣狗", "competition", "争夺猎物与领地"),
    ("狼", "猞猁", "competition", "竞争中小型猎物"),
    ("松鼠", "红松", "dispersal", "松鼠贮食帮助红松传播种子"),
    ("松鼠", "麻栎", "dispersal", "埋藏橡子促进栎树更新"),
    ("白头鹎", "樱桃", "dispersal", "鸟类取食果实并传播种子"),
    ("亚洲象", "无花果", "dispersal", "大象取食果实并长距离传播种子"),
    ("灰头绿啄木鸟", "马尾松", "habitat", "在树干凿洞取食与营巢"),
    ("斑腿泛树蛙", "香樟", "habitat", "树蛙栖息于树冠与枝叶间"),
    ("鹿角珊瑚", "扬幡蝴蝶鱼", "habitat", "珊瑚礁为鱼类提供栖息与庇护"),
    ("大熊猫", "毛竹", "predation", "大熊猫以竹子为主食（植食）"),
    ("长颈鹿", "金合欢", "predation", "长颈鹿取食金合欢枝叶"),
    ("黑脉金斑蝶", "马利筋", "predation", "幼虫取食马利筋并获得毒素"),
    ("狮子", "角马", "predation", "狮子捕食角马"),
    ("斑鬣狗", "角马", "predation", "鬣狗群捕食角马"),
    ("狼", "驼鹿", "predation", "狼群围猎驼鹿"),
    ("狼", "驯鹿", "predation", "狼捕食驯鹿"),
    ("雪豹", "盘羊", "predation", "雪豹捕食盘羊"),
    ("虎", "马鹿", "predation", "虎捕食马鹿"),
    ("猞猁", "欧洲野兔", "predation", "猞猁捕食野兔"),
    ("金钱豹", "梅花鹿", "predation", "豹类捕食鹿类"),
]


def main():
    plan = fi.load_plan()
    by_name = {}
    for e in plan:
        by_name.setdefault(e["name"], e)
    edges = []
    missing = []
    for a, b, t, note in EDGES:
        ea, eb = by_name.get(a), by_name.get(b)
        if not ea or not eb:
            missing.append((a, b))
            continue
        edges.append({"from": ea["id"], "to": eb["id"], "type": t, "note": note,
                      "fromName": ea["name"], "toName": eb["name"]})
    data = {"types": TYPES, "edges": edges}
    out = ROOT / "data" / "relations.js"
    out.write_text("/* 生态关系数据（Lead 维护）：data/relations.js */\nwindow.RELATIONS = "
                   + json.dumps(data, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    print("edges:", len(edges), "missing:", missing)


if __name__ == "__main__":
    main()
