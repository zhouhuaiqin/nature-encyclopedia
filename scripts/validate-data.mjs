#!/usr/bin/env node
/* ============================================================
 * 自然图鉴 · 数据质检
 * 用法：
 *   node scripts/validate-data.mjs                       全量校验
 *   node scripts/validate-data.mjs --cat=mammals,birds   只校验指定分类
 *   node scripts/validate-data.mjs --file=06b-insects-extra.js  只校验某个目标数据文件（扩编任务用）
 *   node scripts/validate-data.mjs --images              额外校验图片与版权
 * ============================================================ */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const getArg = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : null;
};
const catEq = args.find((a) => a.startsWith("--cat="));
const catArg = catEq ? catEq.slice("--cat=".length) : getArg("--cat");
const filter = catArg
  ? catArg.split(",").map((s) => s.trim()).filter(Boolean)
  : null;
const fileEq = args.find((a) => a.startsWith("--file="));
const fileArg = fileEq ? fileEq.slice("--file=".length) : getArg("--file");
const checkImages = args.includes("--images");

const errors = [];
const warnings = [];
const err = (m) => errors.push(m);
const warn = (m) => warnings.push(m);
const charLen = (v) => (typeof v === "string" ? [...v.trim()].length : 0);
const isStr = (v, min = 1) => typeof v === "string" && [...v.trim()].length >= min;

/* ---------- 沙箱加载 ---------- */
const sandbox = { window: {}, console: { log() {}, warn() {}, error() {} } };
vm.createContext(sandbox);

function loadJS(rel) {
  const abs = path.join(ROOT, rel);
  if (!fs.existsSync(abs)) {
    err(`文件不存在：${rel}`);
    return false;
  }
  try {
    vm.runInContext(fs.readFileSync(abs, "utf8"), sandbox, { filename: rel });
    return true;
  } catch (e) {
    err(`执行失败 ${rel}：${e.message}`);
    return false;
  }
}

loadJS("js/data-core.js");
loadJS("data/meta.js");

// 让 window.xxx 同时成为沙箱全局变量（浏览器里两者等价）
for (const k of Object.keys(sandbox.window)) {
  if (!(k in sandbox)) sandbox[k] = sandbox.window[k];
}

const categories = new Map(
  (sandbox.window.CATEGORIES || []).map((c) => [c.code, c])
);
if (!categories.size) err("data/meta.js 中未找到 CATEGORIES");

/* ---------- 计划表（plan/species*.json：原始总表 + 扩编分表） ---------- */
const planDir = path.join(ROOT, "plan");
const planFiles = fs.existsSync(planDir)
  ? fs.readdirSync(planDir).filter((n) => /^species.*\.json$/.test(n)).sort()
  : [];
if (!planFiles.length) err("plan/ 下未找到 species*.json 物种总表");
const plans = {};
const planById = new Map();
for (const file of planFiles) {
  try {
    const json = JSON.parse(fs.readFileSync(path.join(planDir, file), "utf8"));
    const tab = json.tab;
    if (tab !== "animals" && tab !== "plants") {
      err(`计划文件 tab 非法：${file}`);
      continue;
    }
    const rows = (json.species || []).map((row) => ({
      id: row[0],
      name: row[1],
      latin: row[2],
      category: row[3],
      file: row[4] || ""
    }));
    plans[tab] = (plans[tab] || []).concat(rows);
    for (const row of rows) {
      if (planById.has(row.id)) err(`重复计划物种 id：${row.id}（${file}）`);
      planById.set(row.id, row);
    }
  } catch (e) {
    err(`计划文件解析失败 ${file}：${e.message}`);
  }
}

/* ---------- 数据文件 ---------- */
const dataFiles = [];
for (const dir of ["data/animals", "data/plants"]) {
  const abs = path.join(ROOT, dir);
  if (!fs.existsSync(abs)) continue;
  for (const f of fs.readdirSync(abs).filter((n) => n.endsWith(".js")).sort()) {
    dataFiles.push(`${dir}/${f}`);
  }
}
if (!dataFiles.length) err("未发现任何数据文件（data/animals、data/plants）");
dataFiles.forEach(loadJS);

const store = sandbox.window.ENCYCLOPEDIA || { animals: [], plants: [] };
const all = [...store.animals, ...store.plants];
const byId = new Map(all.map((e) => [e.id, e]));

