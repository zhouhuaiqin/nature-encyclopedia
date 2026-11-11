/* 生成首屏轻量索引 data/index.js 与按类群的详情包 data/details/<category>.js */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const sandbox = { window: {}, console };
vm.createContext(sandbox);
function run(file) {
  vm.runInContext(fs.readFileSync(path.join(ROOT, file), "utf8"), sandbox, { filename: file });
}
run("js/data-core.js");
sandbox.registerSpecies = sandbox.window.registerSpecies;
run("data/meta.js");
const files = [];
for (const dir of ["data/animals", "data/plants"]) {
  for (const f of fs.readdirSync(path.join(ROOT, dir)).filter(f => f.endsWith(".js")).sort()) {
    files.push(dir + "/" + f);
  }
}
files.forEach(run);
const ENC = sandbox.window.ENCYCLOPEDIA;
const ALL = ENC.animals.concat(ENC.plants, ENC.fungi || []);
const baseFields = ["id", "name", "latin", "kingdom", "category", "aliases", "tags", "summary", "taxonomy"];
const detailFields = ["description", "habitat", "distribution", "conservation", "details", "facts"];
const byTab = { animals: [], plants: [], fungi: [] };
const byCat = {};
for (const e of ALL) {
  const base = {};
  for (const k of baseFields) if (e[k] !== undefined) base[k] = e[k];
  byTab[e.tab].push(base);
  const detail = {};
  for (const k of detailFields) if (e[k] !== undefined) detail[k] = e[k];
  (byCat[e.category] = byCat[e.category] || {})[e.id] = detail;
}
let index = "/* 首屏轻量索引（由 build_index.cjs 生成） */\n";
for (const tab of ["animals", "plants", "fungi"]) {
  index += "registerSpecies(" + JSON.stringify(tab) + ", " + JSON.stringify(byTab[tab]) + ");\n";
}
fs.writeFileSync(path.join(ROOT, "data/index.js"), index, "utf8");
fs.mkdirSync(path.join(ROOT, "data/details"), { recursive: true });
for (const [cat, map] of Object.entries(byCat)) {
  const js = "/* 详情包（由 build_index.cjs 生成） */\nwindow.registerDetails(" +
    JSON.stringify(cat) + ", " + JSON.stringify(map) + ");\n";
  fs.writeFileSync(path.join(ROOT, "data/details", cat + ".js"), js, "utf8");
}
console.log("species:", ALL.length, "| index MB:", (fs.statSync(path.join(ROOT, "data/index.js")).size / 1048576).toFixed(2), "| details:", Object.keys(byCat).length);
