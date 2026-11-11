/* ============================================================
 * 自然图鉴 · 数据核心（数据注册表 + 图片路径 + 小工具）
 * 维护：Lead。其他成员请勿修改本文件。
 * ============================================================ */
(function () {
  "use strict";

  var store = { animals: [], plants: [], fungi: [], loaded: false };
  var seen = Object.create(null);

  function warn(msg) {
    if (window.console && window.console.error) {
      window.console.error("[百科数据] " + msg);
    }
  }

  window.ENCYCLOPEDIA = store;

  /** 注册一批物种。tab = "animals" | "plants" */
  window.registerSpecies = function (tab, list) {
    if (tab !== "animals" && tab !== "plants" && tab !== "fungi") {
      warn("未知 tab：" + tab);
      return;
    }
    if (!Array.isArray(list)) {
      warn(tab + " 的注册内容不是数组");
      return;
    }
    list.forEach(function (item) {
      if (!item || typeof item !== "object") {
        warn(tab + " 中存在非对象条目");
        return;
      }
      if (!item.id || !item.name || !item.latin || !item.category) {
        warn("条目缺少 id/name/latin/category：" + (item.name || "?"));
        return;
      }
      if (seen[item.id]) {
        warn("重复 id：" + item.id);
        return;
      }
      seen[item.id] = true;
      item.tab = tab;
      item.aliases = item.aliases || [];
      item.tags = item.tags || [];
      item.facts = item.facts || [];
      item.details = item.details || [];
      item.taxonomy = item.taxonomy || {};
      store[tab].push(item);
    });
  };

  /** 合并某类群的详情包（description/栖息/分布/保护/details/facts） */
  window.registerDetails = function (category, map) {
    var buckets = [store.animals, store.plants, store.fungi || []];
    for (var b = 0; b < buckets.length; b += 1) {
      for (var i = 0; i < buckets[b].length; i += 1) {
        var item = buckets[b][i];
        if (item.category !== category) continue;
        var detail = map[item.id];
        if (!detail) continue;
        for (var k in detail) {
          if (Object.prototype.hasOwnProperty.call(detail, k)) item[k] = detail[k];
        }
      }
    }
  };

  /** 物种图片相对路径 */
  window.speciesImage = function (entry) {
    var tab = entry && entry.tab === "animals" ? "animals" : "plants";
    return "assets/images/" + tab + "/" + entry.id + ".webp";
  };

  /** 图片占位符相对路径 */
  window.speciesPlaceholder = function (entry) {
    var tab = entry && entry.tab === "animals" ? "animals" : "plants";
    return "assets/images/placeholder-" + (tab === "animals" ? "animal" : "plant") + ".svg";
  };

  /** 分类显示名（依赖 data/meta.js 的 CATEGORY_MAP） */
  window.speciesCategoryName = function (entry) {
    var map = window.CATEGORY_MAP || {};
    var cat = map[entry.category];
    return cat ? cat.name : entry.category || "";
  };

  window.encyclopediaReady = function () {
    store.loaded = true;
  };
})();
