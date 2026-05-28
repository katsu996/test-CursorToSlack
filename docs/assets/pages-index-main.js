/**
 * GitHub Pages トップ: browser_rows.json を取得して表を描画する。
 * 依存: `pages-index-column-runtime.js`（`window.KOriginalPagesIndex`）
 */
(function () {
  "use strict";

  var PI = window.KOriginalPagesIndex;
  if (!PI || typeof PI.mergeIndexTable !== "function") {
    console.error("KOriginalPagesIndex が未ロードです。pages-index-column-runtime.js を先に読み込んでください。");
    return;
  }

  function fmt(val) {
    if (val === null || val === undefined) return "";
    if (typeof val === "number" && Number.isFinite(val)) return String(val);
    if (typeof val === "boolean") return val ? "true" : "false";
    if (Array.isArray(val)) {
      if (
        val.length &&
        val.every(function (x) {
          return (
            x === null ||
            x === undefined ||
            typeof x === "string" ||
            typeof x === "number" ||
            typeof x === "boolean"
          );
        })
      ) {
        return val
          .map(function (x) {
            return fmt(x);
          })
          .filter(function (s) {
            return s !== "";
          })
          .join(" · ");
      }
    }
    if (typeof val === "object") {
      try {
        return JSON.stringify(val);
      } catch (e) {
        return String(val);
      }
    }
    return String(val);
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function escAttr(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/\r?\n/g, " ");
  }

  function isNumericLike(val) {
    return typeof val === "number" && Number.isFinite(val);
  }

  /** DB 列 `bpm` は minbpm / maxbpm から表示用に合成する */
  var VIRTUAL_DB_KEYS = { bpm: true };

  function bpmNumber(val) {
    if (val === null || val === undefined || val === "") return null;
    if (typeof val === "number" && Number.isFinite(val)) return val;
    var n = Number(val);
    return Number.isFinite(n) ? n : null;
  }

  function formatBpmDisplay(minVal, maxVal) {
    var mi = bpmNumber(minVal);
    var ma = bpmNumber(maxVal);
    if (mi === null || ma === null) return "";
    if (mi === ma) return String(mi);
    return String(mi) + " - " + String(ma);
  }

  function dbFieldRaw(db, key) {
    if (key === "bpm") {
      var text = formatBpmDisplay(db && db.minbpm, db && db.maxbpm);
      return text === "" ? null : text;
    }
    return db ? db[key] : undefined;
  }

  function tablePriOrderForCollect(runtime) {
    var pri = runtime.table_column_order.slice();
    var tra = Array.isArray(runtime.trailing_table_columns) ? runtime.trailing_table_columns : [];
    for (var ti = 0; ti < tra.length; ti++) {
      if (pri.indexOf(tra[ti]) < 0) pri.push(tra[ti]);
    }
    return pri;
  }

  function splitLeadingMainTrailTableKeys(vTKeys, runtime) {
    var leadOrder = Array.isArray(runtime.leading_table_columns) ? runtime.leading_table_columns : [];
    var leadSet = new Set(leadOrder);
    var lead = [];
    for (var li = 0; li < leadOrder.length; li++) {
      var lk = leadOrder[li];
      if (vTKeys.indexOf(lk) >= 0) lead.push(lk);
    }
    var trailOrder = Array.isArray(runtime.trailing_table_columns) ? runtime.trailing_table_columns : [];
    var trailSet = new Set(trailOrder);
    var trail = trailOrder.filter(function (k) {
      return vTKeys.indexOf(k) >= 0 && !leadSet.has(k);
    });
    var main = [];
    for (var si = 0; si < vTKeys.length; si++) {
      var k2 = vTKeys[si];
      if (leadSet.has(k2)) continue;
      if (trailSet.has(k2)) continue;
      main.push(k2);
    }
    return { lead: lead, main: main, trail: trail };
  }

  function collectAllKeys(rows, key, runtime) {
    var s = {};
    for (var i = 0; i < rows.length; i++) {
      var o = rows[i][key];
      if (o && typeof o === "object") {
        var ks = Object.keys(o);
        for (var j = 0; j < ks.length; j++) {
          s[ks[j]] = true;
        }
      }
    }
    var pri = key === "table" ? tablePriOrderForCollect(runtime) : runtime.db_column_order;
    var arr = Object.keys(s);
    var first = [];
    for (var p = 0; p < pri.length; p++) {
      if (s[pri[p]] || (key === "db" && VIRTUAL_DB_KEYS[pri[p]])) first.push(pri[p]);
    }
    var rest = arr
      .filter(function (k) {
        return pri.indexOf(k) < 0;
      })
      .sort();
    return first.concat(rest);
  }

  function applyHrefTemplate(tpl, value) {
    return String(tpl || "").split("{value}").join(value);
  }

  function irCellsHtml(table, runtime) {
    var md5 = table && table.md5 != null ? String(table.md5).trim().toLowerCase() : "";
    var sha = table && table.sha256 != null ? String(table.sha256).trim().toLowerCase() : "";
    var md5ok = /^[0-9a-f]{32}$/.test(md5);
    var shaok = /^[0-9a-f]{64}$/.test(sha);
    var html = "";
    var cols = runtime.ir_subcolumns || [];
    for (var i = 0; i < cols.length; i++) {
      var col = cols[i];
      var hk = col.hash_kind;
      var ok = hk === "md5" ? md5ok : hk === "sha256" ? shaok : false;
      var val = hk === "md5" ? md5 : sha;
      var label = col.header || col.link_label || "—";
      if (ok && col.href_template) {
        var href = applyHrefTemplate(col.href_template, val);
        html +=
          '<td class="ir-cell"><a href="' +
          esc(href) +
          '" rel="noopener noreferrer">' +
          esc(label) +
          "</a></td>";
      } else {
        html += '<td class="empty">—</td>';
      }
    }
    return html;
  }

  function chartCellHtml(table, runtime) {
    var cc = runtime.chart_column || {};
    var m = table && table.md5 != null ? String(table.md5).trim().toLowerCase() : "";
    if (!/^[0-9a-f]{32}$/.test(m)) {
      return '<td class="empty">—</td>';
    }
    var href = applyHrefTemplate(cc.href_template || "", m);
    var label = cc.link_label || cc.header || "Chart";
    return (
      '<td class="chart-cell"><a href="' +
      esc(href) +
      '" rel="noopener noreferrer">' +
      esc(label) +
      "</a></td>"
    );
  }

  function cellHtml(val, section, key, runtime) {
    var clamp = section === "table" && key && PI.isTableClampKey(key, runtime);
    var clsExtra = clamp ? " cell-max" : "";
    var t = fmt(val);
    if (!t) return '<td class="empty' + clsExtra + '">—</td>';
    if (/^https?:\/\//i.test(t)) {
      return (
        '<td class="' +
        (clamp ? "cell-max " : "") +
        '"><a href="' +
        esc(t) +
        '" rel="noopener noreferrer">' +
        esc(t) +
        "</a></td>"
      );
    }
    var num = isNumericLike(val);
    var base = num ? "num" : "";
    var tit = clamp && t.length ? ' title="' + escAttr(t) + '"' : "";
    return '<td class="' + base + clsExtra + '"' + tit + ">" + esc(t) + "</td>";
  }

  function getSortValue(r, spec) {
    if (!spec) return null;
    var parts = spec.split(":");
    if (parts.length < 2) return null;
    var grp = parts[0];
    var col = parts.slice(1).join(":");
    if (grp === "db" && col === "bpm") {
      var d = r.db;
      if (!d || typeof d !== "object") return null;
      var mi = bpmNumber(d.minbpm);
      if (mi !== null) return mi;
      return bpmNumber(d.maxbpm);
    }
    var o = grp === "table" ? r.table : r.db;
    if (!o || typeof o !== "object") return null;
    return o[col];
  }

  function compareVals(a, b) {
    var ae = a === null || a === undefined || a === "";
    var be = b === null || b === undefined || b === "";
    if (ae && be) return 0;
    if (ae) return 1;
    if (be) return -1;
    if (
      typeof a === "number" &&
      typeof b === "number" &&
      Number.isFinite(a) &&
      Number.isFinite(b)
    ) {
      if (a < b) return -1;
      if (a > b) return 1;
      return 0;
    }
    var sa = typeof a === "object" ? JSON.stringify(a) : String(a);
    var sb = typeof b === "object" ? JSON.stringify(b) : String(b);
    return sa.localeCompare(sb, "ja", { numeric: true, sensitivity: "base" });
  }

  /** 独自レベル未設定行の内部キー（URL クエリ `cl` と対応） */
  var CUSTOM_LEVEL_UNSET_KEY = "__unset__";

  function rowCustomLevelKey(r) {
    var v = r && r.table ? r.table.custom_level : undefined;
    if (v === null || v === undefined || v === "") return CUSTOM_LEVEL_UNSET_KEY;
    return String(v);
  }

  function sortCustomLevelKeys(keys) {
    return keys.slice().sort(function (a, b) {
      if (a === CUSTOM_LEVEL_UNSET_KEY && b === CUSTOM_LEVEL_UNSET_KEY) return 0;
      if (a === CUSTOM_LEVEL_UNSET_KEY) return 1;
      if (b === CUSTOM_LEVEL_UNSET_KEY) return -1;
      var na = Number(a);
      var nb = Number(b);
      var aNum = String(na) === a && Number.isFinite(na);
      var bNum = String(nb) === b && Number.isFinite(nb);
      if (aNum && bNum) {
        if (na < nb) return -1;
        if (na > nb) return 1;
        return 0;
      }
      return String(a).localeCompare(String(b), "ja", { numeric: true, sensitivity: "base" });
    });
  }

  function externalSearchStrings(table, runtime) {
    var parts = [];
    var md5 = table && table.md5 != null ? String(table.md5).trim().toLowerCase() : "";
    var sha = table && table.sha256 != null ? String(table.sha256).trim().toLowerCase() : "";
    var md5ok = /^[0-9a-f]{32}$/.test(md5);
    var shaok = /^[0-9a-f]{64}$/.test(sha);
    var cols = runtime.ir_subcolumns || [];
    for (var i = 0; i < cols.length; i++) {
      var col = cols[i];
      var hk = col.hash_kind;
      if (hk === "md5" && md5ok && col.href_template) parts.push(applyHrefTemplate(col.href_template, md5));
      if (hk === "sha256" && shaok && col.href_template) parts.push(applyHrefTemplate(col.href_template, sha));
    }
    var cc = runtime.chart_column;
    if (cc && cc.hash_kind === "md5" && md5ok && cc.href_template) {
      parts.push(applyHrefTemplate(cc.href_template, md5));
    }
    return parts;
  }

  /** 1ページあたりの行数（一覧のセレクトと URL ?ps= で同期） */
  var PAGE_SIZE_OPTIONS = [50, 100, 150, 200, 300, 500];

  var metaEl = document.getElementById("meta");
  var metaDl = document.getElementById("meta-dl");
  var filterSrcBar = document.getElementById("filter-src-bar");
  var filterCustomLevelBar = document.getElementById("filter-custom-level-bar");
  var errEl = document.getElementById("err");
  var scrollEl = document.getElementById("scroll");
  var colbarEl = document.getElementById("colbar");
  var colbarInner = document.getElementById("colbar-inner");
  var thead = document.getElementById("thead");
  var tbody = document.getElementById("tbody");
  var q = document.getElementById("q");
  var countEl = document.getElementById("count");
  var sortCol1 = document.getElementById("sort-col-1");
  var sortDir1 = document.getElementById("sort-dir-1");
  var sortCol2 = document.getElementById("sort-col-2");
  var sortDir2 = document.getElementById("sort-dir-2");
  var sortCol3 = document.getElementById("sort-col-3");
  var sortDir3 = document.getElementById("sort-dir-3");
  var loadStatus = document.getElementById("load-status");
  var reloadBtn = document.getElementById("reload-data");
  var paginationBar = document.getElementById("pagination-bar");
  var pagePrev = document.getElementById("page-prev");
  var pageNext = document.getElementById("page-next");
  var pageFirst = document.getElementById("page-first");
  var pageLast = document.getElementById("page-last");
  var pageGo = document.getElementById("page-go");
  var pageJump = document.getElementById("page-jump");
  var pageSizeSel = document.getElementById("page-size");
  var pageIndicator = document.getElementById("page-indicator");
  var toolbarToggle = document.getElementById("toolbar-panel-toggle");
  var toolbarPanel = document.getElementById("toolbar-panel");

  if (loadStatus) loadStatus.hidden = false;
  if (errEl) {
    errEl.hidden = true;
    errEl.textContent = "";
  }
  var mainContent = document.getElementById("main-content");
  if (mainContent) mainContent.setAttribute("aria-busy", "true");

  fetch("./table/browser_rows.json", { cache: "no-store" })
    .then(function (r) {
      if (!r.ok) throw new Error("browser_rows.json を取得できません (" + r.status + ")");
      return r.json();
    })
    .then(function (data) {
      if (loadStatus) loadStatus.hidden = true;
      if (reloadBtn) reloadBtn.hidden = true;
      if (mainContent) mainContent.setAttribute("aria-busy", "false");
      if (!data || typeof data !== "object") {
        throw new Error("browser_rows.json の形式が不正です（トップレベルがオブジェクトではありません）。");
      }
      if (!Object.prototype.hasOwnProperty.call(data, "rows")) {
        var rsn = data.meta && data.meta.reason ? String(data.meta.reason) : "(meta.reason なし)";
        throw new Error("browser_rows.json に rows がありません。meta.reason: " + rsn);
      }
      var meta = data.meta || {};
      var rows = Array.isArray(data.rows) ? data.rows : [];
      var pagesUi = meta.pages_ui && typeof meta.pages_ui === "object" ? meta.pages_ui : {};
      var runtime = PI.mergeIndexTable(pagesUi);
      var colWidthsDefault =
        pagesUi.column_widths && typeof pagesUi.column_widths === "object" ? pagesUi.column_widths : {};
      var visDefaults =
        pagesUi.column_visible_defaults && typeof pagesUi.column_visible_defaults === "object"
          ? pagesUi.column_visible_defaults
          : {};
      var hiddenFb = runtime.column_hidden_fallback;

      function defaultExtraVisible(key) {
        if (visDefaults && typeof visDefaults === "object" && Object.prototype.hasOwnProperty.call(visDefaults, key)) {
          return !!visDefaults[key];
        }
        return true;
      }
      var visIr = defaultExtraVisible("ir");
      var visChart = defaultExtraVisible("chart");
      var defaultVisIr = visIr;
      var defaultVisChart = visChart;

      function defaultColumnVisible(k, section) {
        var secKey = section === "table" ? "table" : "db";
        var sec = visDefaults[secKey];
        if (sec && typeof sec === "object" && Object.prototype.hasOwnProperty.call(sec, k)) {
          return !!sec[k];
        }
        if (section === "db" && (k === "title" || k === "artist")) return false;
        if (section === "db" && (k === "md5" || k === "sha256")) return false;
        return !hiddenFb[k];
      }

      var colWidths = {};
      try {
        var _cw = localStorage.getItem("k-original-col-widths-v2");
        if (_cw) colWidths = JSON.parse(_cw) || {};
      } catch (_e0) {}

      function colKeysList(vTKeys, vDKeys) {
        var sp = splitLeadingMainTrailTableKeys(vTKeys, runtime);
        var vTLead = sp.lead;
        var vTMain = sp.main;
        var vTTrail = sp.trail;
        var keys = [];
        var ti;
        for (ti = 0; ti < vTLead.length; ti++) keys.push("t:" + vTLead[ti]);
        if (vTMain.length) {
          for (ti = 0; ti < vTMain.length; ti++) keys.push("t:" + vTMain[ti]);
        } else if (!vTLead.length) keys.push("t:_empty");
        if (vDKeys.length) {
          for (ti = 0; ti < vDKeys.length; ti++) keys.push("d:" + vDKeys[ti]);
        } else keys.push("d:_empty");
        var irs = runtime.ir_subcolumns || [];
        if (visIr) {
          for (var ii = 0; ii < irs.length; ii++) {
            if (irs[ii].colgroup_key) keys.push(String(irs[ii].colgroup_key));
          }
        }
        if (visChart) {
          if (runtime.chart_column && runtime.chart_column.colgroup_key) {
            keys.push(String(runtime.chart_column.colgroup_key));
          } else {
            keys.push("chart");
          }
        }
        for (ti = 0; ti < vTTrail.length; ti++) keys.push("t:" + vTTrail[ti]);
        return keys;
      }
      function persistColWidths() {
        try {
          localStorage.setItem("k-original-col-widths-v2", JSON.stringify(colWidths));
        } catch (_e1) {}
      }
      function rebuildColgroup(vTKeys, vDKeys) {
        var cg = document.getElementById("tbl-colgroup");
        if (!cg) return;
        cg.innerHTML = "";
        var keys = colKeysList(vTKeys, vDKeys);
        for (var ci = 0; ci < keys.length; ci++) {
          var ck = keys[ci];
          var col = document.createElement("col");
          var sw = colWidths[ck];
          if (sw) col.style.width = sw;
          else {
            var defAny = colWidthsDefault[ck];
            if (typeof defAny === "string" && defAny.trim()) {
              col.style.width = defAny.trim();
            } else if (ck.indexOf("t:") === 0) {
              var rk = ck.slice(2);
              if (rk !== "_empty" && PI.isTableClampKey(rk, runtime)) col.style.width = "50ch";
            } else if (
              ck.indexOf("ir:") === 0 ||
              ck === "chart" ||
              (runtime.chart_column && ck === String(runtime.chart_column.colgroup_key || ""))
            ) {
              col.style.width = "4.5rem";
            }
          }
          col.setAttribute("data-col-key", ck);
          cg.appendChild(col);
        }
      }
      function initColResize(trh2, vTKeys, vDKeys) {
        var cg = document.getElementById("tbl-colgroup");
        if (!cg || !trh2) return;
        var keys = colKeysList(vTKeys, vDKeys);
        var ths = trh2.querySelectorAll("th");
        if (ths.length !== keys.length || cg.children.length !== keys.length) return;
        for (var hi = 0; hi < ths.length; hi++) {
          (function (idx) {
            var th = ths[idx];
            var prev = th.querySelector(".col-resize-handle");
            if (prev) prev.remove();
            var handle = document.createElement("span");
            handle.className = "col-resize-handle";
            handle.title = "ドラッグで列幅を変更";
            th.appendChild(handle);
            handle.addEventListener("mousedown", function (downEv) {
              downEv.preventDefault();
              downEv.stopPropagation();
              var startX = downEv.clientX;
              var colEl = cg.children[idx];
              var rect = colEl.getBoundingClientRect();
              var startW = rect.width;
              function move(ev) {
                var w = Math.max(64, startW + (ev.clientX - startX));
                colEl.style.width = w + "px";
              }
              function up() {
                document.removeEventListener("mousemove", move);
                document.removeEventListener("mouseup", up);
                colWidths[keys[idx]] = colEl.style.width;
                persistColWidths();
                document.body.style.cursor = "";
                document.body.classList.remove("col-resizing");
              }
              document.addEventListener("mousemove", move);
              document.addEventListener("mouseup", up);
              document.body.style.cursor = "col-resize";
              document.body.classList.add("col-resizing");
            });
          })(hi);
        }
      }

      var pt = meta.page_title && String(meta.page_title).trim();
      if (pt) {
        var h1el = document.getElementById("site-h1");
        if (h1el) h1el.textContent = pt;
        document.title = pt;
      }
      metaDl.innerHTML = "";
      var pairs = [["行数", meta.row_count]];
      var metaShortsForLine = Array.isArray(meta.source_table_short_names) ? meta.source_table_short_names : [];
      var metaDisplaysForLine = Array.isArray(meta.source_table_display_names) ? meta.source_table_display_names : [];
      var srcLineParts = [];
      for (var li = 0; li < metaShortsForLine.length || li < metaDisplaysForLine.length; li++) {
        var shL = li < metaShortsForLine.length ? String(metaShortsForLine[li] || "").trim() : "";
        var dnL = li < metaDisplaysForLine.length ? String(metaDisplaysForLine[li] || "").trim() : "";
        if (!shL && !dnL) continue;
        if (!shL) shL = dnL;
        if (!dnL) dnL = shL;
        srcLineParts.push(shL + "(" + dnL + ")");
      }
      if (srcLineParts.length) {
        pairs.push(["難易度表", srcLineParts.join(" · ")]);
      }
      pairs.push(["備考", meta.reason]);
      pairs.forEach(function (pair) {
        if (pair[1] === undefined || pair[1] === null || pair[1] === "") return;
        var dt = document.createElement("dt");
        dt.textContent = pair[0];
        var dd = document.createElement("dd");
        dd.textContent = String(pair[1]);
        metaDl.appendChild(dt);
        metaDl.appendChild(dd);
      });
      metaEl.hidden = metaDl.children.length === 0;

      var allTKeys = collectAllKeys(rows, "table", runtime);
      var allDKeys = collectAllKeys(rows, "db", runtime);
      var metaShorts = Array.isArray(meta.source_table_short_names) ? meta.source_table_short_names : [];
      var metaDisplays = Array.isArray(meta.source_table_display_names) ? meta.source_table_display_names : [];
      var sourceFilterState = {};
      var customLevelFilterState = {};
      var customLevelOrderedKeys = [];

      function buildCustomLevelFilterBar() {
        customLevelFilterState = {};
        customLevelOrderedKeys = [];
        if (!filterCustomLevelBar) return;
        if (allTKeys.indexOf("custom_level") < 0) {
          filterCustomLevelBar.hidden = true;
          filterCustomLevelBar.innerHTML = "";
          return;
        }
        var seen = {};
        for (var rli = 0; rli < rows.length; rli++) {
          seen[rowCustomLevelKey(rows[rli])] = true;
        }
        var keys = sortCustomLevelKeys(Object.keys(seen));
        if (!keys.length) {
          filterCustomLevelBar.hidden = true;
          filterCustomLevelBar.innerHTML = "";
          return;
        }
        customLevelOrderedKeys = keys;
        filterCustomLevelBar.innerHTML = "";
        var leadCl = document.createElement("div");
        leadCl.className = "filter-src-lead";
        leadCl.textContent =
          "独自レベル（チェックした値の行だけ表示。すべてオフのときは行を表示しません）";
        filterCustomLevelBar.appendChild(leadCl);
        var bulkCl = document.createElement("div");
        bulkCl.className = "filter-bulk-actions";
        var bAllCl = document.createElement("button");
        bAllCl.type = "button";
        bAllCl.className = "shadcn-btn filter-bulk-btn";
        bAllCl.textContent = "すべて選択";
        var bNoneCl = document.createElement("button");
        bNoneCl.type = "button";
        bNoneCl.className = "shadcn-btn filter-bulk-btn";
        bNoneCl.textContent = "すべて解除";
        bulkCl.appendChild(bAllCl);
        bulkCl.appendChild(bNoneCl);
        filterCustomLevelBar.appendChild(bulkCl);
        bAllCl.addEventListener("click", function () {
          for (var ai = 0; ai < customLevelOrderedKeys.length; ai++) {
            customLevelFilterState[customLevelOrderedKeys[ai]] = true;
          }
          filterCustomLevelBar.querySelectorAll("input[type=checkbox][data-cl-key]").forEach(function (inp) {
            inp.checked = true;
          });
          currentPage = 1;
          refresh();
        });
        bNoneCl.addEventListener("click", function () {
          for (var zi = 0; zi < customLevelOrderedKeys.length; zi++) {
            customLevelFilterState[customLevelOrderedKeys[zi]] = false;
          }
          filterCustomLevelBar.querySelectorAll("input[type=checkbox][data-cl-key]").forEach(function (inp) {
            inp.checked = false;
          });
          currentPage = 1;
          refresh();
        });
        keys.forEach(function (ck) {
          customLevelFilterState[ck] = true;
          var labCl = document.createElement("label");
          var inpCl = document.createElement("input");
          inpCl.type = "checkbox";
          inpCl.checked = true;
          inpCl.setAttribute("data-cl-key", ck);
          inpCl.addEventListener("change", function () {
            customLevelFilterState[ck] = inpCl.checked;
            currentPage = 1;
            refresh();
          });
          labCl.appendChild(inpCl);
          var disp = ck === CUSTOM_LEVEL_UNSET_KEY ? "（未設定）" : ck;
          labCl.appendChild(document.createTextNode(disp));
          filterCustomLevelBar.appendChild(labCl);
        });
        filterCustomLevelBar.hidden = false;
      }

      function applyCustomLevelFilter(base) {
        if (!customLevelOrderedKeys.length) return base.slice();
        var enabledCl = [];
        for (var eci = 0; eci < customLevelOrderedKeys.length; eci++) {
          var ek = customLevelOrderedKeys[eci];
          if (customLevelFilterState[ek]) enabledCl.push(ek);
        }
        if (!enabledCl.length) return [];
        return base.filter(function (r) {
          return enabledCl.indexOf(rowCustomLevelKey(r)) >= 0;
        });
      }

      function buildSourceFilterBar() {
        sourceFilterState = {};
        if (!filterSrcBar) return;
        var entries = [];
        for (var si = 0; si < metaShorts.length; si++) {
          var sh = String(metaShorts[si] || "").trim();
          if (!sh) continue;
          var dn =
            si < metaDisplays.length && String(metaDisplays[si] || "").trim()
              ? String(metaDisplays[si]).trim()
              : sh;
          entries.push({ short: sh, label: dn });
        }
        if (!entries.length) {
          filterSrcBar.hidden = true;
          return;
        }
        filterSrcBar.innerHTML = "";
        var lead = document.createElement("div");
        lead.className = "filter-src-lead";
        lead.textContent = "難易度表（1つ以上チェックした表のみ表示。すべてオフのときは行を表示しません）";
        filterSrcBar.appendChild(lead);
        var bulkSrc = document.createElement("div");
        bulkSrc.className = "filter-bulk-actions";
        var bAllSrc = document.createElement("button");
        bAllSrc.type = "button";
        bAllSrc.className = "shadcn-btn filter-bulk-btn";
        bAllSrc.textContent = "すべて選択";
        var bNoneSrc = document.createElement("button");
        bNoneSrc.type = "button";
        bNoneSrc.className = "shadcn-btn filter-bulk-btn";
        bNoneSrc.textContent = "すべて解除";
        bulkSrc.appendChild(bAllSrc);
        bulkSrc.appendChild(bNoneSrc);
        filterSrcBar.appendChild(bulkSrc);
        bAllSrc.addEventListener("click", function () {
          Object.keys(sourceFilterState).forEach(function (k) {
            sourceFilterState[k] = true;
          });
          filterSrcBar.querySelectorAll("input[type=checkbox][data-short]").forEach(function (inp) {
            inp.checked = true;
          });
          currentPage = 1;
          refresh();
        });
        bNoneSrc.addEventListener("click", function () {
          Object.keys(sourceFilterState).forEach(function (k) {
            sourceFilterState[k] = false;
          });
          filterSrcBar.querySelectorAll("input[type=checkbox][data-short]").forEach(function (inp) {
            inp.checked = false;
          });
          currentPage = 1;
          refresh();
        });
        entries.forEach(function (e) {
          sourceFilterState[e.key] = true;
          var lab = document.createElement("label");
          var inp = document.createElement("input");
          inp.type = "checkbox";
          inp.checked = true;
          inp.dataset.short = e.key;
          inp.addEventListener("change", function () {
            sourceFilterState[e.key] = inp.checked;
            currentPage = 1;
            refresh();
          });
          lab.appendChild(inp);
          lab.appendChild(document.createTextNode(e.label));
          filterSrcBar.appendChild(lab);
        });
        filterSrcBar.hidden = false;
      }

      function rowSourceTags(r) {
        var t = r.table || {};
        var out = {};
        var shorts = t.source_table_short_names;
        if (Array.isArray(shorts)) {
          for (var ri = 0; ri < shorts.length; ri++) {
            var s = String(shorts[ri] || "").trim();
            if (s) out[s] = true;
          }
        }
        if (!Object.keys(out).length && t.source_table_index != null && metaShorts.length) {
          var ix = Number(t.source_table_index);
          if (Number.isFinite(ix) && ix >= 1 && ix <= metaShorts.length) {
            var fb = String(metaShorts[ix - 1] || "").trim();
            if (fb) out[fb] = true;
          }
        }
        return out;
      }

      function applySourceFilter(base) {
        if (!Object.keys(sourceFilterState).length) return base.slice();
        var enabled = [];
        Object.keys(sourceFilterState).forEach(function (k) {
          if (sourceFilterState[k]) enabled.push(k);
        });
        if (!enabled.length) return [];
        return base.filter(function (r) {
          var tags = rowSourceTags(r);
          for (var ei = 0; ei < enabled.length; ei++) {
            if (tags[enabled[ei]]) return true;
          }
          return false;
        });
      }

      buildSourceFilterBar();
      buildCustomLevelFilterBar();

      var currentPage = 1;
      var pageSize = 150;
      try {
        var _storedPs = localStorage.getItem("k-original-page-size");
        if (_storedPs) {
          var _nps = parseInt(_storedPs, 10);
          if (PAGE_SIZE_OPTIONS.indexOf(_nps) >= 0) pageSize = _nps;
        }
      } catch (_e_ps) {}
      var urlTimer = null;

      function syncPageSizeSelect() {
        if (!pageSizeSel) return;
        for (var pi = 0; pi < pageSizeSel.options.length; pi++) {
          if (parseInt(pageSizeSel.options[pi].value, 10) === pageSize) {
            pageSizeSel.selectedIndex = pi;
            return;
          }
        }
      }

      if (pageSizeSel) {
        pageSizeSel.innerHTML = "";
        for (var psi = 0; psi < PAGE_SIZE_OPTIONS.length; psi++) {
          var nOpt = PAGE_SIZE_OPTIONS[psi];
          var optSz = document.createElement("option");
          optSz.value = String(nOpt);
          optSz.textContent = String(nOpt);
          pageSizeSel.appendChild(optSz);
        }
        pageSizeSel.addEventListener("change", function () {
          var v = parseInt(pageSizeSel.value, 10);
          if (PAGE_SIZE_OPTIONS.indexOf(v) >= 0) {
            pageSize = v;
            try {
              localStorage.setItem("k-original-page-size", String(v));
            } catch (_ls) {}
            currentPage = 1;
            refresh();
          }
        });
        syncPageSizeSelect();
      }

      var visT = {};
      var visD = {};
      allTKeys.forEach(function (k) {
        visT[k] = defaultColumnVisible(k, "table");
      });
      allDKeys.forEach(function (k) {
        visD[k] = defaultColumnVisible(k, "db");
      });

      var defaultVisT = {};
      var defaultVisD = {};
      allTKeys.forEach(function (k) {
        defaultVisT[k] = visT[k];
      });
      allDKeys.forEach(function (k) {
        defaultVisD[k] = visD[k];
      });

      function visibleKeys(allKeys, vis) {
        return allKeys.filter(function (k) {
          return vis[k];
        });
      }

      function rebuildThead(vTKeys, vDKeys) {
        var sp = splitLeadingMainTrailTableKeys(vTKeys, runtime);
        var vTLead = sp.lead;
        var vTMain = sp.main;
        var vTTrail = sp.trail;
        var irCols = runtime.ir_subcolumns || [];
        var gl = runtime.group_labels || {};
        thead.innerHTML = "";
        var trh1 = document.createElement("tr");
        if (vTLead.length) {
          var thL = document.createElement("th");
          thL.colSpan = Math.max(1, vTLead.length);
          thL.className = "group-lead";
          thL.textContent = gl.leading || "独自レベル";
          trh1.appendChild(thL);
        }
        var thT = document.createElement("th");
        thT.colSpan = Math.max(1, vTMain.length);
        thT.className = "group-t";
        thT.textContent = gl.table || "元難易度表の列";
        trh1.appendChild(thT);
        var thD = document.createElement("th");
        thD.colSpan = Math.max(1, vDKeys.length);
        thD.className = "group-d";
        thD.textContent = gl.db || "楽曲情報の列";
        trh1.appendChild(thD);
        if (visIr && irCols.length) {
          var thIr = document.createElement("th");
          thIr.colSpan = Math.max(1, irCols.length);
          thIr.className = "group-ir";
          thIr.textContent = gl.ir || "IR";
          trh1.appendChild(thIr);
        }
        if (visChart) {
          var thChart = document.createElement("th");
          thChart.colSpan = 1;
          thChart.className = "group-chart";
          thChart.textContent = gl.chart || "Chart";
          trh1.appendChild(thChart);
        }
        if (vTTrail.length) {
          var thTr = document.createElement("th");
          thTr.colSpan = Math.max(1, vTTrail.length);
          thTr.className = "group-trail";
          thTr.textContent = gl.trailing || "末尾の表列";
          trh1.appendChild(thTr);
        }
        thead.appendChild(trh1);

        var trh2 = document.createElement("tr");
        vTLead.forEach(function (k) {
          var thL2 = document.createElement("th");
          thL2.className = "group-lead" + (PI.isTableClampKey(k, runtime) ? " cell-max" : "");
          thL2.textContent = PI.tableColTitle(k, runtime);
          trh2.appendChild(thL2);
        });
        vTMain.forEach(function (k) {
          var th = document.createElement("th");
          th.className = "group-t" + (PI.isTableClampKey(k, runtime) ? " cell-max" : "");
          th.textContent = PI.tableColTitle(k, runtime);
          trh2.appendChild(th);
        });
        if (!vTMain.length) {
          var th0 = document.createElement("th");
          th0.className = "group-t";
          th0.textContent = "（表データなし）";
          trh2.appendChild(th0);
        }
        vDKeys.forEach(function (k) {
          var th = document.createElement("th");
          th.className = "group-d";
          th.textContent = PI.dbColTitle(k, runtime);
          trh2.appendChild(th);
        });
        if (!vDKeys.length) {
          var th1 = document.createElement("th");
          th1.className = "group-d";
          th1.textContent = "（DB列なし）";
          trh2.appendChild(th1);
        }
        if (visIr) {
          irCols.forEach(function (col) {
            var thi = document.createElement("th");
            thi.className = "group-ir";
            thi.textContent = col.header || col.colgroup_key || "—";
            trh2.appendChild(thi);
          });
        }
        if (visChart) {
          var thChart2 = document.createElement("th");
          thChart2.className = "group-chart";
          thChart2.textContent = (runtime.chart_column && runtime.chart_column.header) || "Chart";
          trh2.appendChild(thChart2);
        }
        vTTrail.forEach(function (k) {
          var th3 = document.createElement("th");
          th3.className = "group-trail";
          th3.textContent = PI.tableColTitle(k, runtime);
          trh2.appendChild(th3);
        });
        thead.appendChild(trh2);
        rebuildColgroup(vTKeys, vDKeys);
        initColResize(trh2, vTKeys, vDKeys);
      }

      function buildColPicker() {
        colbarInner.innerHTML = "";
        function addGroup(title, cls, allKeys, vis, section) {
          var wrap = document.createElement("div");
          wrap.className = "colbar-group";
          var h = document.createElement("div");
          h.className = "colbar-group-title " + cls;
          h.textContent = title;
          wrap.appendChild(h);
          var picks = document.createElement("div");
          picks.className = "colpick-wrap";
          allKeys.forEach(function (k) {
            var lab = document.createElement("label");
            lab.className = "colpick";
            var inp = document.createElement("input");
            inp.type = "checkbox";
            inp.checked = !!vis[k];
            inp.addEventListener("change", function () {
              vis[k] = inp.checked;
              currentPage = 1;
              var vT = visibleKeys(allTKeys, visT);
              var vD = visibleKeys(allDKeys, visD);
              rebuildThead(vT, vD);
              refresh();
            });
            lab.appendChild(inp);
            var span = document.createElement("span");
            span.textContent =
              section === "db" ? PI.dbColTitle(k, runtime) : PI.tableColTitle(k, runtime);
            lab.appendChild(span);
            picks.appendChild(lab);
          });
          wrap.appendChild(picks);
          colbarInner.appendChild(wrap);
        }
        var tsp = splitLeadingMainTrailTableKeys(allTKeys, runtime);
        var glPick = runtime.group_labels || {};
        if (tsp.lead.length) {
          addGroup(glPick.leading || "独自レベル", "lead", tsp.lead, visT, "table");
        }
        if (tsp.main.length) {
          addGroup(glPick.table || "元難易度表の列", "t", tsp.main, visT, "table");
        }
        if (tsp.trail.length) {
          addGroup(glPick.trailing || "末尾の表列", "trail", tsp.trail, visT, "table");
        }
        addGroup(glPick.db || "楽曲情報の列", "d", allDKeys, visD, "db");
        var wrapX = document.createElement("div");
        wrapX.className = "colbar-group";
        var hx = document.createElement("div");
        hx.className = "colbar-group-title ir";
        hx.textContent = "IR・Chart";
        wrapX.appendChild(hx);
        var picksX = document.createElement("div");
        picksX.className = "colpick-wrap";
        function addExtraCheckbox(labelText, get, set) {
          var lab = document.createElement("label");
          lab.className = "colpick";
          var inp = document.createElement("input");
          inp.type = "checkbox";
          inp.checked = get();
          inp.addEventListener("change", function () {
            set(inp.checked);
            currentPage = 1;
            var vT = visibleKeys(allTKeys, visT);
            var vD = visibleKeys(allDKeys, visD);
            rebuildThead(vT, vD);
            refresh();
          });
          lab.appendChild(inp);
          lab.appendChild(document.createTextNode(labelText));
          picksX.appendChild(lab);
        }
        addExtraCheckbox(
          "IR（LR2IR / MinIR / Mocha）",
          function () {
            return visIr;
          },
          function (v) {
            visIr = v;
          }
        );
        addExtraCheckbox(
          "Chart",
          function () {
            return visChart;
          },
          function (v) {
            visChart = v;
          }
        );
        wrapX.appendChild(picksX);
        colbarInner.appendChild(wrapX);
      }

      function rowText(r) {
        var t = r.table || {};
        var d = r.db || {};
        var parts = [];
        allTKeys.forEach(function (k) {
          parts.push(fmt(t[k]));
        });
        allDKeys.forEach(function (k) {
          parts.push(fmt(dbFieldRaw(d, k)));
        });
        externalSearchStrings(t, runtime).forEach(function (u) {
          parts.push(u);
        });
        return parts.join(" ") + " " + JSON.stringify(t) + " " + JSON.stringify(d);
      }

      function fillSortSelect(sortSelect) {
        if (!sortSelect) return;
        while (sortSelect.options.length > 1) sortSelect.remove(1);
        allTKeys.forEach(function (k) {
          var opt = document.createElement("option");
          opt.value = "table:" + k;
          opt.textContent = PI.tableColTitle(k, runtime);
          sortSelect.appendChild(opt);
        });
        allDKeys.forEach(function (k) {
          var opt = document.createElement("option");
          opt.value = "db:" + k;
          opt.textContent = PI.dbColTitle(k, runtime);
          sortSelect.appendChild(opt);
        });
      }

      fillSortSelect(sortCol1);
      fillSortSelect(sortCol2);
      fillSortSelect(sortCol3);
      if (selectHasValue(sortCol1, "table:custom_level")) {
        sortCol1.value = "table:custom_level";
      } else if (allTKeys.indexOf("title") >= 0) {
        sortCol1.value = "table:title";
      } else if (allDKeys.indexOf("title") >= 0) {
        sortCol1.value = "db:title";
      } else {
        sortCol1.value = "";
      }
      sortDir1.value = "asc";
      sortCol2.value = "";
      sortDir2.value = "asc";
      sortCol3.value = "";
      sortDir3.value = "asc";
      [sortCol1, sortDir1, sortCol2, sortDir2, sortCol3, sortDir3].forEach(function (el) {
        if (el) el.disabled = false;
      });

      function readUrlSearchParams() {
        try {
          return new URL(window.location.href).searchParams;
        } catch (e1) {
          return new URLSearchParams();
        }
      }

      function selectHasValue(sel, val) {
        if (!sel || !val) return false;
        for (var oi = 0; oi < sel.options.length; oi++) {
          if (sel.options[oi].value === val) return true;
        }
        return false;
      }

      function applyUrlState() {
        var p = readUrlSearchParams();
        if (p.get("q")) q.value = p.get("q");
        var pairs = [
          ["s1", sortCol1, "d1", sortDir1],
          ["s2", sortCol2, "d2", sortDir2],
          ["s3", sortCol3, "d3", sortDir3]
        ];
        for (var pi = 0; pi < pairs.length; pi++) {
          var pk = pairs[pi];
          var sk = p.get(pk[0]);
          if (sk && selectHasValue(pk[1], sk)) pk[1].value = sk;
          var dk = (p.get(pk[2]) || "").toLowerCase();
          if (dk === "asc" || dk === "desc") pk[3].value = dk;
        }
        if (p.has("src") && filterSrcBar && Object.keys(sourceFilterState).length) {
          var raw = p.get("src");
          var parts = raw
            ? raw
                .split(",")
                .map(function (x) {
                  return String(x || "").trim();
                })
                .filter(Boolean)
            : [];
          var en = {};
          for (var pj = 0; pj < parts.length; pj++) en[parts[pj]] = true;
          Object.keys(sourceFilterState).forEach(function (k) {
            sourceFilterState[k] = !!en[k];
          });
          filterSrcBar.querySelectorAll("input[type=checkbox][data-short]").forEach(function (inp) {
            var sh = inp.getAttribute("data-short");
            if (sh) inp.checked = !!sourceFilterState[sh];
          });
        }
        if (p.has("cl") && filterCustomLevelBar && customLevelOrderedKeys.length) {
          var clRaw = p.get("cl");
          if (clRaw === "") {
            Object.keys(customLevelFilterState).forEach(function (k) {
              customLevelFilterState[k] = false;
            });
          } else if (clRaw != null && String(clRaw).length) {
            var wantCl = {};
            String(clRaw)
              .split(",")
              .forEach(function (seg) {
                var t = String(seg || "").trim();
                if (!t) return;
                try {
                  wantCl[decodeURIComponent(t)] = true;
                } catch (e3) {
                  wantCl[t] = true;
                }
              });
            Object.keys(customLevelFilterState).forEach(function (k) {
              customLevelFilterState[k] = !!wantCl[k];
            });
          }
          filterCustomLevelBar.querySelectorAll("input[type=checkbox][data-cl-key]").forEach(function (inp) {
            var ck = inp.getAttribute("data-cl-key");
            if (ck) inp.checked = !!customLevelFilterState[ck];
          });
        }
        var tcols = p.get("tcols");
        if (tcols && tcols.trim()) {
          var setT = {};
          tcols.split(",").forEach(function (x) {
            var k = String(x || "").trim();
            if (k) setT[k] = true;
          });
          allTKeys.forEach(function (k) {
            visT[k] = !!setT[k];
          });
        }
        var dcols = p.get("dcols");
        if (dcols && dcols.trim()) {
          var setD = {};
          dcols.split(",").forEach(function (x) {
            var k2 = String(x || "").trim();
            if (k2) setD[k2] = true;
          });
          allDKeys.forEach(function (k) {
            visD[k] = !!setD[k];
          });
        }
        if (p.has("ir")) {
          var irv = (p.get("ir") || "").toLowerCase();
          if (irv === "0" || irv === "false") visIr = false;
          else if (irv === "1" || irv === "true") visIr = true;
        }
        if (p.has("ch")) {
          var chv = (p.get("ch") || "").toLowerCase();
          if (chv === "0" || chv === "false") visChart = false;
          else if (chv === "1" || chv === "true") visChart = true;
        }
        var pgn = parseInt(p.get("pg") || "1", 10);
        if (Number.isFinite(pgn) && pgn >= 1) currentPage = pgn;
        if (p.has("ps")) {
          var psn = parseInt(p.get("ps"), 10);
          if (PAGE_SIZE_OPTIONS.indexOf(psn) >= 0) pageSize = psn;
        }
        if (p.get("tb") === "1" && toolbarPanel && toolbarToggle) {
          toolbarPanel.hidden = false;
          toolbarToggle.setAttribute("aria-expanded", "true");
          var chev = toolbarToggle.querySelector(".filter-chevron");
          if (chev) chev.textContent = "▲";
        }
      }

      applyUrlState();
      syncPageSizeSelect();

      function render(list) {
        var vTKeys = visibleKeys(allTKeys, visT);
        var vDKeys = visibleKeys(allDKeys, visD);
        var sp = splitLeadingMainTrailTableKeys(vTKeys, runtime);
        var vTLead = sp.lead;
        var vTMain = sp.main;
        var vTTrail = sp.trail;
        tbody.innerHTML = "";
        list.forEach(function (r) {
          var tr = document.createElement("tr");
          var t = r.table || {};
          var d = r.db || {};
          vTLead.forEach(function (k) {
            tr.insertAdjacentHTML("beforeend", cellHtml(t[k], "table", k, runtime));
          });
          vTMain.forEach(function (k) {
            tr.insertAdjacentHTML("beforeend", cellHtml(t[k], "table", k, runtime));
          });
          if (!vTMain.length) tr.insertAdjacentHTML("beforeend", '<td class="empty">—</td>');
          vDKeys.forEach(function (k) {
            tr.insertAdjacentHTML("beforeend", cellHtml(dbFieldRaw(d, k), "db", k, runtime));
          });
          if (!vDKeys.length) tr.insertAdjacentHTML("beforeend", '<td class="empty">—</td>');
          if (visIr) tr.insertAdjacentHTML("beforeend", irCellsHtml(t, runtime));
          if (visChart) tr.insertAdjacentHTML("beforeend", chartCellHtml(t, runtime));
          vTTrail.forEach(function (k) {
            tr.insertAdjacentHTML("beforeend", cellHtml(t[k], "table", k, runtime));
          });
          tbody.appendChild(tr);
        });
      }

      function applySearch() {
        var needle = (q.value || "").trim().toLowerCase();
        if (!needle) return rows.slice();
        return rows.filter(function (r) {
          return rowText(r).toLowerCase().indexOf(needle) >= 0;
        });
      }

      function applySort(base) {
        var levels = [];
        [
          { c: sortCol1, d: sortDir1 },
          { c: sortCol2, d: sortDir2 },
          { c: sortCol3, d: sortDir3 }
        ].forEach(function (pair) {
          if (!pair.c) return;
          var spec = String(pair.c.value || "").trim();
          if (!spec) return;
          var dir = pair.d && pair.d.value === "desc" ? -1 : 1;
          levels.push({ spec: spec, dir: dir });
        });
        if (!levels.length) return base.slice();
        return base.slice().sort(function (r1, r2) {
          for (var li = 0; li < levels.length; li++) {
            var L = levels[li];
            var cmp = compareVals(getSortValue(r1, L.spec), getSortValue(r2, L.spec));
            if (cmp !== 0) return L.dir * cmp;
          }
          return 0;
        });
      }

      function filteredList() {
        return applySort(applyCustomLevelFilter(applySourceFilter(applySearch())));
      }

      function visEqualDefaults() {
        for (var vi = 0; vi < allTKeys.length; vi++) {
          var kt = allTKeys[vi];
          if (visT[kt] !== defaultVisT[kt]) return false;
        }
        for (var vj = 0; vj < allDKeys.length; vj++) {
          var kd = allDKeys[vj];
          if (visD[kd] !== defaultVisD[kd]) return false;
        }
        if (visIr !== defaultVisIr) return false;
        if (visChart !== defaultVisChart) return false;
        return true;
      }

      function allSourceFiltersOn() {
        var ks = Object.keys(sourceFilterState);
        if (!ks.length) return true;
        for (var ai = 0; ai < ks.length; ai++) {
          if (!sourceFilterState[ks[ai]]) return false;
        }
        return true;
      }

      function allCustomLevelFiltersOn() {
        if (!customLevelOrderedKeys.length) return true;
        for (var ci = 0; ci < customLevelOrderedKeys.length; ci++) {
          if (!customLevelFilterState[customLevelOrderedKeys[ci]]) return false;
        }
        return true;
      }

      function syncUrlToLocation() {
        urlTimer = null;
        var u;
        try {
          u = new URL(window.location.href);
        } catch (e2) {
          return;
        }
        var p = u.searchParams;
        ["q", "s1", "d1", "s2", "d2", "s3", "d3", "src", "cl", "tcols", "dcols", "ir", "ch", "pg", "ps", "tb"].forEach(function (k) {
          p.delete(k);
        });
        var qv = (q.value || "").trim();
        if (qv) p.set("q", qv);
        var sortPairs = [
          ["s1", sortCol1, "d1", sortDir1],
          ["s2", sortCol2, "d2", sortDir2],
          ["s3", sortCol3, "d3", sortDir3]
        ];
        for (var si = 0; si < sortPairs.length; si++) {
          var sp = sortPairs[si];
          var spec = sp[1] && String(sp[1].value || "").trim();
          if (spec) {
            p.set(sp[0], spec);
            p.set(sp[2], sp[3] && sp[3].value === "desc" ? "desc" : "asc");
          }
        }
        if (!allSourceFiltersOn()) {
          var en = Object.keys(sourceFilterState).filter(function (k) {
            return sourceFilterState[k];
          });
          p.set("src", en.join(","));
        }
        if (customLevelOrderedKeys.length && !allCustomLevelFiltersOn()) {
          var enCl = customLevelOrderedKeys.filter(function (k) {
            return customLevelFilterState[k];
          });
          if (enCl.length === 0) p.set("cl", "");
          else
            p.set(
              "cl",
              enCl
                .map(function (k) {
                  return encodeURIComponent(k);
                })
                .join(",")
            );
        }
        if (!visEqualDefaults()) {
          p.set(
            "tcols",
            allTKeys
              .filter(function (k) {
                return visT[k];
              })
              .join(",")
          );
          p.set(
            "dcols",
            allDKeys
              .filter(function (k) {
                return visD[k];
              })
              .join(",")
          );
          if (visIr !== defaultVisIr) p.set("ir", visIr ? "1" : "0");
          if (visChart !== defaultVisChart) p.set("ch", visChart ? "1" : "0");
        }
        if (currentPage > 1) p.set("pg", String(currentPage));
        if (pageSize !== 150) p.set("ps", String(pageSize));
        if (toolbarPanel && toolbarToggle && !toolbarPanel.hidden) p.set("tb", "1");
        var nextSearch = p.toString();
        var next = u.pathname + (nextSearch ? "?" + nextSearch : "") + u.hash;
        var cur = window.location.pathname + window.location.search + window.location.hash;
        if (next !== cur) history.replaceState(null, "", next);
      }

      function scheduleUrlSync() {
        if (urlTimer) clearTimeout(urlTimer);
        urlTimer = setTimeout(syncUrlToLocation, 320);
      }

      function updatePaginationUi(totalFiltered, totalPages) {
        if (!paginationBar) return;
        if (totalFiltered <= pageSize) {
          paginationBar.hidden = true;
          return;
        }
        paginationBar.hidden = false;
        if (pageIndicator) pageIndicator.textContent = currentPage + " / " + totalPages + " ページ";
        if (pagePrev) pagePrev.disabled = currentPage <= 1;
        if (pageNext) pageNext.disabled = currentPage >= totalPages;
        if (pageFirst) pageFirst.disabled = currentPage <= 1;
        if (pageLast) pageLast.disabled = currentPage >= totalPages;
        if (pageJump) {
          pageJump.min = "1";
          pageJump.max = String(totalPages);
          pageJump.value = String(currentPage);
        }
      }

      function refresh() {
        var list = filteredList();
        var totalFiltered = list.length;
        var totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize) || 1);
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;
        var start = (currentPage - 1) * pageSize;
        var slice = list.slice(start, start + pageSize);
        render(slice);
        if (countEl) {
          countEl.textContent =
            slice.length + " / " + totalFiltered + " 行（このページ） / データ " + rows.length + " 行";
        }
        updatePaginationUi(totalFiltered, totalPages);
        scheduleUrlSync();
      }

      buildColPicker();
      rebuildThead(visibleKeys(allTKeys, visT), visibleKeys(allDKeys, visD));
      colbarEl.hidden = false;

      refresh();
      q.disabled = false;
      var qTimer = null;
      q.addEventListener("input", function () {
        currentPage = 1;
        if (qTimer) clearTimeout(qTimer);
        qTimer = setTimeout(function () {
          refresh();
        }, 200);
      });
      [sortCol1, sortDir1, sortCol2, sortDir2, sortCol3, sortDir3].forEach(function (el) {
        if (el)
          el.addEventListener("change", function () {
            currentPage = 1;
            refresh();
          });
      });
      if (pagePrev)
        pagePrev.addEventListener("click", function () {
          if (currentPage > 1) {
            currentPage -= 1;
            refresh();
          }
        });
      if (pageNext)
        pageNext.addEventListener("click", function () {
          currentPage += 1;
          refresh();
        });
      function goToJumpPage() {
        if (!pageJump) return;
        var listG = filteredList();
        var tpG = Math.max(1, Math.ceil(listG.length / pageSize) || 1);
        var want = parseInt(String(pageJump.value || "").trim(), 10);
        if (!Number.isFinite(want)) return;
        if (want < 1) want = 1;
        if (want > tpG) want = tpG;
        currentPage = want;
        refresh();
      }
      if (pageFirst)
        pageFirst.addEventListener("click", function () {
          if (currentPage > 1) {
            currentPage = 1;
            refresh();
          }
        });
      if (pageLast)
        pageLast.addEventListener("click", function () {
          var listL = filteredList();
          var tp = Math.max(1, Math.ceil(listL.length / pageSize) || 1);
          if (currentPage < tp) {
            currentPage = tp;
            refresh();
          }
        });
      if (pageGo && pageJump) {
        pageGo.addEventListener("click", goToJumpPage);
        pageJump.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter") {
            ev.preventDefault();
            goToJumpPage();
          }
        });
      }

      if (toolbarToggle)
        toolbarToggle.addEventListener("click", function () {
          setTimeout(scheduleUrlSync, 0);
        });

      scrollEl.hidden = false;
    })
    .catch(function (e) {
      if (loadStatus) loadStatus.hidden = true;
      if (mainContent) mainContent.setAttribute("aria-busy", "false");
      if (errEl) {
        errEl.textContent =
          "一覧データの読み込みに失敗しました。ネットワークやビルド成果物（table/browser_rows.json）を確認してください。詳細: " +
          String(e.message || e);
        errEl.hidden = false;
      }
      if (reloadBtn) {
        reloadBtn.hidden = false;
        reloadBtn.onclick = function () {
          location.reload();
        };
      }
    });
})();
