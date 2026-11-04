#!/usr/bin/env node
/* ============================================================
 * 自然图鉴 · 内容质量巡检（只读，不改数据）
 * 用法：node scripts/qa-content.mjs
 * 输出：控制台报告 + plan/qa-content.json
 * ============================================================ */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sandbox = { window: {}, console: { log() {}, warn() {}, error() {} } };
vm.createContext(sandbox);
for (const rel of ["js/data-core.js", "data/meta.js"]) {
  try {
    vm.runInContext(fs.readFileSync(path.join(ROOT, rel), "utf8"), sandbox, { filename: rel });
  } catch (e) {
    console.error(`加载失败 ${rel}: ${e.message}`);
  }
}
for (const k of Object.keys(sandbox.window)) if (!(k in sandbox)) sandbox[k] = sandbox.window[k];
for (const rel of [
  ...fs
    .readdirSync(path.join(ROOT, "data/animals"))
    .filter((f) => f.endsWith(".js"))
    .sort()
    .map((f) => "data/animals/" + f),
  ...fs
    .readdirSync(path.join(ROOT, "data/plants"))
    .filter((f) => f.endsWith(".js"))
    .sort()
    .map((f) => "data/plants/" + f)
]) {
  try {
    vm.runInContext(fs.readFileSync(path.join(ROOT, rel), "utf8"), sandbox, { filename: rel });
  } catch (e) {
    console.error(`加载失败 ${rel}: ${e.message}`);
  }
}
for (const k of Object.keys(sandbox.window)) if (!(k in sandbox)) sandbox[k] = sandbox.window[k];
const store = sandbox.window.ENCYCLOPEDIA;
const all = [...store.animals, ...store.plants];
const categories = sandbox.window.CATEGORIES || [];
const catMap = new Map(categories.map((c) => [c.code, c]));
const charLen = (v) => [...String(v || "").trim()].length;

const issues = [];
const warnings = [];
const addIssue = (id, kind, detail) => issues.push({ id, kind, detail });
const addWarn = (id, kind, detail) => warnings.push({ id, kind, detail });

/* 1. 重复 summary / facts */
const summaryIndex = new Map();
const factIndex = new Map();
for (const e of all) {
  const s = String(e.summary || "").trim();
  if (summaryIndex.has(s)) addIssue(e.id, "duplicate-summary", `与 ${summaryIndex.get(s)} 的 summary 完全相同`);
  else summaryIndex.set(s, e.id);
  for (const f of e.facts || []) {
    const key = String(f).trim();
    if (factIndex.has(key)) addWarn(e.id, "duplicate-fact", `与 ${factIndex.get(key)} 重复：${key.slice(0, 30)}`);
    else factIndex.set(key, e.id);
  }
}

/* 2. 跨物种重复长句（description/facts） */
const sentenceMap = new Map();
for (const e of all) {
  const text = [e.description, ...(e.facts || [])].join("\n");
  const sentences = text
    .split(/[。！？\n]/)
    .map((s) => s.trim())
    .filter((s) => charLen(s) >= 18);
  for (const s of sentences) {
    if (!sentenceMap.has(s)) sentenceMap.set(s, new Set());
    sentenceMap.get(s).add(e.id);
  }
}
let crossCount = 0;
for (const [s, ids] of sentenceMap) {
  if (ids.size >= 2 && crossCount < 30) {
    crossCount += 1;
    addWarn("(多物种)", "shared-sentence", `${[...ids].slice(0, 3).join(",")} 共用句子：${s.slice(0, 40)}`);
  }
}

