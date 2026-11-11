# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "js" / "app.js"
s = p.read_text(encoding="utf-8")

old_open = '''  var modalOpen = false;
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
  }'''

new_open = '''  var modalOpen = false;
  var detailLoaded = {};
  var detailLoading = {};
  var detailQueue = {};
  var creditsLoading = false;
  var creditsQueue = [];

  function loadCredits(cb) {
    if (window.IMAGE_CREDITS) { cb(); return; }
    creditsQueue.push(cb);
    if (creditsLoading) return;
    creditsLoading = true;
    var script = document.createElement("script");
    script.src = "js/image-credits.js";
    script.onload = script.onerror = function () {
      creditsLoading = false;
      var queue = creditsQueue.splice(0);
      queue.forEach(function (fn) { fn(); });
    };
    document.head.appendChild(script);
  }

  function ensureDetails(entry, cb) {
    if (entry.description) { loadCredits(cb); return; }
    var category = entry.category;
    if (detailLoaded[category]) { loadCredits(cb); return; }
    var queue = detailQueue[category] || (detailQueue[category] = []);
    queue.push(cb);
    if (detailLoading[category]) return;
    detailLoading[category] = true;
    var script = document.createElement("script");
    script.src = "data/details/" + category + ".js";
    script.onload = script.onerror = function () {
      detailLoading[category] = false;
      detailLoaded[category] = true;
      var waiting = detailQueue[category] || [];
      detailQueue[category] = [];
      waiting.forEach(function (fn) { loadCredits(fn); });
    };
    document.head.appendChild(script);
  }

  function openModalById(id, opts) {
    var entry = speciesById(id);
    if (!entry) return false;
    ensureDetails(entry, function () { openModalNow(entry, opts); });
    return true;
  }

  function openModalNow(entry, opts) {
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
  }'''

if old_open not in s:
    print("MISS open block")
s = s.replace(old_open, new_open)

old_step = '''  function stepModal(dir) {
    if (!modalOpen) return;
    var id = dir < 0 ? el.modalPrev.dataset.id : el.modalNext.dataset.id;
    if (!id) return;
    var entry = speciesById(id);
    if (!entry) return;
    fillModal(entry);
    history.replaceState(null, "", "#/species/" + encodeURIComponent(entry.id));
    document.title = entry.name + " · " + (SITE.title || "自然图鉴");
  }'''
new_step = '''  function stepModal(dir) {
    if (!modalOpen) return;
    var id = dir < 0 ? el.modalPrev.dataset.id : el.modalNext.dataset.id;
    if (!id) return;
    var entry = speciesById(id);
    if (!entry) return;
    ensureDetails(entry, function () {
      fillModal(entry);
      history.replaceState(null, "", "#/species/" + encodeURIComponent(entry.id));
      document.title = entry.name + " · " + (SITE.title || "自然图鉴");
    });
  }'''
if old_step not in s:
    print("MISS step block")
s = s.replace(old_step, new_step)

p.write_text(s, encoding="utf-8")
print("app lazy modal patched")
