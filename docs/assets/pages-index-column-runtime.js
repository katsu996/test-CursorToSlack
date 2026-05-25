/**
 * 列順・ラベル・IR/Chart リンクなど index 表のランタイム設定。
 * 既定値は `docs/table/pages_ui_config.json` の `index_table` と同期すること（古い browser_rows 用のフォールバック）。
 */
(function (global) {
  "use strict";

  var DEFAULT_INDEX_TABLE = {
    table_column_order: [
      "id",
      "source_table_index",
      "source_table_short_names",
      "source_table_names",
      "title",
      "note",
      "artist",
      "level",
      "custom_level",
      "md5",
      "sha256"
    ],
    db_column_order: [
      "title",
      "subtitle",
      "subartist",
      "artist",
      "genre",
      "path",
      "minbpm",
      "maxbpm",
      "notes",
      "length",
      "level",
      "difficulty",
      "md5",
      "sha256",
      "folder",
      "preview",
      "banner",
      "stagefile",
      "backbmp",
      "tag",
      "parent",
      "mode",
      "judge",
      "feature",
      "content",
      "date",
      "adddate",
      "favorite",
      "charthash"
    ],
    table_clamp_keys: ["title", "note"],
    column_labels: {
      id: "表 ID",
      source_table_index: "出自表（番号）",
      source_table_short_names: "シンボル",
      source_table_names: "出自（フル）",
      md5: "MD5",
      sha256: "SHA256",
      title: "表タイトル",
      artist: "表アーティスト",
      note: "表メモ",
      level: "表レベル",
      custom_level: "独自レベル",
      url: "リンク",
      url_diff: "差分URL",
      subtitle: "サブタイトル",
      genre: "ジャンル",
      subartist: "サブアーティスト",
      folder: "フォルダID",
      difficulty: "difficulty",
      maxbpm: "max BPM",
      minbpm: "min BPM",
      length: "長さ(秒?)",
      notes: "ノーツ数",
      charthash: "charthash",
      date: "ファイル日時"
    },
    column_hidden_fallback: {
      id: true,
      source_table_index: true,
      source_table_names: true,
      path: true,
      preview: true,
      banner: true,
      stagefile: true,
      backbmp: true,
      tag: true,
      parent: true,
      mode: true,
      judge: true,
      feature: true,
      content: true,
      favorite: true,
      adddate: true,
      url: true,
      url_diff: true,
      source_header_json_url: true,
      source_table_register_url: true,
      folder: true
    },
    group_labels: {
      table: "難易度表 JSON の列",
      db: "songdata.db（song）の列",
      ir: "IR",
      chart: "Chart"
    },
    ir_subcolumns: [
      {
        colgroup_key: "ir:lr2ir",
        header: "LR2IR",
        hash_kind: "md5",
        href_template: "http://www.dream-pro.info/~lavalse/LR2IR/search.cgi?mode=ranking&bmsmd5={value}"
      },
      {
        colgroup_key: "ir:minir",
        header: "MinIR",
        hash_kind: "sha256",
        href_template: "https://www.gaftalk.com/minir/#/viewer/song/{value}/0"
      },
      {
        colgroup_key: "ir:mocha",
        header: "Mocha",
        hash_kind: "sha256",
        href_template: "https://mocha-repository.info/song.php?sha256={value}"
      }
    ],
    chart_column: {
      colgroup_key: "chart",
      header: "Chart",
      link_label: "Chart",
      hash_kind: "md5",
      href_template: "https://bms-score-viewer.pages.dev/view?md5={value}"
    }
  };

  function shallowCopy(obj) {
    var out = {};
    if (obj && typeof obj === "object") {
      var ks = Object.keys(obj);
      for (var i = 0; i < ks.length; i++) out[ks[i]] = obj[ks[i]];
    }
    return out;
  }

  /**
   * @param {Record<string, unknown>} pagesUi meta.pages_ui
   */
  function mergeIndexTable(pagesUi) {
    var def = DEFAULT_INDEX_TABLE;
    var it =
      pagesUi && pagesUi.index_table && typeof pagesUi.index_table === "object" ? pagesUi.index_table : {};
    var tableOrder = Array.isArray(it.table_column_order) && it.table_column_order.length
      ? it.table_column_order.slice()
      : def.table_column_order.slice();
    var dbOrder = Array.isArray(it.db_column_order) && it.db_column_order.length
      ? it.db_column_order.slice()
      : def.db_column_order.slice();
    var labels = Object.assign({}, def.column_labels, shallowCopy(it.column_labels));
    var clampKeys = Array.isArray(it.table_clamp_keys) && it.table_clamp_keys.length
      ? it.table_clamp_keys.slice()
      : def.table_clamp_keys.slice();
    var hiddenFb = Object.assign({}, def.column_hidden_fallback, shallowCopy(it.column_hidden_fallback));
    var groupLabels = Object.assign({}, def.group_labels, shallowCopy(it.group_labels));
    var irSubs =
      Array.isArray(it.ir_subcolumns) && it.ir_subcolumns.length
        ? it.ir_subcolumns.map(function (c) {
            return shallowCopy(c);
          })
        : def.ir_subcolumns.map(function (c) {
            return shallowCopy(c);
          });
    var chartCol = Object.assign({}, def.chart_column, shallowCopy(it.chart_column));
    return {
      table_column_order: tableOrder,
      db_column_order: dbOrder,
      column_labels: labels,
      table_clamp_keys: clampKeys,
      column_hidden_fallback: hiddenFb,
      group_labels: groupLabels,
      ir_subcolumns: irSubs,
      chart_column: chartCol
    };
  }

  function isTableClampKey(k, runtime) {
    return runtime.table_clamp_keys.indexOf(k) >= 0;
  }

  function tableColTitle(k, runtime) {
    return runtime.column_labels[k] || "表: " + k;
  }

  function dbColTitle(k, runtime) {
    return runtime.column_labels[k] || "DB: " + k;
  }

  global.KOriginalPagesIndex = {
    DEFAULT_INDEX_TABLE: DEFAULT_INDEX_TABLE,
    mergeIndexTable: mergeIndexTable,
    isTableClampKey: isTableClampKey,
    tableColTitle: tableColTitle,
    dbColTitle: dbColTitle
  };
})(typeof window !== "undefined" ? window : globalThis);
