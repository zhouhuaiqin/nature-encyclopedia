/* ============================================================
 * 自然图鉴 · 站点元信息与分类体系
 * 维护：Lead。其他成员请勿修改本文件。
 * ============================================================ */
window.SITE = {
  title: "自然图鉴",
  subtitle: "动植物百科图典",
  tagline: "把整个自然，收进一册图鉴",
  intro:
    "从雪线之上的雪豹到雨林深处的蓝闪蝶，从两亿年前的银杏到餐桌上的稻米——2663 份生命档案，动物、植物与菌物三界并列，按界、门、纲、目、科、属层层展开。这是一册可以慢慢翻的自然志，也是一座纸上的自然博物馆。",
  version: "3.9",
  regions: 2663
};

window.TABS = [
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
];

window.CATEGORIES = [
  { code: "mammals", name: "哺乳动物", tab: "animals", kingdom: "动物界", icon: "🐾", blurb: "恒温胎生、以乳汁育幼的脊椎动物" },
  { code: "birds", name: "鸟类", tab: "animals", kingdom: "动物界", icon: "🦜", blurb: "身披羽毛、大多数能飞行的温血动物" },
  { code: "reptiles", name: "爬行动物", tab: "animals", kingdom: "动物界", icon: "🦎", blurb: "覆鳞甲、变温、多产卵的脊椎动物" },
  { code: "amphibians", name: "两栖动物", tab: "animals", kingdom: "动物界", icon: "🐸", blurb: "水陆两栖、皮肤裸露的变温动物" },
  { code: "fish", name: "鱼类", tab: "animals", kingdom: "动物界", icon: "🐟", blurb: "用鳃呼吸、以鳍游动的水生脊椎动物" },
  { code: "insects", name: "昆虫", tab: "animals", kingdom: "动物界", icon: "🦋", blurb: "六足、体分三段，地球上最繁盛的动物类群" },
  { code: "arachnids", name: "蛛形动物", tab: "animals", kingdom: "动物界", icon: "🕷️", blurb: "八足、体分头胸腹的节肢动物" },
  { code: "crustaceans", name: "甲壳动物", tab: "animals", kingdom: "动物界", icon: "🦀", blurb: "身披坚硬甲壳、多栖于水中的节肢动物" },
  { code: "mollusks", name: "软体动物", tab: "animals", kingdom: "动物界", icon: "🐙", blurb: "身体柔软、常带贝壳的海洋与陆生类群" },
  { code: "other-invertebrates", name: "其他无脊椎动物", tab: "animals", kingdom: "动物界", icon: "🪸", blurb: "珊瑚、水母、海星、蚯蚓等无脊椎生命" },
  { code: "trees", name: "乔木", tab: "plants", kingdom: "植物界", icon: "🌳", blurb: "具有明显主干的高大木本植物" },
  { code: "shrubs", name: "灌木与花木", tab: "plants", kingdom: "植物界", icon: "🌿", blurb: "低矮丛生或以观花观叶见长的木本植物" },
  { code: "flowers", name: "花卉与草本", tab: "plants", kingdom: "植物界", icon: "🌸", blurb: "一二年生或多年生草本与观赏花卉" },
  { code: "succulents", name: "多肉植物", tab: "plants", kingdom: "植物界", icon: "🌵", blurb: "茎叶肥厚、善于储水的耐旱植物" },
  { code: "aquatic", name: "水生植物", tab: "plants", kingdom: "植物界", icon: "🪷", blurb: "生于水中或湿地、形态各异的植物" },
  { code: "ferns-gymnosperms", name: "蕨类与裸子植物", tab: "plants", kingdom: "植物界", icon: "🌲", blurb: "以孢子或裸露种子繁殖的古老植物" },
  { code: "crops", name: "农作物与经济植物", tab: "plants", kingdom: "植物界", icon: "🌾", blurb: "供养人类衣食的栽培植物" },
  { code: "fungi", name: "真菌", tab: "fungi", kingdom: "真菌界", icon: "🍄", blurb: "菌物界：从食用菌到虫草的神奇生命" }
];

window.CATEGORY_MAP = {};
window.CATEGORIES.forEach(function (c) {
  window.CATEGORY_MAP[c.code] = c;
});

/* 策展精选（首页封面与精选栏使用） */
window.FEATURED = [
  "mammal-giant-panda", "bird-red-crowned-crane", "insect-blue-morpho",
  "aquatic-giant-water-lily", "mammal-tiger", "fungus-fly-agaric",
  "bird-crested-ibis", "tree-ginkgo", "fish-whale-shark", "flower-common-sunflower"
];

/* 分类总览卡片封面（用该类代表物种图片） */
window.CATEGORY_COVERS = {
  mammals: "mammal-giant-panda",
  birds: "bird-red-crowned-crane",
  reptiles: "reptile-komodo-dragon",
  amphibians: "amphibian-red-eyed-tree-frog",
  fish: "fish-whale-shark",
  insects: "insect-blue-morpho",
  arachnids: "arachnid-mexican-red-knee",
  crustaceans: "crustacean-coconut-crab",
  mollusks: "mollusk-chambered-nautilus",
  "other-invertebrates": "invertebrate-moon-jelly",
  trees: "tree-ginkgo",
  shrubs: "shrub-tree-peony",
  flowers: "flower-common-sunflower",
  succulents: "succulent-golden-barrel-cactus",
  aquatic: "aquatic-sacred-lotus",
  "ferns-gymnosperms": "fern-spinulose-tree-fern",
  crops: "crop-asian-rice",
  fungi: "fungus-fly-agaric"
};
