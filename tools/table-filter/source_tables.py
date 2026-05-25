"""
難易度表ソース設定の正規化。

- `source_tables_path` で別 JSON から配列を読み込み（肥大化したソース一覧向け）
- `source_tables`（オブジェクト配列）を推奨。各要素に任意で `custom_level_mapping` を同梱可能
- 後方互換: `source_header_urls` + `source_table_display_names` + `source_table_short_names`
- 後方互換: トップレベル `custom_level_mapping` 配列（エントリ内に無いインデックスのみ適用）
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping, MutableMapping


def normalize_level_map(raw: Any) -> dict[str, Any]:
    """レベル写像オブジェクトを正規化（キーは文字列に揃える）。"""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        key = str(k).strip()
        if key:
            out[key] = v
    return out


def _load_json_file(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_source_tables_path(cfg: MutableMapping[str, Any], *, config_path: str) -> None:
    """
    `source_tables_path` があれば、その JSON を読み `cfg["source_tables"]` に設定する。
    相対パスは filter_config.json があるディレクトリ基準。
    ファイルが指定されている場合はインラインの `source_tables` より優先する。
    """
    rel = str(cfg.get("source_tables_path") or "").strip()
    if not rel:
        return
    base = os.path.dirname(os.path.abspath(config_path))
    fp = rel if os.path.isabs(rel) else os.path.normpath(os.path.join(base, rel))
    if not os.path.isfile(fp):
        raise FileNotFoundError(f"source_tables_path が指すファイルがありません: {fp}")
    raw_file = _load_json_file(fp)
    if isinstance(raw_file, list):
        cfg["source_tables"] = raw_file
    elif isinstance(raw_file, dict) and isinstance(raw_file.get("source_tables"), list):
        cfg["source_tables"] = raw_file["source_tables"]
    else:
        raise ValueError(
            f"source_tables_path の JSON は配列か、{{\"source_tables\": [...]}} 形式である必要があります: {fp}"
        )


def load_resolved_filter_config(config_path: str) -> dict[str, Any]:
    """filter_config を読み、`source_tables_path` を解決した辞書を返す。"""
    with open(config_path, encoding="utf-8") as f:
        cfg: dict[str, Any] = json.load(f)
    resolve_source_tables_path(cfg, config_path=config_path)
    return cfg


def extract_source_table_entries(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    """
    有効な難易度表ソースのエントリ一覧（各要素は header_url / display_name / short_name / custom_level_mapping 等を含み得る）。
    """
    raw = cfg.get("source_tables")
    out: list[dict[str, Any]] = []
    if isinstance(raw, list) and raw:
        for item in raw:
            if not isinstance(item, dict):
                continue
            u = str(item.get("header_url") or item.get("url") or "").strip()
            if not u:
                continue
            e = dict(item)
            e["header_url"] = u
            out.append(e)
        if out:
            return out

    urls_raw = cfg.get("source_header_urls")
    out_urls: list[str] = []
    if isinstance(urls_raw, list):
        out_urls = [str(u).strip() for u in urls_raw if str(u).strip()]
    if not out_urls:
        single = str(cfg.get("source_header_url") or "").strip()
        if single:
            out_urls = [single]

    n = len(out_urls)
    disp_raw = cfg.get("source_table_display_names")
    short_raw = cfg.get("source_table_short_names")
    legacy_maps = cfg.get("custom_level_mapping")
    for i in range(n):
        d = ""
        if isinstance(disp_raw, list) and i < len(disp_raw):
            d = str(disp_raw[i]).strip()
        s = ""
        if isinstance(short_raw, list) and i < len(short_raw):
            s = str(short_raw[i]).strip()
        ent: dict[str, Any] = {"header_url": out_urls[i], "display_name": d, "short_name": s}
        if isinstance(legacy_maps, list) and i < len(legacy_maps) and isinstance(legacy_maps[i], dict):
            ent["custom_level_mapping"] = dict(legacy_maps[i])
        out.append(ent)
    return out


def normalize_source_tables(cfg: Mapping[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """
    戻り値: (header_urls, display_names, short_names) を同じ長さで揃える。
    display_names / short_names の要素は空文字のとき、呼び出し側でヘッダー JSON 名にフォールバックする。
    """
    entries = extract_source_table_entries(cfg)
    urls = [str(e["header_url"]).strip() for e in entries]
    displays = [str(e.get("display_name") or "").strip() for e in entries]
    shorts = [str(e.get("short_name") or "").strip() for e in entries]
    return urls, displays, shorts


def effective_custom_level_maps(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    """
    ソースごとのレベル写像（正規化済み辞書）のリスト。
    各 `source_tables[]` の `custom_level_mapping` を優先し、無いインデックスは
    トップレベル `custom_level_mapping` の同インデックスでフォールバックする。
    """
    entries = extract_source_table_entries(cfg)
    legacy = cfg.get("custom_level_mapping")
    maps: list[dict[str, Any]] = []
    for i, ent in enumerate(entries):
        emb = ent.get("custom_level_mapping")
        m = normalize_level_map(emb) if isinstance(emb, dict) else {}
        if not m and isinstance(legacy, list) and i < len(legacy):
            m = normalize_level_map(legacy[i])
        maps.append(m)
    return maps


def uses_explicit_source_table_objects(cfg: Mapping[str, Any]) -> bool:
    """分割配列ではなく、`source_tables` または `source_tables_path` でオブジェクト形式を使っているか。"""
    if str(cfg.get("source_tables_path") or "").strip():
        return True
    raw = cfg.get("source_tables")
    return isinstance(raw, list) and bool(raw)
