# -*- coding: utf-8 -*-
"""把关系网渲染替换为以物种为中心的关系探索器。"""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "js" / "app.js"
s = p.read_text(encoding="utf-8")

start = s.index("function renderRelationGraph() {")
end = s.index("function renderModalRelations(entry) {")

new = """function renderRelationGraph() {
    if (!el.relationGraph) return;
    var all = REL.edges || [];
    if (!all.length) {
      el.relationGraph.innerHTML = '<p class="rel-empty">暂无关系数据</p>';
      if (el.relationCount) el.relationCount.textContent = "0 条关系";
      return;
    }
    var known = {};
    all.forEach(function (e) { known[e.from] = 1; known[e.to] = 1; });
    var focusId = state.relationFocus;
    if (!focusId || !known[focusId]) focusId = known["mammal-lion"] ? "mammal-lion" : Object.keys(known)[0];
    state.relationFocus = focusId;
    var focus = speciesById(focusId);
    var rows = all.filter(function (e) {
      return (e.from === focusId || e.to === focusId) &&
        (state.relationType === "all" || e.type === state.relationType);
    });
    var options = Object.keys(known).map(function (id) { return speciesById(id); })
      .filter(Boolean).sort(function (a, b) { return a.name.localeCompare(b.name, "zh"); })
      .map(function (entry) {
        return '<option value="' + escapeHtml(entry.id) + '"' + (entry.id === focusId ? " selected" : "") + ">" +
          escapeHtml(entry.name) + "</option>";
      }).join("");
    var html = '<aside class="rel-focus">' +
      '<div class="rel-focus__media">' + (focus ? '<img loading="lazy" src="' + escapeHtml(speciesImage(focus)) + '" alt="' + escapeHtml(focus.name) + '">' : "") + "</div>" +
      '<div class="rel-focus__body"><p class="rel-focus__label">ECOLOGICAL FOCUS</p>' +
      '<h3 class="rel-focus__name">' + escapeHtml(focus ? focus.name : "未知") + "</h3>" +
      '<p class="rel-focus__latin">' + escapeHtml(focus ? focus.latin : "") + "</p>" +
      '<p class="rel-focus__summary">' + escapeHtml(focus ? String(focus.summary || "").slice(0, 92) : "") + "…</p>" +
      '<div class="rel-focus__actions"><select class="rel-select" id="rel-select" aria-label="选择物种">' + options + "</select>" +
      '<button type="button" class="rel-random" id="rel-random">随机看一个</button></div></div></aside>' +
      '<div class="rel-panel"><div class="rel-panel__head"><h3>' + escapeHtml(focus ? focus.name : "") + " 的生态关系</h3>" +
      '<p>共 ' + rows.length + " 条 · 颜色=类型；→ 当前物种指向对方，← 对方指向当前物种</p></div>" +
      '<div class="rel-spokes">';
    if (!rows.length) {
      html += '<p class="rel-empty">当前筛选下没有关系，试试“全部”。</p>';
    } else {
      rows.forEach(function (e) {
        var isFrom = e.from === focusId;
        var otherId = isFrom ? e.to : e.from;
        var other = speciesById(otherId);
        if (!other) return;
        var info = REL.types[e.type] || { label: e.type, color: "#6f7a71" };
        html += '<article class="rel-card" data-rel-focus="' + escapeHtml(otherId) + '">' +
          '<div class="rel-card__media"><img loading="lazy" src="' + escapeHtml(speciesImage(other)) + '" alt="' + escapeHtml(other.name) + '"></div>' +
          '<div class="rel-card__body"><div class="rel-card__top"><span class="rel-card__name">' + escapeHtml(other.name) + "</span>" +
          '<span class="rel-type" style="background:' + info.color + '">' + escapeHtml(info.label) + "</span></div>" +
          '<p class="rel-card__dir">' + escapeHtml((isFrom ? "→ " : "← ") + other.name) + "</p>" +
          '<p class="rel-card__note">' + escapeHtml(e.note || "") + "</p>" +
          '<span class="rel-card__open" data-rel-open="' + escapeHtml(otherId) + '">查看物种详情 →</span></div></article>';
      });
    }
    html += "</div></div>";
    el.relationGraph.innerHTML = html;
    if (el.relationCount) el.relationCount.textContent = Object.keys(known).length + " 个物种 · " + all.length + " 条关系";
  }

"""
s = s[:start] + new + s[end:]

old = """  if (el.relationGraph) el.relationGraph.addEventListener("click", function (event) {
    var node = event.target.closest("[data-rel-id]");
    if (!node) return;
    openModalById(node.getAttribute("data-rel-id"));
  });"""
new2 = """  if (el.relationGraph) el.relationGraph.addEventListener("click", function (event) {
    var openBtn = event.target.closest("[data-rel-open]");
    if (openBtn) { openModalById(openBtn.getAttribute("data-rel-open")); return; }
    if (event.target.closest("#rel-random")) {
      var ids = Object.keys(REL.edges.reduce(function (m, e) { m[e.from] = 1; m[e.to] = 1; return m; }, {}));
      state.relationFocus = ids[Math.floor(Math.random() * ids.length)];
      renderRelationGraph();
      return;
    }
    var card = event.target.closest("[data-rel-focus]");
    if (card) {
      state.relationFocus = card.getAttribute("data-rel-focus");
      renderRelationGraph();
      if (el.relationGraph) el.relationGraph.scrollIntoView({ block: "nearest" });
    }
  });
  if (el.relationGraph) el.relationGraph.addEventListener("change", function (event) {
    var select = event.target.closest("#rel-select");
    if (!select) return;
    state.relationFocus = select.value;
    renderRelationGraph();
  });"""
if old in s:
    s = s.replace(old, new2)
else:
    print("listener pattern missing")

p.write_text(s, encoding="utf-8")
print("explorer renderer + listeners patched")
