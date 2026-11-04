/* 生态关系数据（Lead 维护）：data/relations.js */
window.RELATIONS = {
  "types": {
    "predation": {
      "label": "捕食",
      "color": "#a34a2a"
    },
    "mutualism": {
      "label": "共生",
      "color": "#2f6b4f"
    },
    "parasitism": {
      "label": "寄生",
      "color": "#7a4b8f"
    },
    "competition": {
      "label": "竞争",
      "color": "#b07a45"
    },
    "pollination": {
      "label": "传粉",
      "color": "#c9a227"
    },
    "dispersal": {
      "label": "传播",
      "color": "#3d6f8e"
    },
    "habitat": {
      "label": "栖息",
      "color": "#6f7a71"
    }
  },
  "edges": [
    {
      "from": "mammal-tiger",
      "to": "mammal-sika-deer",
      "type": "predation",
      "note": "虎的主要猎物之一",
      "fromName": "虎",
      "toName": "梅花鹿"
    },
    {
      "from": "mammal-tiger",
      "to": "mammal-wild-boar",
      "type": "predation",
      "note": "虎会捕食野猪",
      "fromName": "虎",
      "toName": "野猪"
    },
    {
      "from": "mammal-lion",
      "to": "mammal-grevys-zebra",
      "type": "predation",
      "note": "草原上的典型捕食关系",
      "fromName": "狮子",
      "toName": "细纹斑马"
    },
    {
      "from": "mammal-lion",
      "to": "mammal-mountain-zebra",
      "type": "predation",
      "note": "狮子捕食斑马",
      "fromName": "狮子",
      "toName": "山斑马"
    },
    {
      "from": "mammal-wolf",
      "to": "mammal-european-hare",
      "type": "predation",
      "note": "狼追捕野兔",
      "fromName": "狼",
      "toName": "欧洲野兔"
    },
    {
      "from": "mammal-wolf",
      "to": "mammal-red-deer",
      "type": "predation",
      "note": "狼群围猎马鹿",
      "fromName": "狼",
      "toName": "马鹿"
    },
    {
      "from": "mammal-snow-leopard",
      "to": "mammal-blue-sheep",
      "type": "predation",
      "note": "雪豹最典型的猎物",
      "fromName": "雪豹",
      "toName": "岩羊"
    },
    {
      "from": "mammal-brown-bear",
      "to": "fish-chum-salmon",
      "type": "predation",
      "note": "秋季棕熊捕食洄游鲑鱼",
      "fromName": "棕熊",
      "toName": "大马哈鱼"
    },
    {
      "from": "mammal-polar-bear",
      "to": "mammal-ringed-seal",
      "type": "predation",
      "note": "北极熊依赖海豹脂肪",
      "fromName": "北极熊",
      "toName": "环斑海豹"
    },
    {
      "from": "mammal-orca",
      "to": "mammal-ringed-seal",
      "type": "predation",
      "note": "虎鲸捕食海豹",
      "fromName": "虎鲸",
      "toName": "环斑海豹"
    },
    {
      "from": "mammal-orca",
      "to": "bird-chinstrap-penguin",
      "type": "predation",
      "note": "南极虎鲸的猎物",
      "fromName": "虎鲸",
      "toName": "帽带企鹅"
    },
    {
      "from": "fish-great-white-shark",
      "to": "mammal-stellers-sea-lion",
      "type": "predation",
      "note": "大白鲨捕食海狮",
      "fromName": "大白鲨",
      "toName": "北海狮"
    },
    {
      "from": "bird-golden-eagle",
      "to": "mammal-alpine-marmot",
      "type": "predation",
      "note": "金雕捕食旱獭",
      "fromName": "金雕",
      "toName": "旱獭"
    },
    {
      "from": "bird-golden-eagle",
      "to": "mammal-american-pika",
      "type": "predation",
      "note": "鼠兔是金雕的食物",
      "fromName": "金雕",
      "toName": "北美鼠兔"
    },
    {
      "from": "bird-eurasian-eagle-owl",
      "to": "mammal-american-pika",
      "type": "predation",
      "note": "夜行猛禽捕食鼠兔",
      "fromName": "雕鸮",
      "toName": "北美鼠兔"
    },
    {
      "from": "reptile-beauty-ratsnake",
      "to": "amphibian-marsh-frog",
      "type": "predation",
      "note": "蛇类捕食蛙类",
      "fromName": "黑眉锦蛇",
      "toName": "泽蛙"
    },
    {
      "from": "reptile-short-tailed-pit-viper",
      "to": "amphibian-marsh-frog",
      "type": "predation",
      "note": "蝮蛇捕食蛙与鼠",
      "fromName": "短尾蝮",
      "toName": "泽蛙"
    },
    {
      "from": "insect-oriental-mantis",
      "to": "insect-chinese-grasshopper",
      "type": "predation",
      "note": "螳螂伏击蝗虫",
      "fromName": "广斧螳",
      "toName": "中华蚱蜢"
    },
    {
      "from": "insect-emperor-dragonfly",
      "to": "insect-northern-house-mosquito",
      "type": "predation",
      "note": "蜻蜓捕食蚊虫",
      "fromName": "碧伟蜓",
      "toName": "淡色库蚊"
    },
    {
      "from": "insect-seven-spotted-ladybird",
      "to": "insect-cotton-aphid",
      "type": "predation",
      "note": "瓢虫是蚜虫的天敌",
      "fromName": "七星瓢虫",
      "toName": "棉蚜"
    },
    {
      "from": "arachnid-ventricose-araneus",
      "to": "insect-housefly",
      "type": "predation",
      "note": "结网捕食飞虫",
      "fromName": "大腹园蛛",
      "toName": "家蝇"
    },
    {
      "from": "mammal-jaguar",
      "to": "mammal-lesser-mouse-deer",
      "type": "predation",
      "note": "美洲豹捕食小型有蹄类",
      "fromName": "美洲豹",
      "toName": "小鼷鹿"
    },
    {
      "from": "reptile-green-anaconda",
      "to": "mammal-lesser-mouse-deer",
      "type": "predation",
      "note": "森蚺捕食小型哺乳动物",
      "fromName": "绿水蚺",
      "toName": "小鼷鹿"
    },
    {
      "from": "reptile-nile-crocodile",
      "to": "mammal-wildebeest",
      "type": "predation",
      "note": "鳄鱼伏击饮水角马",
      "fromName": "尼罗鳄",
      "toName": "角马"
    },
    {
      "from": "crustacean-pacific-cleaner-shrimp",
      "to": "fish-giant-grouper",
      "type": "mutualism",
      "note": "清洁虾为石斑鱼清除寄生虫",
      "fromName": "太平洋清洁虾",
      "toName": "龙胆石斑"
    },
    {
      "from": "insect-fig-wasp-2",
      "to": "tree-banyan",
      "type": "mutualism",
      "note": "榕树依赖榕小蜂传粉",
      "fromName": "榕小蜂",
      "toName": "榕树"
    },
    {
      "from": "insect-fig-wasp-2",
      "to": "tree-edible-fig",
      "type": "mutualism",
      "note": "专性传粉共生",
      "fromName": "榕小蜂",
      "toName": "无花果"
    },
    {
      "from": "insect-weaver-ant",
      "to": "tree-formosan-acacia",
      "type": "mutualism",
      "note": "蚂蚁保护植物、植物提供食物与住所",
      "fromName": "黄猄蚁",
      "toName": "相思树"
    },
    {
      "from": "insect-western-honey-bee",
      "to": "flower-common-sunflower",
      "type": "pollination",
      "note": "蜜蜂为向日葵传粉",
      "fromName": "西方蜜蜂",
      "toName": "向日葵"
    },
    {
      "from": "insect-eastern-honey-bee",
      "to": "crop-rapeseed",
      "type": "pollination",
      "note": "重要农业传粉者",
      "fromName": "中华蜜蜂",
      "toName": "油菜"
    },
    {
      "from": "insect-bumblebee",
      "to": "crop-tomato",
      "type": "pollination",
      "note": "熊蜂为番茄振动传粉",
      "fromName": "明亮熊蜂",
      "toName": "番茄"
    },
    {
      "from": "insect-black-garden-ant",
      "to": "insect-cotton-aphid",
      "type": "mutualism",
      "note": "蚂蚁取食蜜露并保护蚜虫",
      "fromName": "黑毛蚁",
      "toName": "棉蚜"
    },
    {
      "from": "fungus-porcini",
      "to": "tree-masson-pine",
      "type": "mutualism",
      "note": "外生菌根共生",
      "fromName": "美味牛肝菌",
      "toName": "马尾松"
    },
    {
      "from": "insect-chouioia-wasp",
      "to": "insect-fall-webworm",
      "type": "parasitism",
      "note": "寄生蜂防治美国白蛾",
      "fromName": "周氏啮小蜂",
      "toName": "美国白蛾"
    },
    {
      "from": "invertebrate-japanese-blood-fluke",
      "to": "mollusk-oncomelania-snail",
      "type": "parasitism",
      "note": "钉螺是日本血吸虫的中间宿主",
      "fromName": "日本血吸虫",
      "toName": "湖北钉螺"
    },
    {
      "from": "invertebrate-malaria-parasite",
      "to": "insect-chinese-malaria-mosquito",
      "type": "parasitism",
      "note": "按蚊传播疟疾",
      "fromName": "恶性疟原虫",
      "toName": "中华按蚊"
    },
    {
      "from": "mammal-lion",
      "to": "mammal-spotted-hyena",
      "type": "competition",
      "note": "争夺猎物与领地",
      "fromName": "狮子",
      "toName": "斑鬣狗"
    },
    {
      "from": "mammal-wolf",
      "to": "mammal-lynx",
      "type": "competition",
      "note": "竞争中小型猎物",
      "fromName": "狼",
      "toName": "猞猁"
    },
    {
      "from": "mammal-red-squirrel",
      "to": "tree-korean-pine",
      "type": "dispersal",
      "note": "松鼠贮食帮助红松传播种子",
      "fromName": "松鼠",
      "toName": "红松"
    },
    {
      "from": "mammal-red-squirrel",
      "to": "tree-sawtooth-oak",
      "type": "dispersal",
      "note": "埋藏橡子促进栎树更新",
      "fromName": "松鼠",
      "toName": "麻栎"
    },
    {
      "from": "bird-light-vented-bulbul",
      "to": "crop-cherry",
      "type": "dispersal",
      "note": "鸟类取食果实并传播种子",
      "fromName": "白头鹎",
      "toName": "樱桃"
    },
    {
      "from": "mammal-asian-elephant",
      "to": "tree-edible-fig",
      "type": "dispersal",
      "note": "大象取食果实并长距离传播种子",
      "fromName": "亚洲象",
      "toName": "无花果"
    },
    {
      "from": "bird-grey-headed-woodpecker",
      "to": "tree-masson-pine",
      "type": "habitat",
      "note": "在树干凿洞取食与营巢",
      "fromName": "灰头绿啄木鸟",
      "toName": "马尾松"
    },
    {
      "from": "amphibian-spot-legged-tree-frog",
      "to": "tree-camphor",
      "type": "habitat",
      "note": "树蛙栖息于树冠与枝叶间",
      "fromName": "斑腿泛树蛙",
      "toName": "香樟"
    },
    {
      "from": "invertebrate-staghorn-coral-2",
      "to": "fish-threadfin-butterflyfish",
      "type": "habitat",
      "note": "珊瑚礁为鱼类提供栖息与庇护",
      "fromName": "鹿角珊瑚",
      "toName": "扬幡蝴蝶鱼"
    },
    {
      "from": "mammal-giant-panda",
      "to": "crop-moso-bamboo",
      "type": "predation",
      "note": "大熊猫以竹子为主食（植食）",
      "fromName": "大熊猫",
      "toName": "毛竹"
    },
    {
      "from": "mammal-giraffe",
      "to": "shrub-sweet-acacia",
      "type": "predation",
      "note": "长颈鹿取食金合欢枝叶",
      "fromName": "长颈鹿",
      "toName": "金合欢"
    },
    {
      "from": "insect-monarch-butterfly",
      "to": "shrub-bloodflower",
      "type": "predation",
      "note": "幼虫取食马利筋并获得毒素",
      "fromName": "黑脉金斑蝶",
      "toName": "马利筋"
    },
    {
      "from": "mammal-lion",
      "to": "mammal-wildebeest",
      "type": "predation",
      "note": "狮子捕食角马",
      "fromName": "狮子",
      "toName": "角马"
    },
    {
      "from": "mammal-spotted-hyena",
      "to": "mammal-wildebeest",
      "type": "predation",
      "note": "鬣狗群捕食角马",
      "fromName": "斑鬣狗",
      "toName": "角马"
    },
    {
      "from": "mammal-wolf",
      "to": "mammal-moose",
      "type": "predation",
      "note": "狼群围猎驼鹿",
      "fromName": "狼",
      "toName": "驼鹿"
    },
    {
      "from": "mammal-wolf",
      "to": "mammal-reindeer",
      "type": "predation",
      "note": "狼捕食驯鹿",
      "fromName": "狼",
      "toName": "驯鹿"
    },
    {
      "from": "mammal-snow-leopard",
      "to": "mammal-argali",
      "type": "predation",
      "note": "雪豹捕食盘羊",
      "fromName": "雪豹",
      "toName": "盘羊"
    },
    {
      "from": "mammal-tiger",
      "to": "mammal-red-deer",
      "type": "predation",
      "note": "虎捕食马鹿",
      "fromName": "虎",
      "toName": "马鹿"
    },
    {
      "from": "mammal-lynx",
      "to": "mammal-european-hare",
      "type": "predation",
      "note": "猞猁捕食野兔",
      "fromName": "猞猁",
      "toName": "欧洲野兔"
    },
    {
      "from": "mammal-leopard",
      "to": "mammal-sika-deer",
      "type": "predation",
      "note": "豹类捕食鹿类",
      "fromName": "金钱豹",
      "toName": "梅花鹿"
    }
  ]
};
