"""beatoraja / jbmstable-parser 向けの行・ヘッダー整形。"""

from __future__ import annotations

import re
from typing import Any, Mapping, MutableMapping

from sql_where_guard import die

# jbmstable-parser の decodeJSONTableData(..., accept=false) に合わせ、
# Pages 用拡張キーはデータ部から除外する
DEFAULT_BEATORAJA_STRIP_CHART_KEYS: frozenset[str] = frozenset(
    (
        "source_table_index",
        "source_table_names",
        "source_table_short_names",
        "source_header_json_url",
        "source_table_register_url",
        "id",
    )
)


def validate_json_field_name(name: str, label: str) -> None:
    if not name:
        die(f"{label} が空です。")
    if len(name) > 64:
        die(f"{label} が長すぎます（上限 64 文字）。")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        die(f"{label} は英字またはアンダースコアで始まり、英数字とアンダースコアのみ使えます: {name!r}")


def strip_keys_cfg(cfg: Mapping[str, Any]) -> frozenset[str]:
    raw = cfg.get("beatoraja_strip_chart_keys")
    if raw is None:
        return DEFAULT_BEATORAJA_STRIP_CHART_KEYS
    if isinstance(raw, list):
        return frozenset(str(x).strip() for x in raw if str(x).strip())
    return DEFAULT_BEATORAJA_STRIP_CHART_KEYS


def sanitize_chart_row_for_beatoraja(row: Mapping[str, Any], strip_keys: frozenset[str]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k not in strip_keys}


def normalize_beatoraja_chart_row(row: MutableMapping[str, Any]) -> None:
    lv = row.get("level")
    if lv is not None and not isinstance(lv, str):
        row["level"] = str(lv).strip()

    for key in ("artist", "url", "url_diff"):
        v = row.get(key)
        if v is None:
            row[key] = ""
        elif not isinstance(v, str):
            row[key] = str(v)

    t = row.get("title")
    if t is None:
        row["title"] = "（無題）"
    elif not isinstance(t, str):
        row["title"] = str(t)
    if not str(row.get("title", "")).strip():
        row["title"] = "（無題）"

    for hkey in ("md5", "sha256"):
        hv = row.get(hkey)
        if hv is not None and not isinstance(hv, str):
            row[hkey] = str(hv)


def row_passes_beatoraja_strict_decoder(row: Mapping[str, Any]) -> bool:
    if row.get("level") is None:
        return False
    md5 = row.get("md5")
    sha = row.get("sha256")
    md5_ok = md5 is not None and len(str(md5).strip()) > 24
    sha_ok = sha is not None and len(str(sha).strip()) > 24
    return md5_ok or sha_ok


def sanitize_header_for_beatoraja(header: MutableMapping[str, Any], cfg: Mapping[str, Any]) -> None:
    c = header.get("course")
    if isinstance(c, list) and len(c) == 0:
        header.pop("course", None)

    forced = str(cfg.get("output_header_name") or "").strip()
    if forced:
        header["name"] = forced
    else:
        name = str(header.get("name") or "").strip()
        if not name:
            header["name"] = "Filtered difficulty table (songdata)"
