"""
難易度表ソース設定の正規化。

`source_tables`（オブジェクト配列）を推奨。後方互換のため
`source_header_urls` + `source_table_display_names` + `source_table_short_names`
も解釈する。
"""

from __future__ import annotations

from typing import Any, Mapping


def normalize_source_tables(cfg: Mapping[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """
    戻り値: (header_urls, display_names, short_names) を同じ長さで揃える。
    display_names / short_names の要素は空文字のとき、呼び出し側でヘッダー JSON 名にフォールバックする。
    """
    raw = cfg.get("source_tables")
    if isinstance(raw, list) and raw:
        urls: list[str] = []
        displays: list[str] = []
        shorts: list[str] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            u = str(item.get("header_url") or item.get("url") or "").strip()
            if not u:
                continue
            urls.append(u)
            displays.append(str(item.get("display_name") or "").strip())
            shorts.append(str(item.get("short_name") or "").strip())
        if urls:
            return urls, displays, shorts

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
    displays = []
    shorts = []
    for i in range(n):
        d = ""
        if isinstance(disp_raw, list) and i < len(disp_raw):
            d = str(disp_raw[i]).strip()
        displays.append(d)
        s = ""
        if isinstance(short_raw, list) and i < len(short_raw):
            s = str(short_raw[i]).strip()
        shorts.append(s)
    return out_urls, displays, shorts
