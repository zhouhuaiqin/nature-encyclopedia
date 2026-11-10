/* 生成可被搜索引擎收录的物种静态页 + sitemap/robots + 站内搜索索引。 */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const CONFIG = JSON.parse(fs.readFileSync(path.join(ROOT, "site.config.json"), "utf8"));
const BASE = CONFIG.siteUrl.replace(/\/+$/, "");
const BUILD_DATE = new Date().toISOString().slice(0, 10);

const LICENSE_LABEL = {
  "cc0": "CC0", "pd": "公有领域", "cc-by": "CC BY", "cc-by-sa": "CC BY-SA",
  "cc-by-nc": "CC BY-NC", "cc-by-nc-sa": "CC BY-NC-SA", "unknown": "未核验",
  "arr": "版权所有", "": "未标注"
};
const RANK_CN = { kingdom: "界", phylum: "门", class: "纲", order: "目", family: "科", genus: "属" };

function esc(v) {
  return String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function paragraphs(text) {
  return String(text || "").split(/\n{2,}/).map(p => p.trim()).filter(Boolean)
    .map(p => "<p>" + esc(p) + "</p>").join("");
}

/* ---------- 载入浏览器端数据 ---------- */
const sandbox = { window: {}, console };
vm.createContext(sandbox);
function run(file) {
  vm.runInContext(fs.readFileSync(path.join(ROOT, file), "utf8"), sandbox, { filename: file });
}
run("js/data-core.js");
sandbox.registerSpecies = sandbox.window.registerSpecies;
run("data/meta.js");
const dataFiles = [];
for (const dir of ["data/animals", "data/plants"]) {
  for (const f of fs.readdirSync(path.join(ROOT, dir)).filter(f => f.endsWith(".js")).sort()) {
    dataFiles.push(dir + "/" + f);
  }
}
dataFiles.forEach(run);
run("data/relations.js");
run("js/image-credits.js");

const W = sandbox.window;
const ENC = W.ENCYCLOPEDIA;
const ALL = ENC.animals.concat(ENC.plants, ENC.fungi || []);
const CREDITS = W.IMAGE_CREDITS || {};
const REL = W.RELATIONS || { edges: [], types: {} };
const CATEGORY_MAP = W.CATEGORY_MAP || {};
const CATEGORIES = W.CATEGORIES || [];
const SITE = W.SITE || { title: "自然图鉴" };

const byId = {};
ALL.forEach(e => { byId[e.id] = e; });
const indexOf = {};
ALL.forEach((e, i) => { indexOf[e.id] = i; });
const relationsById = {};
REL.edges.forEach(edge => {
  [edge.from, edge.to].forEach(id => {
    if (!relationsById[id]) relationsById[id] = [];
    relationsById[id].push(edge);
  });
});

function speciesImage(e) {
  return "assets/images/" + (e.tab === "animals" ? "animals" : "plants") + "/" + e.id + ".webp";
}
function categoryName(e) {
  const c = CATEGORY_MAP[e.category];
  return c ? c.name : e.category || "";
}
function absolute(p) { return BASE + "/" + p.replace(/^\/+/, ""); }

function creditFor(e) {
  const c = CREDITS[e.id] || {};
  const lic = String(c.license || "unknown").toLowerCase();
  const label = LICENSE_LABEL[lic] || lic;
  const author = c.author || "未标注";
  const src = c.source || "";
  return { label, author, src, note: c.note || "" };
}

function pageHead(e, canonical, image) {
  const title = e.name + "（" + e.latin + "）— " + SITE.title + "·物种档案";
  const desc = (e.summary || "").replace(/\s+/g, " ").slice(0, 150);
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${esc(canonical)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="${esc(SITE.title)}">
<meta property="og:title" content="${esc(e.name + " · " + e.latin)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:image" content="${esc(image)}">
<meta property="og:url" content="${esc(canonical)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="../css/species.css">
<script type="application/ld+json">${JSON.stringify({
    "@context": "https://schema.org", "@type": "Taxon",
    name: e.name, alternateName: e.latin, description: e.summary,
    image: image, url: canonical,
    isPartOf: { "@type": "Collection", name: SITE.title },
    additionalType: "https://schema.org/Taxon"
  })}</script>
<script type="application/ld+json">${JSON.stringify({
    "@context": "https://schema.org", "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: SITE.title, item: BASE + "/" },
      { "@type": "ListItem", position: 2, name: categoryName(e), item: BASE + "/species/index.html" },
      { "@type": "ListItem", position: 3, name: e.name, item: canonical }
    ]
  })}</script>
</head>`;
}

function headerHtml() {
  return `<header class="site-head"><a class="brand" href="../index.html"><span class="brand-mark"></span><span>${esc(SITE.title)}</span></a>
<nav><a href="../index.html">首页</a><a href="../species/index.html">全部物种</a><a href="../search.html">搜索</a></nav></header>`;
}

function footerHtml(e) {
  const c = creditFor(e);
  return `<footer class="site-foot">
<p>图片来源：${esc(c.author)} · ${esc(c.label)}${c.src ? ' · <a href="' + esc(c.src) + '" rel="noopener nofollow">原始来源</a>' : ""}</p>
<p>${esc(c.note)} 本站为非商业学习展示；图片版权归原作者。</p>
<p><a href="../index.html">返回 ${esc(SITE.title)}</a> · <a href="../species/index.html">全部物种</a></p>
</footer>`;
}

function relHtml(e) {
  const rows = relationsById[e.id] || [];
  if (!rows.length) return "";
  const items = rows.map(edge => {
    const isFrom = edge.from === e.id;
    const otherId = isFrom ? edge.to : edge.from;
    const other = byId[otherId];
    if (!other) return "";
    const info = REL.types[edge.type] || { label: edge.type };
    return `<li><span class="rel-type">${esc(info.label)}</span> ${isFrom ? "→" : "←"}
      <a href="${esc(other.id)}.html">${esc(other.name)}</a>
      <span class="rel-note">${esc(edge.note || "")}</span></li>`;
  }).filter(Boolean);
  if (!items.length) return "";
  return `<section class="block"><h2>生态关系</h2><ul class="rel-list">${items.join("")}</ul></section>`;
}

function prevNext(e) {
  const i = indexOf[e.id];
  const prev = i > 0 ? ALL[i - 1] : null;
  const next = i >= 0 && i < ALL.length - 1 ? ALL[i + 1] : null;
  return `<nav class="prev-next">
${prev ? '<a href="' + esc(prev.id) + '.html">← ' + esc(prev.name) + "</a>" : "<span></span>"}
${next ? '<a href="' + esc(next.id) + '.html">' + esc(next.name) + " →</a>" : "<span></span>"}
</nav>`;
}

function speciesPage(e) {
  const canonical = absolute("species/" + e.id + ".html");
  const image = absolute(speciesImage(e));
  const tax = e.taxonomy || {};
  const chain = ["kingdom", "phylum", "class", "order", "family", "genus"]
    .filter(k => tax[k]).map(k => `<span><i>${RANK_CN[k]}</i>${esc(tax[k])}</span>`).join("");
  const details = (e.details || []).map(d => {
    if (d && typeof d === "object") return `<li><b>${esc(d.label || "")}</b>${esc(d.value || "")}</li>`;
    return `<li>${esc(d)}</li>`;
  }).join("");
  const facts = (e.facts || []).map(f => `<li>${esc(f)}</li>`).join("");
  const tags = (e.tags || []).map(t => `<span class="tag">${esc(t)}</span>`).join("");
  return `${pageHead(e, canonical, image)}
<body>
${headerHtml()}
<main class="species" data-pagefind-body>
  <p class="kicker">${esc(categoryName(e))} · ${esc(e.kingdom || "")}</p>
  <h1>${esc(e.name)} <span class="latin">${esc(e.latin)}</span></h1>
  <figure class="hero"><img src="../${esc(speciesImage(e))}" alt="${esc(e.name)}（${esc(e.latin)}）" width="900" height="600" loading="eager">
  <figcaption>${esc(e.name)} · ${esc(categoryName(e))}</figcaption></figure>
  <p class="summary">${esc(e.summary || "")}</p>
  <dl class="specs">
    <div><dt>分类</dt><dd>${chain}</dd></div>
    ${e.habitat ? "<div><dt>栖息环境</dt><dd>" + esc(e.habitat) + "</dd></div>" : ""}
    ${e.distribution ? "<div><dt>地理分布</dt><dd>" + esc(e.distribution) + "</dd></div>" : ""}
    ${e.conservation ? "<div><dt>保护级别</dt><dd>" + esc(e.conservation) + "</dd></div>" : ""}
  </dl>
  <section class="block"><h2>物种志</h2><div class="desc">${paragraphs(e.description)}</div></section>
  ${details ? '<section class="block"><h2>形态与习性</h2><ul class="details">' + details + "</ul></section>" : ""}
  ${facts ? '<section class="block"><h2>趣味知识</h2><ol class="facts">' + facts + "</ol></section>" : ""}
  ${relHtml(e)}
  ${tags ? '<p class="tags">' + tags + "</p>" : ""}
  ${prevNext(e)}
  <p class="back"><a href="../index.html">← 回到图鉴首页</a></p>
</main>
${footerHtml(e)}
</body>
</html>`;
}

function write(file, content) {
  const full = path.join(ROOT, file);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, content, "utf8");
}

/* ---------- 输出 ---------- */
let count = 0;
for (const e of ALL) { write("species/" + e.id + ".html", speciesPage(e)); count += 1; }

/* 全部物种索引（便于爬虫和用户浏览） */
const byCat = {};
CATEGORIES.forEach(c => { byCat[c.code] = []; });
ALL.forEach(e => { (byCat[e.category] = byCat[e.category] || []).push(e); });
const tabs = W.TABS || [];
let indexHtml = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>全部物种索引 — ${esc(SITE.title)}</title><meta name="description" content="自然图鉴全部 ${ALL.length} 个物种的索引，按类群分组。">
<link rel="canonical" href="${esc(absolute("species/index.html"))}"><link rel="stylesheet" href="../css/species.css"></head><body>
${headerHtml().replace(/\.\.\/index\.html/g, "../index.html")}
<main class="species"><h1>全部物种索引</h1><p class="summary">共 ${ALL.length} 个物种，按类群分组。也可使用<a href="../search.html">站内搜索</a>。</p>`;
tabs.forEach(tab => {
  const cats = CATEGORIES.filter(c => c.tab === tab.code);
  indexHtml += `<section class="block"><h2>${esc(tab.name)}</h2>`;
  cats.forEach(cat => {
    const list = byCat[cat.code] || [];
    if (!list.length) return;
    indexHtml += `<h3>${esc(cat.name)} <small>${list.length} 种</small></h3><ul class="species-list">`;
    indexHtml += list.map(e => `<li><a href="${esc(e.id)}.html">${esc(e.name)}</a> <em>${esc(e.latin)}</em></li>`).join("");
    indexHtml += "</ul>";
  });
  indexHtml += "</section>";
});
indexHtml += `</main><footer class="site-foot"><p><a href="../index.html">返回首页</a></p></footer></body></html>`;
write("species/index.html", indexHtml);

/* 站内搜索索引 */
const searchIndex = ALL.map(e => ({
  id: e.id, name: e.name, latin: e.latin, aliases: e.aliases || [],
  tags: e.tags || [], category: categoryName(e), tab: e.tab,
  summary: (e.summary || "").slice(0, 120), url: "species/" + e.id + ".html"
}));
write("search-index.js", "window.SEARCH_INDEX = " + JSON.stringify(searchIndex) + ";\n");

/* 搜索页（无依赖，静态可用） */
write("search.html", `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>站内搜索 — ${esc(SITE.title)}</title><meta name="description" content="搜索 ${ALL.length} 个物种：中文名、别名、学名、标签。">
<link rel="canonical" href="${esc(absolute("search.html"))}"><link rel="stylesheet" href="css/species.css"></head><body>
<header class="site-head"><a class="brand" href="index.html"><span class="brand-mark"></span><span>${esc(SITE.title)}</span></a>
<nav><a href="index.html">首页</a><a href="species/index.html">全部物种</a><a href="search.html">搜索</a></nav></header>
<main class="species"><h1>站内搜索</h1>
<p class="summary">输入中文名、别名、学名或标签；共 ${ALL.length} 个物种。</p>
<form class="search-form" onsubmit="return false"><input id="q" type="search" placeholder="例如：大熊猫 / Panthera / 高山 / 鸟类" autocomplete="off" autofocus><span id="count" class="search-count"></span></form>
<ul id="results" class="search-results"></ul>
<script src="search-index.js"></script>
<p class="back"><a href="index.html">← 回到首页</a></p></main>
<script>
(function () {
  var INDEX = window.SEARCH_INDEX || [];
  var q = document.getElementById("q");
  var out = document.getElementById("results");
  var count = document.getElementById("count");
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[c]; }); }
  function render() {
    var kw = q.value.trim().toLowerCase();
    if (!kw) { out.innerHTML = ""; count.textContent = ""; return; }
    var rows = INDEX.filter(function (e) {
      var hay = [e.name, e.latin].concat(e.aliases, e.tags, [e.category]).join(" ").toLowerCase();
      return hay.indexOf(kw) !== -1;
    }).slice(0, 60);
    count.textContent = rows.length + " 个结果";
    out.innerHTML = rows.map(function (e) {
      return '<li><a href="' + e.url + '">' + esc(e.name) + "</a> <em>" + esc(e.latin) +
        '</em><span class="tag">' + esc(e.category) + "</span><p>" + esc(e.summary) + "…</p></li>";
    }).join("");
  }
  var p = new URLSearchParams(location.search).get("q");
  if (p) { q.value = p; render(); }
  q.addEventListener("input", render);
})();
</script></body></html>`);

/* sitemap */
let urls = [`${BASE}/`, `${BASE}/species/index.html`, `${BASE}/search.html`];
ALL.forEach(e => urls.push(BASE + "/species/" + e.id + ".html"));
const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(u => `  <url><loc>${esc(u)}</loc><lastmod>${BUILD_DATE}</lastmod></url>`).join("\n")}
</urlset>`;
write("sitemap.xml", sitemap);
write("robots.txt", `User-agent: *\nAllow: /\nSitemap: ${BASE}/sitemap.xml\n`);
write(".nojekyll", "");

// 同步首页 head 中的站点地址（占位符与历史仓库地址）
const indexPath = path.join(ROOT, "index.html");
let homeHtml = fs.readFileSync(indexPath, "utf8");
if (homeHtml.includes("YOUR-USERNAME.github.io/nature-encyclopedia")) {
  homeHtml = homeHtml.split("https://YOUR-USERNAME.github.io/nature-encyclopedia").join(BASE);
}
if (homeHtml.includes("https://zhouhuaiqin.github.io/-")) {
  homeHtml = homeHtml.split("https://zhouhuaiqin.github.io/-").join(BASE);
}
fs.writeFileSync(indexPath, homeHtml, "utf8");

console.log("generated species:", count, "| total urls:", urls.length);