/* ---------- 图片版权表 ---------- */
let credits = {};
if (fs.existsSync(path.join(ROOT, "js/image-credits.js"))) {
  loadJS("js/image-credits.js");
  credits = sandbox.window.IMAGE_CREDITS || {};
} else if (checkImages) {
  warn("js/image-credits.js 尚不存在（图片组未完成时可忽略）");
}

const active = (categoryCode) => !filter || filter.includes(categoryCode);

/* ---------- 单条校验 ---------- */
const ID_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
/* 学名：双名法；允许亚种第三词（如 Haliotis discus hannai）；允许杂交种符号 ×；允许栽培品种 */
const LATIN_RE = /^[A-Z][a-z]+ (?:× )?[a-z][a-z-]+(?: [a-z][a-z.-]+){0,2}(?: '[^']+')?$/;
const LATIN_CULTIVAR_RE = /^[A-Z][a-z]+ '[^']+'$/;
const latinOk = (v) => LATIN_RE.test(v || "") || LATIN_CULTIVAR_RE.test(v || "");

function validateEntry(e) {
  const tag = e.id || "(无 id)";
  const cat = categories.get(e.category);
  if (!cat) {
    err(`${tag}：未知分类代码 ${e.category}`);
    return;
  }
  if (!ID_RE.test(e.id)) err(`${tag}：id 格式不合法`);
  if (e.kingdom !== cat.kingdom)
    err(`${tag}：kingdom 应为「${cat.kingdom}」，实际「${e.kingdom}」`);
  if (!latinOk(e.latin))
    err(`${tag}：latin 格式异常「${e.latin}」`);
  if (charLen(e.summary) < 35 || charLen(e.summary) > 130)
    err(`${tag}：summary 长度 ${charLen(e.summary)}，要求 45–110 字`);
  const dlen = charLen(e.description);
  if (dlen < 200 || dlen > 900)
    err(`${tag}：description 长度 ${dlen}，要求 260–450 字`);
  if (dlen >= 200 && !String(e.description).includes("\n\n"))
    warn(`${tag}：description 未分段（建议两段，\n\n 分隔）`);
  if (!isStr(e.habitat, 6)) err(`${tag}：habitat 过短`);
  if (!isStr(e.distribution, 5)) err(`${tag}：distribution 过短`);
  if (!isStr(e.conservation, 2)) warn(`${tag}：conservation 为空`);
  if (!Array.isArray(e.aliases)) err(`${tag}：aliases 必须是数组`);
  const tx = e.taxonomy || {};
  for (const rank of ["phylum", "class", "order", "family", "genus"]) {
    if (!isStr(tx[rank], 1)) err(`${tag}：taxonomy.${rank} 缺失`);
  }
  if (!Array.isArray(e.details) || e.details.length < 5 || e.details.length > 10)
    err(`${tag}：details 需 5–8 项，实际 ${Array.isArray(e.details) ? e.details.length : "非数组"}`);
  else
    e.details.forEach((d, i) => {
      if (!d || !isStr(d.label) || !isStr(d.value))
        err(`${tag}：details[${i}] 缺少 label/value`);
      else if (charLen(d.value) > 90) warn(`${tag}：details[${i}].value 过长`);
    });
  if (!Array.isArray(e.facts) || e.facts.length < 3 || e.facts.length > 6)
    err(`${tag}：facts 需 3–5 条，实际 ${Array.isArray(e.facts) ? e.facts.length : "非数组"}`);
  else
    e.facts.forEach((f, i) => {
      if (!isStr(f, 8)) err(`${tag}：facts[${i}] 过短或非字符串`);
    });
  if (!Array.isArray(e.tags) || e.tags.length < 3 || e.tags.length > 8)
    err(`${tag}：tags 需 3–6 个，实际 ${Array.isArray(e.tags) ? e.tags.length : "非数组"}`);
  else
    e.tags.forEach((t, i) => {
      if (!isStr(t, 1) || charLen(t) > 10) err(`${tag}：tags[${i}] 不合法`);
    });
  if (e.featured !== undefined && typeof e.featured !== "boolean")
    err(`${tag}：featured 必须是布尔值`);

  /* 计划表一致性 */
  const plan = planById.get(e.id);
  if (!plan) {
    err(`${tag}：不在 plan 物种总表中（新增物种须先经 Lead 同意）`);
  } else {
    if (plan.name !== e.name) err(`${tag}：name 与 plan 不一致（plan=${plan.name}，实际=${e.name}）`);
    if (plan.category !== e.category)
      err(`${tag}：category 与 plan 不一致（plan=${plan.category}）`);
    if (plan.latin.toLowerCase().replace(/\s+/g, " ") !== String(e.latin).toLowerCase().replace(/\s+/g, " "))
      warn(`${tag}：latin 与 plan 不一致（plan=${plan.latin}，实际=${e.latin}）`);
  }

  /* 图片 */
  if (checkImages) {
    const imgRel = `assets/images/${e.tab}/${e.id}.webp`;
    const imgAbs = path.join(ROOT, imgRel);
    if (!fs.existsSync(imgAbs)) err(`${tag}：图片缺失 ${imgRel}`);
    else if (fs.statSync(imgAbs).size < 4000) err(`${tag}：图片过小 ${imgRel}`);
    if (!credits[e.id]) warn(`${tag}：缺少图片版权登记`);
    else if (!isStr(credits[e.id].source)) warn(`${tag}：版权登记缺少 source`);
  }
}

