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
    var pri = key === "table" ? runtime.table_column_order : runtime.db_column_order;
    var arr = Object.keys(s);
    var first = [];
    for (var p = 0; p < pri.length; p++) {
      if (s[pri[p]]) first.push(pri[p]);
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

  var metaEl = document.getElementById("meta");
  var metaDl = document.getElementById("meta-dl");
  var filterSrcBar = document.getElementById("filter-src-bar");
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

  fetch("./table/browser_rows.json", { cache: "no-store" })
    .then(function (r) {
      if (!r.ok) throw new Error("browser_rows.json を取得できません (" + r.status + ")");
      return r.json();
    })
    .then(function (data) {
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
        var keys = [];
        var ti;
        if (vTKeys.length) {
          for (ti = 0; ti < vTKeys.length; ti++) keys.push("t:" + vTKeys[ti]);
        } else keys.push("t:_empty");
        if (vDKeys.length) {
          for (ti = 0; ti < vDKeys.length; ti++) keys.push("d:" + vDKeys[ti]);
        } else keys.push("d:_empty");
        var irs = runtime.ir_subcolumns || [];
        for (var ii = 0; ii < irs.length; ii++) {
          if (irs[ii].colgroup_key) keys.push(String(irs[ii].colgroup_key));
        }
        if (runtime.chart_column && runtime.chart_column.colgroup_key) {
          keys.push(String(runtime.chart_column.colgroup_key));
        } else {
          keys.push("chart");
        }
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
      var pairs = [
        ["行数", meta.row_count],
        ["songdata と一致", meta.matched_songdata],
        ["SQL 条件", meta.sql_where]
      ];
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
      if (meta.custom_level_mapping_count) {
        pairs.push(
          ["独自レベル列", meta.custom_level_field],
          ["独自レベル元列", meta.custom_level_source_key],
          ["独自レベル未マップ時", meta.custom_level_unmapped],
          ["独自レベル マップ数（配列要素数）", meta.custom_level_mapping_count]
        );
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
        entries.forEach(function (e) {
          sourceFilterState[e.short] = true;
          var lab = document.createElement("label");
          var inp = document.createElement("input");
          inp.type = "checkbox";
          inp.checked = true;
          inp.addEventListener("change", function () {
            sourceFilterState[e.short] = inp.checked;
            refresh();
          });
          lab.appendChild(inp);
          lab.appendChild(document.createTextNode(e.short + "(" + e.label + ")"));
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

      var visT = {};
      var visD = {};
      allTKeys.forEach(function (k) {
        visT[k] = defaultColumnVisible(k, "table");
      });
      allDKeys.forEach(function (k) {
        visD[k] = defaultColumnVisible(k, "db");
      });

      function visibleKeys(allKeys, vis) {
        return allKeys.filter(function (k) {
          return vis[k];
        });
      }

      function rebuildThead(vTKeys, vDKeys) {
        thead.innerHTML = "";
        var gl = runtime.group_labels || {};
        var trh1 = document.createElement("tr");
        var thT = document.createElement("th");
        thT.colSpan = Math.max(1, vTKeys.length);
        thT.className = "group-t";
        thT.textContent = gl.table || "難易度表 JSON の列";
        trh1.appendChild(thT);
        var thD = document.createElement("th");
        thD.colSpan = Math.max(1, vDKeys.length);
        thD.className = "group-d";
        thD.textContent = gl.db || "songdata.db（song）の列";
        trh1.appendChild(thD);
        var thIr = document.createElement("th");
        var irCols = runtime.ir_subcolumns || [];
        thIr.colSpan = Math.max(1, irCols.length);
        thIr.className = "group-ir";
        thIr.textContent = gl.ir || "IR";
        trh1.appendChild(thIr);
        var thChart = document.createElement("th");
        thChart.colSpan = 1;
        thChart.className = "group-chart";
        thChart.textContent = gl.chart || "Chart";
        trh1.appendChild(thChart);
        thead.appendChild(trh1);

        var trh2 = document.createElement("tr");
        vTKeys.forEach(function (k) {
          var th = document.createElement("th");
          th.className = "group-t" + (PI.isTableClampKey(k, runtime) ? " cell-max" : "");
          th.textContent = PI.tableColTitle(k, runtime);
          trh2.appendChild(th);
        });
        if (!vTKeys.length) {
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
        irCols.forEach(function (col) {
          var thi = document.createElement("th");
          thi.className = "group-ir";
          thi.textContent = col.header || col.colgroup_key || "—";
          trh2.appendChild(thi);
        });
        var thChart2 = document.createElement("th");
        thChart2.className = "group-chart";
        thChart2.textContent = (runtime.chart_column && runtime.chart_column.header) || "Chart";
        trh2.appendChild(thChart2);
        thead.appendChild(trh2);
        rebuildColgroup(vTKeys, vDKeys);
        initColResize(trh2, vTKeys, vDKeys);
      }

      function buildColPicker() {
        colbarInner.innerHTML = "";
        function addGroup(title, cls, allKeys, vis, prefix) {
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
              var vT = visibleKeys(allTKeys, visT);
              var vD = visibleKeys(allDKeys, visD);
              rebuildThead(vT, vD);
              refresh();
            });
            lab.appendChild(inp);
            var span = document.createElement("span");
            span.textContent =
              prefix === "表: " ? "表: " + PI.tableColTitle(k, runtime) : "DB: " + PI.dbColTitle(k, runtime);
            lab.appendChild(span);
            picks.appendChild(lab);
          });
          wrap.appendChild(picks);
          colbarInner.appendChild(wrap);
        }
        addGroup("難易度表 JSON の列", "t", allTKeys, visT, "表: ");
        addGroup("songdata.db（song）の列", "d", allDKeys, visD, "DB: ");
      }

      function rowText(r) {
        var t = r.table || {};
        var d = r.db || {};
        var parts = [];
        allTKeys.forEach(function (k) {
          parts.push(fmt(t[k]));
        });
        allDKeys.forEach(function (k) {
          parts.push(fmt(d ? d[k] : ""));
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
          opt.textContent = "表: " + PI.tableColTitle(k, runtime);
          sortSelect.appendChild(opt);
        });
        allDKeys.forEach(function (k) {
          var opt = document.createElement("option");
          opt.value = "db:" + k;
          opt.textContent = "DB: " + PI.dbColTitle(k, runtime);
          sortSelect.appendChild(opt);
        });
      }

      fillSortSelect(sortCol1);
      fillSortSelect(sortCol2);
      fillSortSelect(sortCol3);
      if (allTKeys.indexOf("title") >= 0) {
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

      function render(list) {
        var vTKeys = visibleKeys(allTKeys, visT);
        var vDKeys = visibleKeys(allDKeys, visD);
        tbody.innerHTML = "";
        list.forEach(function (r) {
          var tr = document.createElement("tr");
          var t = r.table || {};
          var d = r.db || {};
          vTKeys.forEach(function (k) {
            tr.insertAdjacentHTML("beforeend", cellHtml(t[k], "table", k, runtime));
          });
          if (!vTKeys.length) tr.insertAdjacentHTML("beforeend", '<td class="empty">—</td>');
          vDKeys.forEach(function (k) {
            tr.insertAdjacentHTML("beforeend", cellHtml(d ? d[k] : "", "db", k, runtime));
          });
          if (!vDKeys.length) tr.insertAdjacentHTML("beforeend", '<td class="empty">—</td>');
          tr.insertAdjacentHTML("beforeend", irCellsHtml(t, runtime));
          tr.insertAdjacentHTML("beforeend", chartCellHtml(t, runtime));
          tbody.appendChild(tr);
        });
        countEl.textContent = list.length + " / " + rows.length + " 行を表示";
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

      function refresh() {
        render(applySort(applySourceFilter(applySearch())));
      }

      buildColPicker();
      rebuildThead(visibleKeys(allTKeys, visT), visibleKeys(allDKeys, visD));
      colbarEl.hidden = false;

      refresh();
      q.disabled = false;
      q.addEventListener("input", refresh);
      [sortCol1, sortDir1, sortCol2, sortDir2, sortCol3, sortDir3].forEach(function (el) {
        if (el) el.addEventListener("change", refresh);
      });

      scrollEl.hidden = false;
    })
    .catch(function (e) {
      errEl.textContent = "一覧データの読み込みに失敗しました: " + String(e.message || e);
      errEl.hidden = false;
    });
})();