/* 3. 疑似 Markdown / HTML / 模板腔 / 半角标点 */
const badPatterns = [
  [/\*\*|__|^#{1,6}\s|<[a-z/][^>]*>|\[[^\]]*\]\([^)]*\)|`{1,3}/i, "markdown/html"],
  [/小编|我们|大家好|众所周知|希望大家/, "template-tone"],
  [/https?:\/\//i, "url-in-text"],
  [/[\u4e00-\u9fa5][,;:!?](?!\d)/, "half-width-punct"],
  [/\s{2,}/, "double-space"],
  [/[A-Za-z]{6,}/, "long-latin-run"],
];
for (const e of all) {
  const fields = { summary: e.summary, description: e.description, ...Object.fromEntries((e.facts || []).map((f, i) => ["fact" + i, f])) };
  for (const [name, value] of Object.entries(fields)) {
    for (const [re, kind] of badPatterns) {
      if (re.test(String(value || ""))) addWarn(e.id, kind, `${name}: ${String(value).slice(0, 40)}`);
    }
  }
}

/* 4. 分类与学名一致性抽查 */
const latinRe = /^[A-Z][a-z]+ (?:× )?[a-z][a-z-]+(?: [a-z][a-z.-]+){0,2}(?: '[^']+')?$/;
const latinCultivarRe = /^[A-Z][a-z]+ '[^']+'$/;
const latinOk = (v) => latinRe.test(v || "") || latinCultivarRe.test(v || "");
for (const e of all) {
  if (!latinOk(e.latin)) addWarn(e.id, "latin-format", e.latin);
  const cat = catMap.get(e.category);
  if (!cat) addIssue(e.id, "bad-category", e.category);
  else if (cat.kingdom !== e.kingdom) addIssue(e.id, "kingdom-mismatch", `${e.kingdom} vs ${cat.kingdom}`);
  for (const rank of ["phylum", "class", "order", "family", "genus"]) {
    const v = (e.taxonomy || {})[rank];
    if (!v || /未知|不详|待定|None|null/.test(v)) addWarn(e.id, "taxonomy-placeholder", `${rank}=${v}`);
  }
}

/* 5. conservation 格式分布 */
const conservationKinds = new Map();
for (const e of all) {
  const c = String(e.conservation || "");
  let kind = "other";
  if (/^IUCN/.test(c)) kind = "IUCN";
  else if (/^暂无评估/.test(c)) kind = "暂无评估";
  else if (/^CITES/.test(c)) kind = "CITES";
  conservationKinds.set(kind, (conservationKinds.get(kind) || 0) + 1);
  if (kind === "other" && charLen(c) < 4) addWarn(e.id, "conservation-empty", c);
}

/* 6. details label 分布 & 异常 */
const labelCount = new Map();
for (const e of all) {
  for (const d of e.details || []) {
    labelCount.set(d.label, (labelCount.get(d.label) || 0) + 1);
    if (!d.label || !d.value) addIssue(e.id, "details-empty", JSON.stringify(d));
  }
}

/* 7. 长度统计 */
const stats = {
  description: { min: 9999, max: 0, avg: 0, sample: "" },
  summary: { min: 9999, max: 0, avg: 0 },
  facts: { count: 0 },
};
let sumD = 0;
let sumS = 0;
for (const e of all) {
  const dl = charLen(e.description);
  const sl = charLen(e.summary);
  sumD += dl;
  sumS += sl;
  if (dl < stats.description.min) {
    stats.description.min = dl;
    stats.description.sample = e.id;
  }
  if (dl > stats.description.max) stats.description.max = dl;
  stats.summary.min = Math.min(stats.summary.min, sl);
  stats.summary.max = Math.max(stats.summary.max, sl);
  stats.facts.count += (e.facts || []).length;
}
stats.description.avg = Math.round(sumD / all.length);
stats.summary.avg = Math.round(sumS / all.length);
stats.facts.avg = +(stats.facts.count / all.length).toFixed(1);

/* 8. 每个分类字段覆盖 */
const missingFields = [];
for (const e of all) {
  for (const f of ["summary", "description", "habitat", "distribution", "conservation", "aliases", "taxonomy", "details", "facts", "tags"]) {
    if (e[f] === undefined || e[f] === null || e[f] === "") missingFields.push({ id: e.id, field: f });
  }
}

/* ---------- 输出 ---------- */
const report = {
  total: all.length,
  categories: Object.fromEntries(
    categories.map((c) => [c.code, all.filter((e) => e.category === c.code).length])
  ),
  lengthStats: stats,
  conservationKinds: Object.fromEntries(conservationKinds),
  issues,
  warnings: warnings.slice(0, 120),
  warningCount: warnings.length,
  detailLabels: [...labelCount.entries()].sort((a, b) => b[1] - a[1]).slice(0, 40),
  missingFields,
};
fs.writeFileSync(path.join(ROOT, "plan/qa-content.json"), JSON.stringify(report, null, 2), "utf8");

console.log(`\n物种总数：${all.length}`);
console.log("分类数量：" + JSON.stringify(report.categories));
console.log(
  `描述长度：avg ${stats.description.avg}（min ${stats.description.min} @${stats.description.sample}，max ${stats.description.max}）；` +
    `摘要长度：avg ${stats.summary.avg}（min ${stats.summary.min} / max ${stats.summary.max}）；facts 均 ${stats.facts.avg} 条`
);
console.log("保护等级写法：" + JSON.stringify(report.conservationKinds));
console.log(`\n问题 ${issues.length} 条${issues.length ? "：" : ""}`);
issues.slice(0, 30).forEach((i) => console.log(`  ✗ [${i.kind}] ${i.id}：${i.detail}`));
console.log(`\n提示 ${warnings.length} 条（展示前 30）：`);
warnings.slice(0, 30).forEach((i) => console.log(`  ⚠ [${i.kind}] ${i.id}：${i.detail}`));
console.log(`\n常见 details 标签：${report.detailLabels.slice(0, 18).map(([k, v]) => k + "×" + v).join("、")}`);
if (missingFields.length) console.log(`缺失字段 ${missingFields.length} 处`);
