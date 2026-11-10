/* ==========================================================================
   自然图鉴 · 应用逻辑 v3.0（原生 JS，无依赖）
   数据来源：window.ENCYCLOPEDIA（js/data-core.js 注册）、window.CATEGORIES
   ========================================================================== */
(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  var ENC = window.ENCYCLOPEDIA || { animals: [], plants: [] };
  var SITE = window.SITE || { title: "自然图鉴", subtitle: "动植物百科图典" };
  var TABS = window.TABS || [
    { code: "animals", name: "动物界" },
    { code: "plants", name: "植物界" },
    { code: "fungi", name: "菌物界" }
  ];
  var CATEGORIES = window.CATEGORIES || [];
  var CATEGORY_MAP = window.CATEGORY_MAP || {};
  var TABS_MAP = {};
  TABS.forEach(function (t) { TABS_MAP[t.code] = t; });
  var ORDER = {};
  CATEGORIES.forEach(function (c, i) { ORDER[c.code] = i; });

  var ALL = ENC.animals.concat(ENC.plants, ENC.fungi || []);
  var COUNTS_BY_TAB = { animals: ENC.animals.length, plants: ENC.plants.length, fungi: (ENC.fungi || []).length };
  var BASE_INDEX = {};
  ALL.forEach(function (entry, i) { BASE_INDEX[entry.id] = i; });
  var COUNTS_BY_CATEGORY = countBy(ALL, function (e) { return e.category; });
  var FAMILY_SET = {};
  ALL.forEach(function (e) {
    var f = (e.taxonomy || {}).family;
    if (f) FAMILY_SET[f] = true;
  });

  var RANKS = ["kingdom", "phylum", "class", "order", "family"];
  var RANK_CN = { kingdom: "界", phylum: "门", class: "纲", order: "目", family: "科" };

  var BATCH_SIZE = window.matchMedia && window.matchMedia("(max-width: 700px)").matches ? 48 : 96;
  var DEBUG = new URLSearchParams(location.search || "").get("debug") === "1";
  var state = {
    tab: "animals",
    category: null,
    orderFilter: null,
    taxonFilter: null,
    query: "",
    searchScope: "all",
    relationType: "all",
    limit: BATCH_SIZE
  };
  var currentList = [];
  var lastFocused = null;
  var searchTimer = null;

  /* ---------- helpers ---------- */
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function norm(v) { return String(v == null ? "" : v).toLowerCase().replace(/[\s·・,，、;；]/g, ""); }
  function countBy(list, keyFn) {
    var map = {};
    list.forEach(function (item) { var k = keyFn(item); map[k] = (map[k] || 0) + 1; });
    return map;
  }
  function paragraphs(text) {
    return String(text || "").split(/\n{2,}/).map(function (p) { return p.trim(); })
      .filter(Boolean).map(function (p) { return "<p>" + escapeHtml(p) + "</p>"; }).join("");
  }
  function speciesById(id) {
    for (var i = 0; i < ALL.length; i += 1) { if (ALL[i].id === id) return ALL[i]; }
    return null;
  }
  function imageOf(entry) {
    return typeof window.speciesImage === "function" ? window.speciesImage(entry)
      : "assets/images/" + (entry.tab === "animals" ? "animals" : "plants") + "/" + entry.id + ".webp";
  }
  function thumbOf(entry) {
    return "assets/thumbs/" + (entry.tab === "animals" ? "animals" : "plants") + "/" + entry.id + ".webp";
  }
  function placeholderOf(entry) {
    return typeof window.speciesPlaceholder === "function" ? window.speciesPlaceholder(entry)
      : "assets/images/placeholder-" + (entry.tab === "animals" ? "animal" : "plant") + ".svg";
  }
  function categoryOf(entry) { return CATEGORY_MAP[entry.category] || { name: entry.category || "", icon: "" }; }
  function highlight(text, query) {
    var safe = escapeHtml(text);
    var q = String(query || "").trim();
    if (!q) return safe;
    try {
      var re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
      return safe.replace(re, "<mark>$1</mark>");
    } catch (err) { return safe; }
  }
  function uniq(list) {
    var seen = {}, out = [];
    list.forEach(function (v) { if (!seen[v]) { seen[v] = true; out.push(v); } });
    return out;
  }

  /* ---------- taxonomy tree ---------- */
  function buildTree() {
    var root = {};
    ALL.forEach(function (entry) {
      var tx = entry.taxonomy || {};
      var levels = [entry.kingdom || "动物界", tx.phylum || "未分类门", tx.class || "未分类纲", tx.order || "未分类目", tx.family || "未分类科"];
      var cur = root;
      levels.forEach(function (name, i) {
        if (!cur[name]) cur[name] = { name: name, level: i, count: 0, children: {}, tab: entry.tab };
        cur[name].count += 1;
        cur[name].tab = cur[name].tab || entry.tab;
        cur = cur[name].children;
      });
    });
    return root;
  }
  var TREE = buildTree();
  var treeSel = null;

  /* ---------- filtering ---------- */
  function matchScore(entry, query) {
    var nq = norm(query);
    if (!nq) return 0;
    var name = norm(entry.name), latin = norm(entry.latin), cat = categoryOf(entry);
    if (name === nq || latin === nq) return 120;
    if (name.indexOf(nq) === 0) return 110;
    if (name.indexOf(nq) > -1) return 95;
    var aliases = (entry.aliases || []).map(norm);
    if (aliases.some(function (a) { return a === nq; })) return 90;
    if (aliases.some(function (a) { return a.indexOf(nq) > -1; })) return 75;
    if (latin.indexOf(nq) > -1) return 70;
    var tags = (entry.tags || []).map(norm);
    if (tags.some(function (t) { return t.indexOf(nq) > -1; })) return 55;
    if (norm(cat.name).indexOf(nq) > -1) return 40;
    if (norm(entry.summary).indexOf(nq) > -1) return 25;
    return 0;
  }
  function matchTaxon(entry, taxonFilter) {
    if (!taxonFilter) return true;
    var value = taxonFilter.name;
    if (taxonFilter.level === 0) return entry.kingdom === value;
    return (entry.taxonomy || {})[RANKS[taxonFilter.level]] === value;
  }
  function sortByBase(list) {
    return list.slice().sort(function (a, b) {
      var oa = ORDER[a.category] == null ? 999 : ORDER[a.category];
      var ob = ORDER[b.category] == null ? 999 : ORDER[b.category];
      if (oa !== ob) return oa - ob;
      return (BASE_INDEX[a.id] || 0) - (BASE_INDEX[b.id] || 0);
    });
  }
  function computeList() {
    var query = state.query.trim();
    var pool;
    if (query) {
      pool = ALL.filter(function (e) {
        if (state.searchScope !== "all" && e.tab !== state.searchScope) return false;
        if (!matchTaxon(e, state.taxonFilter)) return false;
        return matchScore(e, query) > 0;
      });
      pool.sort(function (a, b) {
        var d = matchScore(b, query) - matchScore(a, query);
        if (d !== 0) return d;
        return (ORDER[a.category] || 0) - (ORDER[b.category] || 0);
      });
      return pool;
    }
    pool = ALL.filter(function (e) {
      if (e.tab !== state.tab) return false;
      if (state.category && e.category !== state.category) return false;
      if (state.orderFilter && (e.taxonomy || {}).order !== state.orderFilter) return false;
      if (!matchTaxon(e, state.taxonFilter)) return false;
      return true;
    });
    return sortByBase(pool);
  }

  /* ---------- DOM ---------- */
  var el = {
    topbar: $("#topbar"),
    navs: $$("[data-nav]"),
    searchInput: $("#search-input"),
    searchClear: $("#search-clear"),
    heroIntro: $("#hero-intro"),
    statTotal: $("#stat-total"),
    statAnimals: $("#stat-animals"),
    statPlants: $("#stat-plants"),
    statFungi: $("#stat-fungi"),
    statFamilies: $("#stat-families"),
    coverGallery: $("#cover-gallery"),
    categoryGrid: $("#category-grid"),
    featuredTrack: $("#featured-track"),
    categoryChips: $("#category-chips"),
    subchipsRow: $("#subchips-row"),
    subcategoryChips: $("#subcategory-chips"),
    resultCount: $("#result-count"),
    activeFilters: $("#active-filters"),
    resetFilters: $("#reset-filters"),
    browseTitle: $("#browse-title"),
    sectionDesc: $("#section-desc"),
    grid: $("#species-grid"),
    moreWrap: $("#more-wrap"),
    loadMore: $("#load-more"),
    moreInfo: $("#more-info"),
    empty: $("#empty-state"),
    emptyReset: $("#empty-reset"),
    gridFoot: $("#grid-foot-text"),
    footerYear: $("#footer-year"),
    footStats: $("#foot-stats"),
    toTop: $("#to-top"),
    scrollProgress: $("#scroll-progress"),
    randomBtn: $("#random-species"),
    randomHero: $("#random-hero"),
    dailyCard: $("#daily-card"),
    dailyDate: $("#daily-date"),
    starMap: $("#star-map"),
    relationGraph: $("#relation-graph"),
    relationChips: $("#relation-chips"),
    relationCount: $("#relation-count"),
    relationLegend: $("#relation-legend"),
    modalRelations: $("#modal-relations"),
    modalRelationsSection: $("#modal-relations-section"),
    featuredPrev: $("#featured-prev"),
    featuredNext: $("#featured-next"),
    taxonOpeners: $$("#nav-tree, #open-taxonomy, #foot-taxonomy"),
    taxonOverlay: $("#taxon-overlay"),
    taxonTree: $("#taxon-tree"),
    taxonPath: $("#taxon-path"),
    taxonCount: $("#taxon-count"),
    taxonApply: $("#taxon-apply"),
    taxonClear: $("#taxon-clear"),
    taxonClose: $("#taxon-close"),
    modal: $("#modal"),
    modalPanel: $(".modal__panel"),
    modalScroll: $("#modal-scroll"),
    modalClose: $("#modal-close"),
    modalImage: $("#modal-image"),
    modalBadge: $("#modal-badge"),
    modalCredit: $("#modal-credit"),
    modalKicker: $("#modal-kicker"),
    modalTitle: $("#modal-title"),
    modalLatin: $("#modal-latin"),
    modalAliases: $("#modal-aliases"),
    modalSummary: $("#modal-summary"),
    modalSpecs: $("#modal-specs"),
    modalDesc: $("#modal-desc"),
    modalTaxonomy: $("#modal-taxonomy"),
    modalFacts: $("#modal-facts"),
    modalTags: $("#modal-tags"),
    modalPrev: $("#modal-prev"),
    modalPrevName: $("#modal-prev-name"),
    modalNext: $("#modal-next"),
    modalNextName: $("#modal-next-name"),
    modalIndex: $("#modal-index")
  };

  /* ---------- cover & counters ---------- */
  function animateNumber(node, target) {
    if (!node) return;
    var start = performance.now();
    var from = 0;
    var dur = 900;
    function tick(now) {
      var p = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      node.textContent = Math.round(from + (target - from) * eased);
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  function renderStats() {
    var total = ALL.length;
    var families = Object.keys(FAMILY_SET).length;
    if (DEBUG) {
      [el.statTotal, el.statAnimals, el.statPlants, el.statFungi, el.statFamilies].forEach(function (node, i) {
        if (node) node.textContent = [total, COUNTS_BY_TAB.animals, COUNTS_BY_TAB.plants, COUNTS_BY_TAB.fungi, families][i];
      });
    } else {
      animateNumber(el.statTotal, total);
      animateNumber(el.statAnimals, COUNTS_BY_TAB.animals);
      animateNumber(el.statPlants, COUNTS_BY_TAB.plants);
      animateNumber(el.statFungi, COUNTS_BY_TAB.fungi);
      animateNumber(el.statFamilies, families);
    }
    if (el.heroIntro && SITE.intro) el.heroIntro.textContent = SITE.intro;
    el.footerYear.textContent = new Date().getFullYear();
    if (el.footStats) {
      el.footStats.textContent = total + " 物种 / " + CATEGORIES.filter(function (c) { return COUNTS_BY_CATEGORY[c.code]; }).length + " 分类 / " + families + " 科";
    }
  }

  function featuredEntries() {
    var ids = window.FEATURED || [];
    var list = [];
    ids.forEach(function (id) { var e = speciesById(id); if (e) list.push(e); });
    if (!list.length) list = ALL.slice(0, 8);
    return list;
  }

  function renderCover() {
    if (!el.coverGallery) return;
    var feats = featuredEntries();
    var picks = [feats[0], feats[1], feats[2], feats[3]].filter(Boolean);
    var cls = ["cover-figure cover-figure--main", "cover-figure cover-figure--a", "cover-figure cover-figure--b", "cover-figure cover-figure--c"];
    var html = picks.map(function (e, i) {
      return '<figure class="' + cls[i] + '">' +
        '<img src="' + escapeHtml(imageOf(e)) + '" alt="' + escapeHtml(e.name) + '" loading="eager" decoding="async">' +
        '<figcaption><span class="cf-name">' + escapeHtml(e.name) + '</span>' +
        '<span class="cf-latin">' + escapeHtml(e.latin) + '</span></figcaption></figure>';
    }).join("");
    html += '<div class="cover-seal">EST.<br>2026<br>VOL.03</div>';
    el.coverGallery.innerHTML = html;
  }

  function renderCategoryGrid() {
    if (!el.categoryGrid) return;
    var covers = window.CATEGORY_COVERS || {};
    var html = CATEGORIES.map(function (cat) {
      var count = COUNTS_BY_CATEGORY[cat.code] || 0;
      if (!count) return "";
      var coverEntry = speciesById(covers[cat.code]) || ALL.filter(function (e) { return e.category === cat.code; })[0];
      var orders = orderFacets(cat.code).slice(0, 3).map(function (o) { return o.name; }).join(" · ");
      return '<button type="button" class="cat-card" data-cat="' + escapeHtml(cat.code) + '">' +
        '<img src="' + escapeHtml(coverEntry ? imageOf(coverEntry) : "") + '" alt="' + escapeHtml(cat.name) + '" loading="lazy" decoding="async">' +
        '<span class="cat-card__body">' +
          '<span class="cat-card__top"><span class="cat-card__name">' + escapeHtml(cat.name) + '</span>' +
          '<span class="cat-card__count">' + count + ' 种</span></span>' +
          '<span class="cat-card__en">' + escapeHtml(cat.code.replace(/-/g, " ")) + '</span>' +
          '<span class="cat-card__sub">' + escapeHtml(orders || cat.blurb || "") + '</span>' +
        '</span></button>';
    }).join("");
    el.categoryGrid.innerHTML = html;
  }

  function renderFeatured() {
    if (!el.featuredTrack) return;
    var html = featuredEntries().map(function (e, i) {
      var cat = categoryOf(e);
      return '<button type="button" class="feat-card" data-id="' + escapeHtml(e.id) + '">' +
        '<span class="feat-card__num">' + String(i + 1).padStart(2, "0") + '</span>' +
        '<span class="feat-card__img"><img src="' + escapeHtml(thumbOf(e)) + '" alt="' + escapeHtml(e.name) + '" loading="lazy" decoding="async"></span>' +
        '<span class="feat-card__body"><span class="feat-card__name">' + escapeHtml(e.name) + '</span>' +
        '<span class="feat-card__latin">' + escapeHtml(e.latin) + '</span>' +
        '<span class="feat-card__cat">' + escapeHtml(cat.name) + '</span></span></button>';
    }).join("");
    el.featuredTrack.innerHTML = html;
  }

  /* ---------- 今日物种 / 分类星图 / 随机漫游 ---------- */
  function pad2(n) { return String(n).padStart(2, "0"); }

  function dailyEntry() {
    var d = new Date();
    var seed = d.getFullYear() * 400 + (d.getMonth() + 1) * 31 + d.getDate();
    var ids = (window.FEATURED || []).concat(Object.values(window.CATEGORY_COVERS || {}));
    var pool = [];
    ids.forEach(function (id) {
      if (!id || pool.some(function (x) { return x.id === id; })) return;
      var e = speciesById(id);
      if (e) pool.push(e);
    });
    if (!pool.length) pool = ALL;
    return pool[seed % pool.length];
  }

  function renderDaily() {
    if (!el.dailyCard) return;
    var e = dailyEntry();
    if (!e) return;
    var cat = categoryOf(e);
    var idx = ALL.findIndex(function (x) { return x.id === e.id; });
    el.dailyCard.href = "#/species/" + encodeURIComponent(e.id);
    el.dailyCard.innerHTML =
      '<span class="daily-card__media"><img src="' + escapeHtml(imageOf(e)) + '" alt="' + escapeHtml(e.name) + '" loading="eager" decoding="async">' +
      '<span class="daily-card__num">' + String(idx + 1).padStart(4, "0") + " / " + ALL.length + "</span></span>" +
      '<span class="daily-card__body">' +
      '<span class="daily-card__kicker">' + escapeHtml(cat.name) + " · " + escapeHtml((e.taxonomy || {}).order || "") + "</span>" +
      '<span class="daily-card__name">' + escapeHtml(e.name) + "</span>" +
      '<span class="daily-card__latin">' + escapeHtml(e.latin) + "</span>" +
      '<span class="daily-card__text">' + escapeHtml(e.summary || "") + "</span>" +
      '<span class="daily-card__go">查看今日物种 →</span></span>';
    el.dailyCard.onclick = function (ev) {
      ev.preventDefault();
      openModalById(e.id);
    };
    if (el.dailyDate) {
      var d = new Date();
      var start = new Date(d.getFullYear(), 0, 0);
      var day = Math.floor((d - start) / 86400000);
      el.dailyDate.textContent = d.getFullYear() + "." + pad2(d.getMonth() + 1) + "." + pad2(d.getDate()) + " · 第 " + day + " 天";
    }
  }

  function renderStarMap() {
    if (!el.starMap) return;
    var covers = window.CATEGORY_COVERS || {};
    var items = CATEGORIES.filter(function (c) { return COUNTS_BY_CATEGORY[c.code]; })
      .map(function (c) { return { cat: c, count: COUNTS_BY_CATEGORY[c.code] }; })
      .sort(function (a, b) { return b.count - a.count; });
    if (!items.length) return;
    var max = items[0].count;
    var html = '<svg class="star-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">';
    var pts = [];
    var cols = 6;
    items.forEach(function (it, i) {
      var col = i % cols;
      var row = Math.floor(i / cols);
      var jx = ((i * 37) % 7 - 3) * 0.9;
      var jy = ((i * 53) % 5 - 2) * 1.2;
      var x = 9 + col * 16.5 + jx;
      var y = 24 + row * 29 + jy;
      pts.push({ x: x, y: y });
    });
    for (var k = 1; k < pts.length; k += 1) {
      html += '<line x1="' + pts[k - 1].x.toFixed(2) + '" y1="' + pts[k - 1].y.toFixed(2) +
        '" x2="' + pts[k].x.toFixed(2) + '" y2="' + pts[k].y.toFixed(2) + '" />';
    }
    html += "</svg>";
    items.forEach(function (it, i) {
      var d = Math.round(54 + 74 * Math.sqrt(it.count / max));
      var cover = speciesById(covers[it.cat.code]) || ALL.filter(function (e) { return e.category === it.cat.code; })[0];
      var img = cover ? thumbOf(cover) : "";
      html += '<button type="button" class="star-node' + (it.count >= 200 ? " star-node--big" : "") +
        '" data-cat="' + escapeHtml(it.cat.code) + '" style="left:' + pts[i].x.toFixed(2) + "%;top:" + pts[i].y.toFixed(2) + '%;">' +
        '<span class="star-node__disc" style="width:' + d + "px;height:" + d + 'px;">' +
        '<img src="' + escapeHtml(img) + '" alt="' + escapeHtml(it.cat.name) + '" loading="' + (DEBUG ? "eager" : "lazy") + '" decoding="async">' +
        '<span class="star-node__count">' + it.count + "</span></span>" +
        '<span class="star-node__label">' + escapeHtml(it.cat.name) + "</span></button>";
    });
    html += '<span class="star-legend">圆面积 ∝ 物种数 · 点击进入</span>';
    el.starMap.innerHTML = html;
  }

  function randomSpecies() {
    if (!ALL.length) return;
    var e = ALL[Math.floor(Math.random() * ALL.length)];
    state.tab = e.tab;
    state.category = e.category;
    state.orderFilter = null;
    state.taxonFilter = null;
    state.query = "";
    state.searchScope = "all";
    if (el.searchInput) el.searchInput.value = "";
    if (el.searchClear) el.searchClear.hidden = true;
    renderAll();
    openModalById(e.id);
  }

  /* ---------- 生态关系网 ---------- */
  var REL = window.RELATIONS || { edges: [], types: {} };
  var REL_COLORS = ["#2f5d3a", "#a9714b", "#3d6f8e", "#7a4b8f", "#b07a45", "#c9a227", "#6f7a71", "#a34a2a"];

  function relationEdges() {
    return (REL.edges || []).filter(function (e) {
      return state.relationType === "all" || e.type === state.relationType;
    });
  }

  function renderRelationChips() {
    if (!el.relationChips) return;
    var edges = REL.edges || [];
    var counts = {};
    edges.forEach(function (e) { counts[e.type] = (counts[e.type] || 0) + 1; });
    var types = Object.keys(REL.types || {}).filter(function (t) { return counts[t]; });
    var html = '<button type="button" class="chip' + (state.relationType === "all" ? " is-active" : "") +
      '" data-rel-type="all">全部<span class="chip__count">' + edges.length + "</span></button>";
    types.forEach(function (t) {
      var info = REL.types[t] || { label: t, color: "#6f7a71" };
      html += '<button type="button" class="chip' + (state.relationType === t ? " is-active" : "") +
        '" data-rel-type="' + t + '"><span class="chip__icon" style="color:' + info.color + '">●</span>' +
        escapeHtml(info.label) + '<span class="chip__count">' + counts[t] + "</span></button>";
    });
    el.relationChips.innerHTML = html;
    if (el.relationLegend) {
      el.relationLegend.innerHTML = types.map(function (t) {
        var info = REL.types[t] || { label: t, color: "#6f7a71" };
        return "<span><i style=\"background:" + info.color + "\"></i>" + escapeHtml(info.label) + "</span>";
      }).join("") + "<span>线越密，说明该物种与其他物种的生态联系越多</span>";
    }
  }

  function renderRelationGraph() {
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
      '<div class="rel-focus__media">' + (focus ? '<img loading="lazy" src="' + escapeHtml(thumbOf(focus)) + '" alt="' + escapeHtml(focus.name) + '">' : "") + "</div>" +
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
          '<div class="rel-card__media"><img loading="lazy" src="' + escapeHtml(thumbOf(other)) + '" alt="' + escapeHtml(other.name) + '"></div>' +
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

function renderModalRelations(entry) {
    if (!el.modalRelations || !el.modalRelationsSection) return;
    var rows = (REL.edges || []).filter(function (e) { return e.from === entry.id || e.to === entry.id; });
    if (!rows.length) {
      el.modalRelationsSection.hidden = true;
      return;
    }
    el.modalRelationsSection.hidden = false;
    el.modalRelations.innerHTML = rows.map(function (e) {
      var isFrom = e.from === entry.id;
      var otherId = isFrom ? e.to : e.from;
      var other = speciesById(otherId);
      var info = REL.types[e.type] || { label: e.type, color: "#6f7a71" };
      return '<li><span class="rel-type" style="background:' + info.color + '">' + escapeHtml(info.label) +
        "</span><span>" + (isFrom ? "→ " : "← ") + '<a class="rel-other" href="#/species/' +
        encodeURIComponent(otherId) + '" data-rel-id="' + escapeHtml(otherId) + '">' +
        escapeHtml(other ? other.name : otherId) + "</a></span>" +
        '<span class="rel-note">' + escapeHtml(e.note || "") + "</span></li>";
    }).join("");
  }

  function orderFacets(categoryCode) {
    var counts = {};
    ALL.forEach(function (e) {
      if (e.category !== categoryCode) return;
      var order = (e.taxonomy || {}).order;
      if (!order) return;
      counts[order] = (counts[order] || 0) + 1;
    });
    return Object.keys(counts).map(function (name) { return { name: name, count: counts[name] }; })
      .sort(function (a, b) { return b.count - a.count; });
  }

  /* ---------- chips ---------- */
  function createChip(opts) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = opts.className || "chip" + (opts.active ? " is-active" : "");
    if (opts.key) btn.setAttribute("data-chip", opts.key);
    btn.innerHTML =
      (opts.icon ? '<span class="chip__icon">' + opts.icon + "</span>" : "") +
      "<span>" + escapeHtml(opts.label) + "</span>" +
      (opts.count == null ? "" : '<span class="chip__count">' + opts.count + "</span>");
    return btn;
  }

  function renderChips() {
    if (!el.categoryChips) return;
    var frag = document.createDocumentFragment();
    var query = state.query.trim();
    if (query) {
      var matches = ALL.filter(function (e) {
        if (!matchTaxon(e, state.taxonFilter)) return false;
        return matchScore(e, query) > 0;
      });
      var counts = countBy(matches, function (e) { return e.tab; });
      frag.appendChild(createChip({ key: "scope:all", label: "全部结果", icon: "⌕", count: matches.length, active: state.searchScope === "all" }));
      TABS.forEach(function (tab) {
        frag.appendChild(createChip({ key: "scope:" + tab.code, label: tab.name, icon: tab.icon || "", count: counts[tab.code] || 0, active: state.searchScope === tab.code }));
      });
    } else {
      frag.appendChild(createChip({ key: "cat:all", label: "全部类群", icon: "✳", count: COUNTS_BY_TAB[state.tab] || 0, active: !state.category }));
      CATEGORIES.filter(function (c) { return c.tab === state.tab && COUNTS_BY_CATEGORY[c.code]; }).forEach(function (cat) {
        frag.appendChild(createChip({ key: "cat:" + cat.code, label: cat.name, icon: cat.icon || "", count: COUNTS_BY_CATEGORY[cat.code] || 0, active: state.category === cat.code }));
      });
    }
    el.categoryChips.innerHTML = "";
    el.categoryChips.appendChild(frag);
  }

  function renderSubchips() {
    if (!el.subchipsRow || !el.subcategoryChips) return;
    if (!state.category) {
      el.subchipsRow.hidden = true;
      return;
    }
    var facets = orderFacets(state.category);
    if (facets.length < 2) {
      el.subchipsRow.hidden = true;
      return;
    }
    el.subchipsRow.hidden = false;
    el.subcategoryChips.innerHTML = "";
    var allBtn = createChip({ key: "order:all", label: "全部目", count: COUNTS_BY_CATEGORY[state.category] || 0, active: !state.orderFilter, className: "chip chip--sub" + (state.orderFilter ? "" : " is-active") });
    el.subcategoryChips.appendChild(allBtn);
    facets.forEach(function (f) {
      el.subcategoryChips.appendChild(createChip({
        key: "order:" + f.name,
        label: f.name,
        count: f.count,
        active: state.orderFilter === f.name,
        className: "chip chip--sub" + (state.orderFilter === f.name ? " is-active" : "")
      }));
    });
  }

  function renderActiveFilters() {
    if (!el.activeFilters) return;
    var pills = [];
    if (state.taxonFilter) {
      pills.push('<span class="filter-pill"><b>' + escapeHtml(state.taxonFilter.path.join(" · ")) + '</b><button type="button" data-clear="taxon" aria-label="清除分类树筛选"><span>×</span></button></span>');
    }
    if (state.orderFilter) {
      pills.push('<span class="filter-pill"><b>' + escapeHtml(state.orderFilter) + '</b><button type="button" data-clear="order" aria-label="清除目筛选"><span>×</span></button></span>');
    }
    el.activeFilters.innerHTML = pills.join("");
    el.activeFilters.hidden = pills.length === 0;
  }

  /* ---------- heads ---------- */
  function renderHead() {
    var query = state.query.trim();
    if (query) {
      el.browseTitle.textContent = "搜索：“" + query + "”";
      el.sectionDesc.textContent = "在全站 18 个类群、数百个科中检索中文名、别名、学名与标签；可按动物界 / 植物与菌物缩小范围。";
      return;
    }
    var tab = TABS_MAP[state.tab] || { name: "动物界", blurb: "" };
    if (state.category) {
      var cat = CATEGORY_MAP[state.category];
      el.browseTitle.textContent = cat.name;
      var facets = orderFacets(state.category);
      el.sectionDesc.textContent = (cat.blurb || "") + (facets.length ? "　本类含 " + facets.length + " 个目：" + facets.slice(0, 4).map(function (f) { return f.name; }).join("、") + (facets.length > 4 ? " 等" : "") + "。" : "");
    } else if (state.taxonFilter) {
      el.browseTitle.textContent = state.taxonFilter.path[state.taxonFilter.path.length - 1];
      el.sectionDesc.textContent = "分类树筛选：" + state.taxonFilter.path.join(" → ");
    } else {
      el.browseTitle.textContent = tab.name + " · 全部类群";
      el.sectionDesc.textContent = tab.blurb || "";
    }
  }

  function renderResultCount(list) {
    if (!el.resultCount) return;
    var query = state.query.trim();
    if (query) el.resultCount.innerHTML = "找到 <b>" + list.length + "</b> 个物种";
    else if (state.category || state.taxonFilter) el.resultCount.innerHTML = "本类 <b>" + list.length + "</b> 个物种";
    else el.resultCount.innerHTML = "共 <b>" + list.length + "</b> 个物种";
  }

  /* ---------- cards ---------- */
  function cardHtml(entry, index) {
    var cat = categoryOf(entry);
    var query = state.query.trim();
    var tags = (entry.tags || []).slice(0, 3).map(function (t) {
      return '<span class="card__tagmini">' + escapeHtml(t) + "</span>";
    }).join("");
    return (
      '<a class="card" href="#/species/' + encodeURIComponent(entry.id) + '" data-id="' + escapeHtml(entry.id) + '" aria-label="查看 ' + escapeHtml(entry.name) + ' 的详情">' +
        '<div class="card__media">' +
          '<span class="card__index">' + String(index + 1).padStart(2, "0") + "</span>" +
          '<img class="card__img" src="' + escapeHtml(thumbOf(entry)) + '" alt="' + escapeHtml(entry.name) + "（" + escapeHtml(entry.latin) + "）" + '" loading="lazy" decoding="async">' +
          '<span class="card__tag">' + escapeHtml(cat.name) + "</span>" +
        "</div>" +
        '<div class="card__body">' +
          '<h3 class="card__name">' + highlight(entry.name, query) + "</h3>" +
          '<p class="card__latin">' + highlight(entry.latin, query) + "</p>" +
          '<p class="card__summary">' + escapeHtml(entry.summary) + "</p>" +
          '<div class="card__foot">' + tags + '<span class="card__arrow" aria-hidden="true">→</span></div>' +
        "</div>" +
      "</a>"
    );
  }

  function bindCardImages(root) {
    $$(".card__img", root || el.grid).forEach(function (img) {
      if (img.dataset.bound) return;
      img.dataset.bound = "1";
      if (DEBUG) img.loading = "eager";
      if (img.complete && img.naturalWidth) { img.classList.add("is-loaded"); return; }
      img.addEventListener("load", function () { img.classList.add("is-loaded"); });
      img.addEventListener("error", function () {
        var card = img.closest(".card");
        var entry = card ? speciesById(card.getAttribute("data-id")) : null;
        if (entry && img.getAttribute("data-fallback") !== "1") {
          img.setAttribute("data-fallback", "1");
          img.src = placeholderOf(entry);
        } else { img.style.display = "none"; }
      });
    });
  }

  function appendCards(start, end) {
    var frag = document.createDocumentFragment();
    for (var i = start; i < end; i += 1) {
      var entry = currentList[i];
      if (!entry) break;
      var template = document.createElement("template");
      template.innerHTML = cardHtml(entry, i).trim();
      frag.appendChild(template.content.firstChild);
    }
    bindCardImages(frag);
    el.grid.appendChild(frag);
  }

  function updateMore() {
    if (!el.moreWrap) return;
    var remaining = currentList.length - state.limit;
    if (remaining > 0) {
      el.moreWrap.hidden = false;
      el.moreInfo.textContent = "已显示 " + state.limit + " / " + currentList.length + " 个物种";
      el.loadMore.textContent = "显示更多（还有 " + remaining + " 个）";
    } else { el.moreWrap.hidden = true; }
  }

  function renderGrid() {
    var list = computeList();
    currentList = list;
    state.limit = Math.min(BATCH_SIZE, list.length);
    el.grid.innerHTML = "";
    appendCards(0, state.limit);
    updateMore();
    el.empty.hidden = list.length > 0;
    el.grid.hidden = list.length === 0;
    renderResultCount(list);
    if (list.length && !state.query.trim()) el.gridFoot.textContent = "已收录 " + list.length + " 个物种 · 点击卡片查看完整档案";
    else if (list.length) el.gridFoot.textContent = "搜索 “" + state.query.trim() + "” · 点击卡片查看完整档案";
    else el.gridFoot.textContent = "没有匹配结果";
  }

  function renderAll() {
    renderNav();
    renderChips();
    renderSubchips();
    renderActiveFilters();
    renderHead();
    renderGrid();
  }

  function renderNav() {
    el.navs.forEach(function (btn) {
      btn.classList.toggle("is-active", !state.query && btn.getAttribute("data-nav") === state.tab);
    });
  }

  /* ---------- taxonomy overlay ---------- */
  function renderTree() {
    var html = "";
    function renderNode(node, parentPath) {
      var path = parentPath.concat(node.name);
      var level = node.level;
      var childNames = Object.keys(node.children).sort(function (a, b) { return node.children[b].count - node.children[a].count; });
      var out = "";
      if (level < RANKS.length - 1 && childNames.length) {
        var open = level <= 1 ? " open" : "";
        out += '<details class="tnode" data-level="' + RANKS[level] + '"' + open + ">" +
          '<summary><span>' + escapeHtml(node.name) + '</span>' +
          '<span class="tnode__en">' + escapeHtml(RANK_CN[RANKS[level]]) + "</span>" +
          '<span class="tnode__count">' + node.count + "</span></summary>" +
          '<div class="tnode__children">';
        out += '<button type="button" class="taxon-leaf" data-level="' + level + '" data-name="' + escapeHtml(node.name) + '" data-path="' + escapeHtml(path.join("|")) + '" data-count="' + node.count + '">' +
          '<span class="rank">全部</span><span>本' + RANK_CN[RANKS[level]] + '全部物种</span><span class="count">' + node.count + "</span></button>";
        childNames.forEach(function (name) { out += renderNode(node.children[name], path); });
        out += "</div></details>";
      } else {
        out += '<button type="button" class="taxon-leaf" data-level="4" data-name="' + escapeHtml(node.name) + '" data-path="' + escapeHtml(path.join("|")) + '" data-count="' + node.count + '">' +
          '<span class="rank">科</span><span>' + escapeHtml(node.name) + '</span><span class="count">' + node.count + "</span></button>";
      }
      return out;
    }
    Object.keys(TREE).forEach(function (kingdomName) {
      html += renderNode(TREE[kingdomName], []);
    });
    el.taxonTree.innerHTML = html;
  }

  function updateTreeSelection() {
    if (!treeSel) {
      el.taxonPath.textContent = "尚未选择";
      el.taxonCount.textContent = "共 " + ALL.length + " 个物种";
      el.taxonApply.disabled = true;
      el.taxonClear.disabled = true;
      return;
    }
    el.taxonPath.textContent = treeSel.path.join(" → ");
    el.taxonCount.textContent = "包含 " + treeSel.count + " 个物种";
    el.taxonApply.disabled = false;
    el.taxonClear.disabled = false;
  }

  function openTaxonomy() {
    el.taxonOverlay.hidden = false;
    document.body.classList.add("has-modal");
    renderTree();
    updateTreeSelection();
    el.taxonClose.focus({ preventScroll: true });
  }
  function closeTaxonomy() {
    el.taxonOverlay.hidden = true;
    if (!modalOpen) document.body.classList.remove("has-modal");
    if (!modalOpen) history.replaceState(null, "", viewHash());
  }
  function applyTreeSel() {
    if (!treeSel) return;
    state.taxonFilter = { level: treeSel.level, name: treeSel.name, path: treeSel.path.slice() };
    state.query = "";
    el.searchInput.value = "";
    el.searchClear.hidden = true;
    var match = ALL.filter(function (e) {
      if (!matchTaxon(e, state.taxonFilter)) return false;
      return true;
    })[0];
    if (match) { state.tab = match.tab; state.category = null; state.orderFilter = null; }
    closeTaxonomy();
    renderAll();
    document.getElementById("browse").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ---------- modal ---------- */
  var LICENSE_URL = {
    cc0: "https://creativecommons.org/publicdomain/zero/1.0/",
    pd: "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc-by-nc": "https://creativecommons.org/licenses/by-nc/4.0/",
    "cc-by-nc-sa": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "cc-by-nc-nd": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    "cc-by-nd": "https://creativecommons.org/licenses/by-nd/4.0/"
  };
  function formatLicense(code) {
    if (!code || code === "all rights reserved") return "版权所有";
    var raw = String(code).toLowerCase();
    if (/^cc0$/i.test(raw) || raw === "pd") return "CC0 / 公有领域";
    return "CC " + raw.replace(/^cc-?/i, "").replace(/-/g, " ").toUpperCase();
  }
  function licenseLink(code, label) {
    var url = LICENSE_URL[String(code || "").toLowerCase()];
    if (!url) return escapeHtml(label);
    return '<a href="' + url + '" target="_blank" rel="noopener noreferrer license">' + escapeHtml(label) + "</a>";
  }
  function cleanAuthor(attribution) {
    var s = String(attribution || "").trim();
    if (!s) return "";
    var uploaded = s.match(/uploaded by\s+([^,()]+)/i);
    if (uploaded) return uploaded[1].trim();
    s = s.replace(/^\(c\)\s*/i, "").replace(/,?\s*some rights reserved[^)]*\)?/i, "")
      .replace(/,?\s*uploaded by.*$/i, "").replace(/\s*\(?CC[^)]*\)?/i, "");
    return s.replace(/[,;]+$/, "").trim();
  }
  function creditHtml(entry) {
    var credits = window.IMAGE_CREDITS || {};
    var rec = credits[entry.id];
    var fallback = "图片来源：本站自绘占位图（公共领域）· 暂无合适的可商用授权照片";
    if (!rec) return fallback;
    var source = rec.source ? '<a href="' + escapeHtml(rec.source) + '" target="_blank" rel="noopener noreferrer">iNaturalist</a>' : "iNaturalist";
    var bits = [];
    var author = cleanAuthor(rec.author);
    if (author) bits.push("摄影 " + escapeHtml(author.slice(0, 60)));
    bits.push("许可：" + licenseLink(rec.license, formatLicense(rec.license)));
    if (rec.note && /可商用|同属/.test(rec.note)) bits.push(escapeHtml(rec.note));
    return "图片来源：" + source + " · " + bits.join(" · ");
  }
  function taxonomyChain(entry) {
    var t = entry.taxonomy || {};
    var rows = [["界", entry.kingdom], ["门", t.phylum], ["纲", t.class], ["目", t.order], ["科", t.family], ["属", t.genus]];
    return rows.filter(function (r) { return r[1]; }).map(function (r) {
      return '<li><span class="rank">' + r[0] + '</span><span class="value">' + escapeHtml(r[1]) + "</span></li>";
    }).join("");
  }
  function fillModal(entry) {
    var cat = categoryOf(entry);
    el.modalImage.classList.remove("is-loaded");
    el.modalImage.onload = function () { el.modalImage.classList.add("is-loaded"); };
    el.modalImage.onerror = function () {
      el.modalImage.onerror = null;
      el.modalImage.src = placeholderOf(entry);
      el.modalImage.classList.add("is-loaded");
    };
    el.modalImage.src = imageOf(entry);
    el.modalImage.alt = entry.name + "（" + entry.latin + "）";
    el.modalBadge.textContent = cat.icon ? cat.icon + " " + cat.name : cat.name;
    el.modalCredit.innerHTML = creditHtml(entry);
    el.modalKicker.textContent = (entry.kingdom || "") + " · " + cat.name + " · " + ((entry.taxonomy || {}).order || "");
    el.modalTitle.textContent = entry.name;
    el.modalLatin.textContent = entry.latin;
    var aliases = entry.aliases || [];
    el.modalAliases.textContent = aliases.length ? "别名： " + aliases.join(" · ") : "";
    el.modalAliases.hidden = aliases.length === 0;
    el.modalSummary.textContent = entry.summary || "";
    var specs = (entry.details || []).slice();
    if (entry.habitat) specs.push({ label: "栖息环境", value: entry.habitat });
    if (entry.distribution) specs.push({ label: "地理分布", value: entry.distribution });
    if (entry.conservation) specs.push({ label: "保护级别", value: entry.conservation });
    el.modalSpecs.innerHTML = specs.map(function (d) {
      return '<div class="detail__spec"><dt>' + escapeHtml(d.label) + "</dt><dd>" + escapeHtml(d.value) + "</dd></div>";
    }).join("");
    el.modalDesc.innerHTML = paragraphs(entry.description);
    el.modalTaxonomy.innerHTML = taxonomyChain(entry);
    el.modalFacts.innerHTML = (entry.facts || []).map(function (f) { return "<li>" + escapeHtml(f) + "</li>"; }).join("");
    el.modalTags.innerHTML = (entry.tags || []).map(function (t) { return "<li>" + escapeHtml(t) + "</li>"; }).join("");
    renderModalRelations(entry);
    var idx = currentList.findIndex(function (x) { return x.id === entry.id; });
    var prev = idx > 0 ? currentList[idx - 1] : null;
    var next = idx > -1 && idx < currentList.length - 1 ? currentList[idx + 1] : null;
    el.modalPrev.disabled = !prev;
    el.modalPrevName.textContent = prev ? prev.name : "已经是第一个";
    el.modalNext.disabled = !next;
    el.modalNextName.textContent = next ? next.name : "已经是最后一个";
    el.modalIndex.textContent = idx > -1 ? String(idx + 1).padStart(2, "0") + " / " + String(currentList.length).padStart(2, "0") : "—";
    el.modalPrev.dataset.id = prev ? prev.id : "";
    el.modalNext.dataset.id = next ? next.id : "";
    el.modalScroll.scrollTop = 0;
  }
  var modalOpen = false;
  function openModalById(id, opts) {
    var entry = speciesById(id);
    if (!entry) return false;
    if (!modalOpen) lastFocused = document.activeElement;
    fillModal(entry);
    el.modal.hidden = false;
    document.body.classList.add("has-modal");
    modalOpen = true;
    document.title = entry.name + " · " + (SITE.title || "自然图鉴");
    if (!opts || opts.updateHash !== false) {
      var target = "#/species/" + encodeURIComponent(entry.id);
      if (location.hash !== target) {
        if (opts && opts.replace) history.replaceState(null, "", target);
        else location.hash = target;
      }
    }
    if (el.modalPanel && el.modalPanel.focus) el.modalPanel.focus({ preventScroll: true });
    return true;
  }
  function closeModal(updateHash) {
    if (!modalOpen) return;
    el.modal.hidden = true;
    modalOpen = false;
    if (!el.taxonOverlay || el.taxonOverlay.hidden) document.body.classList.remove("has-modal");
    document.title = (SITE.title || "自然图鉴") + " · " + (SITE.subtitle || "动植物百科图典");
    if (updateHash) history.replaceState(null, "", viewHash());
    if (lastFocused && lastFocused.focus) { try { lastFocused.focus({ preventScroll: true }); } catch (e) { /* noop */ } }
  }
  function stepModal(dir) {
    if (!modalOpen) return;
    var id = dir < 0 ? el.modalPrev.dataset.id : el.modalNext.dataset.id;
    if (!id) return;
    var entry = speciesById(id);
    if (!entry) return;
    fillModal(entry);
    history.replaceState(null, "", "#/species/" + encodeURIComponent(entry.id));
    document.title = entry.name + " · " + (SITE.title || "自然图鉴");
  }

  /* ---------- hash routing ---------- */
  function viewHash() { return state.category ? "#/category/" + state.category : "#/" + state.tab; }
  function parseHash() {
    var raw = (location.hash || "").replace(/^#/, "");
    raw = decodeURIComponent(raw || "");
    if (!raw || raw === "/") return { view: "home" };
    if (raw === "/tree") return { view: "tree" };
    if (raw === "/animals" || raw === "/plants" || raw === "/fungi") return { view: "tab", tab: raw.slice(1) };
    var catMatch = raw.match(/^\/category\/([a-z0-9-]+)$/);
    if (catMatch && CATEGORY_MAP[catMatch[1]]) return { view: "category", code: catMatch[1] };
    var spMatch = raw.match(/^\/species\/([a-z0-9-]+)$/);
    if (spMatch) return { view: "species", id: spMatch[1] };
    return { view: "home" };
  }
  function applyHash() {
    var route = parseHash();
    if (route.view === "tree") {
      renderAll();
      openTaxonomy();
      return;
    }
    if (route.view === "species") {
      var deep = speciesById(route.id);
      var inList = deep && currentList.some(function (x) { return x.id === route.id; });
      if (!inList && deep) {
        state.tab = deep.tab; state.category = null; state.query = ""; state.orderFilter = null;
        state.searchScope = "all"; el.searchInput.value = ""; el.searchClear.hidden = true;
        renderAll();
      } else if (!inList) renderAll();
      openModalById(route.id, { updateHash: false });
      return;
    }
    closeModal(false);
    if (route.view === "tab") {
      state.tab = route.tab; state.category = null; state.orderFilter = null;
      state.query = ""; state.searchScope = "all"; el.searchInput.value = ""; el.searchClear.hidden = true;
    } else if (route.view === "category") {
      var cat = CATEGORY_MAP[route.code];
      state.tab = cat.tab; state.category = route.code; state.orderFilter = null;
      state.query = ""; state.searchScope = "all"; el.searchInput.value = ""; el.searchClear.hidden = true;
    } else {
      state.tab = "animals"; state.category = null; state.orderFilter = null;
    }
    renderAll();
  }

  function setView(tab, category) {
    state.tab = tab; state.category = category; state.orderFilter = null; state.taxonFilter = null;
    state.query = ""; state.searchScope = "all"; el.searchInput.value = ""; el.searchClear.hidden = true;
    var hash = category ? "#/category/" + category : "#/" + tab;
    if (location.hash === hash) renderAll();
    else location.hash = hash;
  }
  function scrollBrowse() { document.getElementById("browse").scrollIntoView({ behavior: "smooth", block: "start" }); }

  /* ---------- events ---------- */
  el.navs.forEach(function (btn) {
    btn.addEventListener("click", function () { setView(btn.getAttribute("data-nav"), null); scrollBrowse(); });
  });
  el.categoryChips.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-chip]");
    if (!btn) return;
    var key = btn.getAttribute("data-chip");
    if (key.indexOf("scope:") === 0) { state.searchScope = key.slice(6); renderChips(); renderGrid(); return; }
    if (key === "cat:all") { setView(state.tab, null); return; }
    if (key.indexOf("cat:") === 0) setView(state.tab, key.slice(4));
  });
  el.subcategoryChips.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-chip]");
    if (!btn) return;
    var key = btn.getAttribute("data-chip");
    state.orderFilter = key === "order:all" ? null : key.slice(6);
    renderAll();
  });
  el.activeFilters.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-clear]");
    if (!btn) return;
    if (btn.getAttribute("data-clear") === "taxon") state.taxonFilter = null;
    else state.orderFilter = null;
    renderAll();
  });
  el.resetFilters.addEventListener("click", function () {
    state.taxonFilter = null; state.orderFilter = null;
    setView(state.tab, null);
  });
  el.emptyReset.addEventListener("click", function () {
    state.taxonFilter = null; state.orderFilter = null;
    setView("animals", null); el.searchInput.focus();
  });
  el.categoryGrid.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-cat]");
    if (!btn) return;
    var code = btn.getAttribute("data-cat");
    var cat = CATEGORY_MAP[code];
    if (!cat) return;
    setView(cat.tab, code);
    scrollBrowse();
  });
  el.featuredTrack.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-id]");
    if (btn) openModalById(btn.getAttribute("data-id"));
  });
  el.loadMore.addEventListener("click", function () {
    var start = state.limit;
    var end = Math.min(currentList.length, state.limit + BATCH_SIZE);
    state.limit = end;
    appendCards(start, end);
    updateMore();
  });
  function onSearchInput() {
    state.query = el.searchInput.value;
    state.searchScope = "all";
    el.searchClear.hidden = !state.query;
    renderNav(); renderChips(); renderHead(); renderGrid();
  }
  el.searchInput.addEventListener("input", function () {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(onSearchInput, 130);
  });
  el.searchInput.addEventListener("keydown", function (event) {
    if (event.key === "Escape") { el.searchInput.value = ""; onSearchInput(); el.searchInput.blur(); }
    if (event.key === "Enter") {
      if (searchTimer) clearTimeout(searchTimer);
      onSearchInput();
      scrollBrowse();
    }
  });
  el.searchClear.addEventListener("click", function () { el.searchInput.value = ""; onSearchInput(); el.searchInput.focus(); });

  document.addEventListener("keydown", function (event) {
    var tag = (event.target.tagName || "").toLowerCase();
    var typing = tag === "input" || tag === "textarea" || event.target.isContentEditable;
    if (event.key === "/" && !typing && !modalOpen && el.taxonOverlay.hidden) {
      event.preventDefault(); el.searchInput.focus(); el.searchInput.select(); return;
    }
    if (event.key === "Escape") {
      if (!el.taxonOverlay.hidden) { event.preventDefault(); closeTaxonomy(); return; }
      if (modalOpen) { event.preventDefault(); closeModal(true); }
      return;
    }
    if (modalOpen && !typing) {
      if (event.key === "ArrowLeft") { event.preventDefault(); stepModal(-1); }
      else if (event.key === "ArrowRight") { event.preventDefault(); stepModal(1); }
    }
  });

  el.grid.addEventListener("click", function (event) {
    var card = event.target.closest(".card");
    if (!card) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    openModalById(card.getAttribute("data-id"));
  });
  el.modalClose.addEventListener("click", function () { closeModal(true); });
  $(".modal__backdrop").addEventListener("click", function () { closeModal(true); });
  el.modalPrev.addEventListener("click", function () { stepModal(-1); });
  el.modalNext.addEventListener("click", function () { stepModal(1); });

  el.taxonOpeners.forEach(function (btn) { btn.addEventListener("click", openTaxonomy); });
  el.taxonClose.addEventListener("click", closeTaxonomy);
  el.taxonOverlay.addEventListener("click", function (event) {
    if (event.target === el.taxonOverlay) closeTaxonomy();
  });
  el.taxonTree.addEventListener("click", function (event) {
    var leaf = event.target.closest(".taxon-leaf");
    if (!leaf) return;
    var path = (leaf.getAttribute("data-path") || "").split("|").filter(Boolean);
    treeSel = {
      level: parseInt(leaf.getAttribute("data-level"), 10) || 4,
      name: leaf.getAttribute("data-name"),
      count: parseInt(leaf.getAttribute("data-count"), 10) || 0,
      path: path
    };
    $$(".taxon-leaf", el.taxonTree).forEach(function (n) { n.classList.remove("is-selected"); });
    leaf.classList.add("is-selected");
    updateTreeSelection();
  });
  el.taxonApply.addEventListener("click", applyTreeSel);
  el.taxonClear.addEventListener("click", function () {
    treeSel = null;
    $$(".taxon-leaf", el.taxonTree).forEach(function (n) { n.classList.remove("is-selected"); });
    updateTreeSelection();
  });

  window.addEventListener("hashchange", applyHash);

  function onScroll() {
    var y = window.scrollY || window.pageYOffset;
    el.topbar.classList.toggle("is-scrolled", y > 8);
    el.toTop.hidden = y < 620;
    if (el.scrollProgress) {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var p = max > 0 ? Math.min(1, y / max) : 0;
      el.scrollProgress.style.width = (p * 100).toFixed(2) + "%";
    }
    if (el.coverGallery) {
      var off = Math.min(y, 900) * 0.06;
      el.coverGallery.style.transform = off > 0.5 ? "translate3d(0," + off.toFixed(1) + "px,0)" : "";
    }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  el.toTop.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });

  if (el.randomBtn) el.randomBtn.addEventListener("click", randomSpecies);
  if (el.randomHero) el.randomHero.addEventListener("click", randomSpecies);
  if (el.featuredPrev) el.featuredPrev.addEventListener("click", function () {
    el.featuredTrack.scrollBy({ left: -360, behavior: "smooth" });
  });
  if (el.featuredNext) el.featuredNext.addEventListener("click", function () {
    el.featuredTrack.scrollBy({ left: 360, behavior: "smooth" });
  });
  if (el.starMap) el.starMap.addEventListener("click", function (event) {
    var node = event.target.closest("[data-cat]");
    if (!node) return;
    var cat = CATEGORY_MAP[node.getAttribute("data-cat")];
    if (!cat) return;
    setView(cat.tab, cat.code);
    scrollBrowse();
  });
  if (el.relationChips) el.relationChips.addEventListener("click", function (event) {
    var chip = event.target.closest("[data-rel-type]");
    if (!chip) return;
    state.relationType = chip.getAttribute("data-rel-type");
    renderRelationChips();
    renderRelationGraph();
  });
  if (el.relationGraph) el.relationGraph.addEventListener("click", function (event) {
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
  });
  if (el.modalRelations) el.modalRelations.addEventListener("click", function (event) {
    var link = event.target.closest("[data-rel-id]");
    if (!link) return;
    event.preventDefault();
    var id = link.getAttribute("data-rel-id");
    closeModal(false);
    openModalById(id);
  });

  function setupReveal() {
    var nodes = $$("[data-reveal]");
    if (!("IntersectionObserver" in window)) {
      nodes.forEach(function (n) { n.classList.add("is-in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add("is-in"); io.unobserve(entry.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    nodes.forEach(function (n) { io.observe(n); });
  }

  /* ---------- boot ---------- */
  function boot() {
    renderStats();
    renderCover();
    renderDaily();
    renderStarMap();
    renderRelationChips();
    renderRelationGraph();
    renderCategoryGrid();
    renderFeatured();
    renderAll();
    applyHash();
    onScroll();
    setupReveal();
    if (DEBUG) {
      document.body.classList.add("debug");
      $$("img").forEach(function (img) { img.loading = "eager"; });
      $$("[data-reveal]").forEach(function (n) { n.classList.add("is-in"); });
    }
    var params = new URLSearchParams(location.search || "");
    var scrollTarget = params.get("scroll");
    if (scrollTarget) {
      var targetEl = document.getElementById(scrollTarget);
      if (targetEl) setTimeout(function () { targetEl.scrollIntoView({ block: "start" }); }, 60);
    }
    var q = params.get("q");
    if (q) {
      el.searchInput.value = q;
      state.query = q;
      el.searchClear.hidden = false;
      renderAll();
    }
    var scrollTo = params.get("scroll");
    if (scrollTo) {
      var target = document.getElementById(scrollTo);
      if (target) {
        setTimeout(function () {
          var top = target.getBoundingClientRect().top + (window.scrollY || window.pageYOffset);
          window.scrollTo({ top: top - 8, behavior: "instant" });
        }, 120);
      }
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
