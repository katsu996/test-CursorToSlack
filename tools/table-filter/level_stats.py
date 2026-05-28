"""レベル別集計用のバケット化・ソート（難易度表 JSON の level 列）。"""

from __future__ import annotations

from typing import Any

UNSET_LEVEL_LABEL = "(未設定)"


def level_bucket_for_stats(raw_lvl: Any) -> str:
    if raw_lvl is None:
        return UNSET_LEVEL_LABEL
    if isinstance(raw_lvl, bool):
        return str(raw_lvl).lower()
    if isinstance(raw_lvl, int):
        return str(raw_lvl)
    if isinstance(raw_lvl, float):
        if raw_lvl.is_integer():
            return str(int(raw_lvl))
        s = str(raw_lvl).strip()
        return s if s else UNSET_LEVEL_LABEL
    s = str(raw_lvl).strip()
    if not s:
        return UNSET_LEVEL_LABEL
    try:
        f = float(s.replace(",", ""))
        if f.is_integer():
            return str(int(f))
    except ValueError:
        pass
    return s


def sort_level_stat_keys(keys: list[str]) -> list[str]:
    def sort_key(k: str) -> tuple[int, float, str]:
        if k == UNSET_LEVEL_LABEL:
            return (2, 0.0, k)
        try:
            return (0, float(int(k)), k)
        except ValueError:
            pass
        try:
            return (1, float(k), k)
        except ValueError:
            return (1, 0.0, k)

    return sorted(keys, key=sort_key)


def merge_level_compare_rows(by_sql: dict[str, int], by_all: dict[str, int]) -> list[dict[str, Any]]:
    keys = sort_level_stat_keys(list(set(by_sql.keys()) | set(by_all.keys())))
    return [{"level": k, "after_sql": by_sql.get(k, 0), "before_sql": by_all.get(k, 0)} for k in keys]


def source_indices_for_merged_row(
    row: dict[str, Any],
    *,
    display_name_to_index: dict[str, int],
    short_name_to_index: dict[str, int],
) -> list[int]:
    """統合行が属する元難易度表インデックス（重複時は複数）。"""
    found: list[int] = []
    seen: set[int] = set()

    def add(idx: Any) -> None:
        if isinstance(idx, bool):
            return
        if isinstance(idx, int) and idx > 0 and idx not in seen:
            seen.add(idx)
            found.append(idx)
        elif isinstance(idx, float) and idx.is_integer():
            i = int(idx)
            if i > 0 and i not in seen:
                seen.add(i)
                found.append(i)

    names = row.get("source_table_names")
    if isinstance(names, list):
        for name in names:
            if not isinstance(name, str):
                continue
            n = name.strip()
            if n and n in display_name_to_index:
                add(display_name_to_index[n])

    shorts = row.get("source_table_short_names")
    if isinstance(shorts, list):
        for short in shorts:
            if not isinstance(short, str):
                continue
            s = short.strip()
            if s and s in short_name_to_index:
                add(short_name_to_index[s])

    add(row.get("source_table_index"))
    return found


def _source_columns_from_stats(source_stats: list[dict[str, Any]]) -> tuple[
    list[dict[str, Any]],
    dict[str, int],
    dict[str, int],
]:
    """元表の出現順（index 昇順）で source_columns と名前→index マップを作る。"""
    display_name_to_index: dict[str, int] = {}
    short_name_to_index: dict[str, int] = {}
    source_columns: list[dict[str, Any]] = []
    for src in source_stats:
        if not isinstance(src, dict):
            continue
        idx = src.get("index")
        if not isinstance(idx, int) or idx < 1:
            continue
        disp = str(src.get("display_name") or "").strip() or f"表 {idx}"
        short = str(src.get("short_name") or "").strip()
        source_columns.append({"index": idx, "display_name": disp, "short_name": short})
        display_name_to_index[disp] = idx
        if short:
            short_name_to_index[short] = idx
    source_columns.sort(key=lambda c: int(c["index"]))
    return source_columns, display_name_to_index, short_name_to_index


def _by_source_for_columns(
    per_src: dict[int, int],
    source_columns: list[dict[str, Any]],
) -> dict[str, int]:
    return {str(col["index"]): per_src.get(int(col["index"]), 0) for col in source_columns}


def _accumulate_custom_level_buckets(
    rows: list[dict[str, Any]],
    *,
    custom_level_field: str,
    display_name_to_index: dict[str, int],
    short_name_to_index: dict[str, int],
) -> tuple[dict[str, int], dict[str, dict[int, int]]]:
    merged_by_custom: dict[str, int] = {}
    by_custom_source: dict[str, dict[int, int]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_cl = row.get(custom_level_field)
        if raw_cl is None or raw_cl == "":
            bucket = UNSET_LEVEL_LABEL
        else:
            bucket = level_bucket_for_stats(raw_cl)
        merged_by_custom[bucket] = merged_by_custom.get(bucket, 0) + 1
        src_bucket = by_custom_source.setdefault(bucket, {})
        for src_idx in source_indices_for_merged_row(
            row,
            display_name_to_index=display_name_to_index,
            short_name_to_index=short_name_to_index,
        ):
            src_bucket[src_idx] = src_bucket.get(src_idx, 0) + 1
    return merged_by_custom, by_custom_source


def build_merged_custom_level_rows(
    rows_after_dedup: list[dict[str, Any]],
    *,
    custom_level_field: str,
    source_stats: list[dict[str, Any]],
    rows_before_dedup: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """独自レベル別の曲数（重複除去前後）と、元難易度表ごとの内訳列を返す。"""
    source_columns, display_name_to_index, short_name_to_index = _source_columns_from_stats(
        source_stats
    )

    merged_after, by_src_after = _accumulate_custom_level_buckets(
        rows_after_dedup,
        custom_level_field=custom_level_field,
        display_name_to_index=display_name_to_index,
        short_name_to_index=short_name_to_index,
    )
    before_rows = rows_before_dedup if rows_before_dedup is not None else rows_after_dedup
    merged_before, _by_src_before = _accumulate_custom_level_buckets(
        before_rows,
        custom_level_field=custom_level_field,
        display_name_to_index=display_name_to_index,
        short_name_to_index=short_name_to_index,
    )

    level_keys = sort_level_stat_keys(
        list(set(merged_after.keys()) | set(merged_before.keys()))
    )
    out_rows: list[dict[str, Any]] = []
    for level_key in level_keys:
        per_src = by_src_after.get(level_key, {})
        out_rows.append(
            {
                "level": level_key,
                "count": merged_after.get(level_key, 0),
                "count_before_dedup": merged_before.get(level_key, 0),
                "by_source": _by_source_for_columns(per_src, source_columns),
            }
        )
    return source_columns, out_rows