/* ---------- 执行校验 ---------- */
let planSubset;
if (fileArg) {
  planSubset = [...planById.values()].filter((row) => row.file === fileArg);
  if (!planSubset.length) err(`--file=${fileArg} 在计划表中没有对应物种（检查文件名拼写）`);
} else {
  planSubset = [...planById.values()].filter((row) => active(row.category));
}
const subsetIds = new Set(planSubset.map((row) => row.id));
const checkedIds = new Set();
for (const e of all) {
  if (fileArg) {
    if (!subsetIds.has(e.id)) continue;
  } else if (!active(e.category)) {
    continue;
  }
  if (checkedIds.has(e.id)) err(`${e.id}：出现重复 id`);
  checkedIds.add(e.id);
  validateEntry(e);
}

/* 计划内但实际缺失 */
for (const row of planSubset) {
  if (!byId.has(row.id)) err(`缺失物种：${row.id}（${row.name} / ${row.category}）`);
}
/* 数量统计 */
const countPool = fileArg
  ? all.filter((e) => subsetIds.has(e.id))
  : all.filter((e) => active(e.category));
const counts = new Map();
for (const e of countPool) {
  counts.set(e.category, (counts.get(e.category) || 0) + 1);
}
const planCounts = new Map();
for (const row of planSubset) {
  planCounts.set(row.category, (planCounts.get(row.category) || 0) + 1);
}

/* ---------- 输出 ---------- */
const activeCodes = fileArg
  ? [...new Set([...planCounts.keys(), ...counts.keys()])].sort()
  : filter || [...categories.keys()];
if (fileArg) {
  console.log(`\n目标文件：${fileArg}（计划 ${planSubset.length} 个物种）`);
} else {
  console.log("\n分类统计（已写入 / 计划）：");
}
for (const code of activeCodes) {
  const cat = categories.get(code);
  const a = counts.get(code) || 0;
  const p = planCounts.get(code) || 0;
  const mark = a === p ? "OK " : "!! ";
  console.log(`  ${mark}${String(code).padEnd(20)} ${String(a).padStart(3)} / ${String(p).padStart(3)}  ${cat ? cat.name : ""}`);
}
let totalA = 0;
let totalP = 0;
for (const code of activeCodes) {
  totalA += counts.get(code) || 0;
  totalP += planCounts.get(code) || 0;
}
console.log(`  ${totalA === totalP ? "OK " : "!! "}${"合计".padEnd(18)} ${String(totalA).padStart(3)} / ${String(totalP).padStart(3)}`);

if (warnings.length) {
  console.log(`\n警告 ${warnings.length} 条：`);
  warnings.slice(0, 40).forEach((w) => console.log("  ⚠ " + w));
  if (warnings.length > 40) console.log(`  … 还有 ${warnings.length - 40} 条`);
}
if (errors.length) {
  console.log(`\n错误 ${errors.length} 条：`);
  errors.slice(0, 80).forEach((e) => console.log("  ✗ " + e));
  if (errors.length > 80) console.log(`  … 还有 ${errors.length - 80} 条`);
  console.log("\n校验未通过。");
  process.exit(1);
}
console.log("\n✅ 校验通过。");
process.exit(0);
