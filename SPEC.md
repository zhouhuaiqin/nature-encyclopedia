# 自然图鉴 · 动植物百科 —— 项目说明与数据契约（唯一权威规范）

项目根目录（下文用 `<ROOT>` 表示）：`C:\Users\靳绍航\Documents\deepseek-harness\default-workspace\nature-encyclopedia`

## 1. 项目目标

做一个**纯静态、可在本地直接双击打开**的中文动植物百科网站（file:// 协议可用，不依赖任何服务器/网络/外部 CDN）。
共收录 **2658 个物种**：动物 1534 种（10 个分类）+ 植物与菌物 1124 种（8 个分类）。
每个物种必须有：中文名、拉丁学名、分类地位（界门纲目科属）、简介、详细描述、特征数据、趣味知识、**一张本地图片**。
页面要求：简洁、工整、信息密度高、响应式、有分类筛选与全站搜索、详情弹层。

## 2. 技术约束

- 纯 HTML + CSS + 原生 JS，**不引入任何第三方库、字体、CDN、图标库**。
- 数据以 `data/*.js` 形式通过 `<script>` 同步加载（不是 fetch JSON），保证 `file://` 直接打开可用。
- 图片全部下载到 `assets/images/` 本地，页面用相对路径引用。
- 不启动任何开发服务器；校验页面用 Edge headless 截图（见 §7）。
- Node 路径：`C:\Users\靳绍航\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe`
- Python（含 Pillow）路径：`C:\Users\靳绍航\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`
- Edge 路径：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`

## 3. 目录结构与文件归属（严禁越界修改他人文件）

```
nature-encyclopedia/
├─ index.html                        [前端]
├─ css/style.css                     [前端]
├─ js/app.js                         [前端]
├─ js/data-core.js                   [Lead]
├─ js/image-credits.js               [图片]
├─ data/meta.js                      [Lead]
├─ data/animals/01-mammals.js        [数据 A1]
├─ data/animals/02-birds.js          [数据 A2]
├─ data/animals/03-reptiles.js       [数据 A3]
├─ data/animals/04-amphibians.js     [数据 A3]
├─ data/animals/05-fish.js           [数据 A4]
├─ data/animals/06-insects.js        [数据 A5]
├─ data/animals/06b-insects-extra.js [扩编·昆虫续 1]
├─ data/animals/06c-insects-extra.js [扩编·昆虫续 2]
├─ data/animals/06d-insects-extra2.js [扩编·昆虫续 3]
├─ data/animals/06e-insects-extra3.js [扩编·昆虫续 4]
├─ data/animals/07-arachnids.js      [数据 A3]
├─ data/animals/08-crustaceans.js    [数据 A5]
├─ data/animals/09-mollusks.js       [数据 A4]
├─ data/animals/10-other-invertebrates.js  [数据 A5]
├─ data/plants/01-trees.js           [数据 P1]
├─ data/plants/02-shrubs.js          [数据 P1]
├─ data/plants/03-flowers.js         [数据 P2]
├─ data/plants/04-succulents.js      [数据 P2]
├─ data/plants/05-aquatic.js         [数据 P2]
├─ data/plants/06-ferns-gymnosperms.js [数据 P3]
├─ data/plants/07-crops.js           [数据 P3]
├─ data/plants/08-fungi.js           [数据 P3]
├─ data/plants/08b-fungi-extra.js    [扩编·真菌续]
├─ data/plants/08c-fungi-extra2.js   [扩编·真菌续 2]
├─ plan/species-animals.json         [Lead，初始物种总表，只读]
├─ plan/species-plants.json          [Lead，初始物种总表，只读]
├─ plan/species-animals-add1/2/3.json [Lead，扩编分表（第 5 项=目标数据文件），只读]
├─ plan/species-animals-add4/5/6.json [Lead，v3.0 扩编分表，只读]
├─ plan/species-animals-add7/8/9.json [Lead，v3.1 扩编分表，只读]
├─ plan/species-animals-add10/11/12.json [Lead，v3.2 扩编分表，只读]
├─ plan/species-plants-add1/2.json   [Lead，扩编分表（第 5 项=目标数据文件），只读]
├─ plan/species-plants-add3/4.json   [Lead，v3.0 扩编分表，只读]
├─ plan/species-plants-add5/6.json   [Lead，v3.1 扩编分表，只读]
├─ plan/species-plants-add7/8.json   [Lead，v3.2 扩编分表，只读]
├─ scripts/validate-data.mjs         [Lead]
├─ scripts/fetch_images.py           [图片]
└─ assets/images/animals|plants/*.jpg [图片]
```

## 4. 数据契约（每个物种对象）

数据文件内调用：

```js
registerSpecies("animals", [ {…}, {…} ]);   // 动物文件
registerSpecies("plants",  [ {…}, {…} ]);   // 植物/真菌文件
```

`registerSpecies` 由 `js/data-core.js` 提供，可在一个文件里调用多次；每个文件末尾必须有 sentinel 注释行：

```js
/* ==== FILE-END: 在此行之前追加新的 registerSpecies 调用 ==== */
```

之后追加内容时，用 edit 工具把该 sentinel 行替换成「新的 registerSpecies 调用 + 同样的 sentinel 行」即可，**不要重写整份文件**（防止输出过长被截断）。

### 4.1 字段定义

| 字段 | 类型 | 必填 | 要求 |
|---|---|---|---|
| `id` | string | 是 | **必须与 plan 文件中给定值完全一致**，小写字母/数字/连字符 |
| `name` | string | 是 | plan 给定中文名，完全一致 |
| `latin` | string | 是 | plan 给定拉丁学名，完全一致（格式：属名 种加词） |
| `kingdom` | string | 是 | 动物界 / 植物界 / 真菌界（与分类代码对应） |
| `category` | string | 是 | plan 给定分类代码（如 mammals、trees） |
| `aliases` | string[] | 是 | 0–4 个别名/俗称（可为 `[]`） |
| `taxonomy` | object | 是 | 必须含 5 个键：`phylum` `class` `order` `family` `genus`，均为非空字符串 |
| `summary` | string | 是 | 45–110 字，一句话概括 |
| `description` | string | 是 | 260–450 字，**两段**，段间用 `\n\n`；含外形、习性/用途、分布或典故 |
| `habitat` | string | 是 | 10–80 字，栖息环境 / 生长环境 |
| `distribution` | string | 是 | 8–80 字，地理分布 |
| `conservation` | string | 是 | IUCN 等级 + 保护级别，例：`IUCN 易危（VU）；中国国家一级保护动物`；无评估写 `暂无评估` |
| `details` | {label,value}[] | 是 | **5–8 项**特征数据，见 4.2 |
| `facts` | string[] | 是 | **3–5 条**趣味知识/冷知识，每条 15–60 字 |
| `tags` | string[] | 是 | **3–6 个**标签，每个 2–8 字 |
| `featured` | boolean | 否 | 代表物种可标 `true`（每分类最多 2 个） |

### 4.2 details 建议项目（按类群）

- 动物：食性、体型（体长）、体重、寿命、繁殖、活动节律、社会结构、天敌
- 植物：株高、花期、果期、光照、水分、土壤、繁殖方式、主要用途
- 真菌：菌盖/菌柄、生境、食用性、毒性、采收期、经济价值

**注意**：`details` 中禁止重复 `habitat`/`distribution` 已说过的空泛内容，要给具体数字或事实；不确定时用“约/可达”等限定词，禁止编造精确数据。

### 4.3 分类代码、物种数量与数据文件

| 分类代码 | 中文名 | tab | 数据文件 | 数量 |
|---|---|---|---|---|
| mammals | 哺乳动物 | animals | 01-mammals.js | 220 |
| birds | 鸟类 | animals | 02-birds.js | 209 |
| reptiles | 爬行动物 | animals | 03-reptiles.js | 105 |
| amphibians | 两栖动物 | animals | 04-amphibians.js | 84 |
| fish | 鱼类 | animals | 05-fish.js | 137 |
| insects | 昆虫 | animals | 06-insects.js + 06b + 06c + 06d + 06e | 357 |
| arachnids | 蛛形动物 | animals | 07-arachnids.js | 68 |
| crustaceans | 甲壳动物 | animals | 08-crustaceans.js | 77 |
| mollusks | 软体动物 | animals | 09-mollusks.js | 122 |
| other-invertebrates | 其他无脊椎动物 | animals | 10-other-invertebrates.js | 155 |
| trees | 乔木 | plants | 01-trees.js | 185 |
| shrubs | 灌木与花木 | plants | 02-shrubs.js | 145 |
| flowers | 花卉与草本 | plants | 03-flowers.js | 165 |
| succulents | 多肉植物 | plants | 04-succulents.js | 97 |
| aquatic | 水生植物 | plants | 05-aquatic.js | 87 |
| ferns-gymnosperms | 蕨类与裸子植物 | plants | 06-ferns-gymnosperms.js | 88 |
| crops | 农作物与经济植物 | plants | 07-crops.js | 144 |
| fungi | 真菌（菌物界） | plants | 08-fungi.js + 08b + 08c | 213 |

**物种清单唯一来源**：`plan/species*.json` —— 初始总表 `species-animals.json` / `species-plants.json`，扩编分表 `species-animals-add1~add12.json`、`species-plants-add1~add8.json`（合计 2658 种）。
格式：`{"tab":"animals","species":[["id","中文名","学名","分类代码","目标数据文件"], ...]}`（初始总表没有第 5 项）。
写数据前先读 plan 分表，按**第 5 项目标数据文件**筛选出自己负责的物种，逐一收录，**不得遗漏、不得新增、不得改 id/name/latin**。
如认为 plan 有误（学名拼写等），先按 plan 写，然后把问题报告 Lead 裁定。

### 4.4 写作风格

- 简体中文，客观科普语气，不用第一人称、不用营销腔、不写“小编”。
- 纯文本：禁止 Markdown 语法、禁止 HTML 标签；中文用全角标点。
- 数字用阿拉伯数字，单位用 cm / m / km / kg / g / ℃ 等；时间用“年/月/天”。
- 保护等级参考 IUCN 红色名录（EX/EW/CR/EN/VU/NT/LC/DD）与中国国家重点保护野生动物名录；不确定写 `暂无评估`。
- 每个物种的 `summary`、`description`、`facts` 必须是**该物种独有信息**，禁止复制粘贴同一段模板（如“是重要的生态资源”这类废话）。

### 4.5 正确示例（一个完整条目）

```js
{
  id: "mammal-giant-panda",
  name: "大熊猫",
  latin: "Ailuropoda melanoleuca",
  kingdom: "动物界",
  category: "mammals",
  aliases: ["熊猫", "竹熊"],
  taxonomy: { phylum: "脊索动物门", class: "哺乳纲", order: "食肉目", family: "熊科", genus: "大熊猫属" },
  summary: "中国特有的珍稀兽类，以黑白相间的毛色和酷爱吃竹闻名，被称为“活化石”。",
  description: "大熊猫体型肥硕似熊，头圆尾短，黑白相间的毛色在密林中格外醒目……\n\n野生大熊猫主要生活在四川、陕西、甘肃三省的深山竹林……",
  habitat: "海拔 1200–3400 米的亚高山针阔混交林与竹林",
  distribution: "中国四川、陕西、甘肃三省山区",
  conservation: "IUCN 易危（VU）；中国国家一级保护动物",
  details: [
    { label: "食性", value: "99% 为竹子，也偶食小型动物" },
    { label: "体长", value: "120–180 cm" },
    { label: "体重", value: "70–125 kg" },
    { label: "寿命", value: "野外约 20 年，圈养可超 30 年" },
    { label: "繁殖", value: "每年 3–5 月发情，妊娠期 3–5 个月" }
  ],
  facts: ["大熊猫有“第六指”——由腕骨特化而成的伪拇指，帮助握住竹竿。", "每天进食 12–16 小时，吃掉 12–38 kg 竹子。"],
  tags: ["国宝", "食肉目", "竹林", "中国特有"],
  featured: true
}
```

## 5. 图片规范

- 每个物种 1 张图片，路径固定：`assets/images/animals/<id>.jpg` 或 `assets/images/plants/<id>.jpg`。
- 图片来源：iNaturalist（经其公开 API 获取，使用 large 尺寸后统一缩放到宽 ≤900px、JPEG 品质 82）。
- 每张图必须登记到 `js/image-credits.js`：

```js
window.IMAGE_CREDITS = {
  "mammal-giant-panda": { author: "xxx", license: "CC BY-NC 4.0", source: "https://www.inaturalist.org/photos/123456" },
  …
};
```

- 占位图（固定文件）：`assets/images/placeholder-animal.svg`、`assets/images/placeholder-plant.svg`，由图片组提供；前端在图片加载失败时使用。

## 6. 数据质检命令

```powershell
# 全量校验（Lead 验收用）
& "C:\Users\靳绍航\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe" scripts\validate-data.mjs
# 只校验自己负责的目标数据文件（扩编任务用）
& "C:\Users\靳绍航\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe" scripts\validate-data.mjs --file=01-mammals.js
# 只校验指定分类
& "C:\Users\靳绍航\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe" scripts\validate-data.mjs --cat=mammals,birds
```

- `--file=xxx.js` 只校验 plan 分表中“目标数据文件”等于 xxx.js 的物种（扩编任务必须用这个，互不干扰）。
- `--cat=...` 只校验指定分类（写作过程中用，不检查其它分类是否缺失）。
- 不带参数为全量校验（Lead 最终验收用）。
- `--images` 额外检查图片文件存在（图片组跑完后用）。
- 校验器会检查：必填字段、字数区间、taxonomy 五项、details/facts/tags 数量、id 与 plan 一致、重复 id、每个分类应有数量、全量时计划物种是否齐全。
- **每个数据文件写完后必须运行一次校验并修掉所有 error，再报告完成。**

## 7. 协作纪律

1. 只修改自己任务 write scope 内的文件；**不要改** `index.html`、`css/style.css`、`js/app.js`、`js/data-core.js`、`data/meta.js`、plan 文件、其他成员的数据文件。
2. 不启动服务器、不引入外部资源、不 pip/npm 安装任何东西。
3. 中文路径包含 Chinese 字符，PowerShell 调用外部 exe 时先 `cd` 到项目根目录，用相对路径。
4. 完成时：把共享任务标为 completed，并用 `send_message` 给 lead 发一条简报：完成数量、校验结果（error/warning 数）、遇到的问题（如有 plan 错误列出）。
5. 中途遇到无法解决的阻塞（API 不可用、路径错误等），立刻 `send_message` 给 lead，不要空转。
