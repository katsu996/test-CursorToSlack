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
