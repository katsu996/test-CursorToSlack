"""sql_where のプリセット解決と安全検証（識別子ホワイトリスト）。"""

from __future__ import annotations

import re
import sys
from typing import Any, Mapping

# beatoraja の songdata.db（song テーブル）に基づく列名
SONG_TABLE_COLUMNS: frozenset[str] = frozenset(
    (
        "md5",
        "sha256",
        "title",
        "subtitle",
        "genre",
        "artist",
        "subartist",
        "tag",
        "path",
        "folder",
        "stagefile",
        "banner",
        "backbmp",
        "preview",
        "parent",
        "level",
        "difficulty",
        "maxbpm",
        "minbpm",
        "length",
        "mode",
        "judge",
        "feature",
        "content",
        "date",
        "favorite",
        "adddate",
        "notes",
        "charthash",
    )
)

# WHERE 断片でよく使う SQLite キーワード・リテラル（識別子として誤検知しない）
SQL_EXPRESSION_KEYWORDS: frozenset[str] = frozenset(
    (
        "and",
        "or",
        "not",
        "null",
        "is",
        "in",
        "between",
        "like",
        "glob",
        "regexp",
        "exists",
        "case",
        "when",
        "then",
        "else",
        "end",
        "cast",
        "as",
        "true",
        "false",
        "escape",
        "distinct",
        "collate",
    )
)

# プリセット名 → song WHERE 断片（括弧内にそのまま埋め込む）
SQL_WHERE_PRESETS: dict[str, str] = {
    "const_bpm": "minbpm IS NOT NULL AND maxbpm IS NOT NULL AND minbpm = maxbpm",
    "var_bpm": "minbpm IS NOT NULL AND maxbpm IS NOT NULL AND minbpm != maxbpm",
}

_IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def resolve_sql_where(cfg: Mapping[str, Any]) -> str:
    """
    sql_where_preset が非空ならプリセットの SQL のみを採用（自由記述 sql_where は無視）。
    未指定なら sql_where をそのまま使う。
    """
    preset_key = str(cfg.get("sql_where_preset") or "").strip()
    if preset_key:
        if preset_key not in SQL_WHERE_PRESETS:
            known = ", ".join(sorted(SQL_WHERE_PRESETS))
            die(f"sql_where_preset が不明です: {preset_key!r}（利用可能: {known}）")
        return SQL_WHERE_PRESETS[preset_key]
    return str(cfg.get("sql_where", "")).strip()


def validate_sql_where(fragment: str, *, strict_identifiers: bool) -> None:
    if not fragment or not fragment.strip():
        die("設定 sql_where（またはプリセット）が空です。例: minbpm IS NOT NULL AND maxbpm IS NOT NULL AND minbpm = maxbpm")
    frag = fragment.strip()
    if len(frag) > 500:
        die("sql_where が長すぎます（上限 500 文字）。")
    lower = frag.lower()
    banned_sub = (";", "--", "/*", "*/")
    for b in banned_sub:
        if b in frag:
            die(f"sql_where に禁止部分 {b!r} が含まれています。")
    banned_words = (
        "attach",
        "detach",
        "pragma",
        "sqlite_",
        "drop ",
        "delete ",
        "insert ",
        "update ",
        "create ",
        "replace ",
        "trigger ",
        "vacuum",
    )
    for w in banned_words:
        if w in lower:
            die(f"sql_where に禁止キーワードに該当する部分が含まれています: {w.strip()!r}")

    if strict_identifiers:
        for m in _IDENT_RE.finditer(frag):
            word = m.group(0).lower()
            if word in SQL_EXPRESSION_KEYWORDS:
                continue
            if word in SONG_TABLE_COLUMNS:
                continue
            die(
                f"sql_where に許可されていない識別子があります: {m.group(0)!r}。"
                " song テーブルの列名と SQLite の式キーワード以外は使えません。"
                " 高度な式が必要な場合は filter_config の sql_where_disable_identifier_whitelist を true にしてください"
                "（自己責任・信頼できる設定のみコミットしてください）。"
            )
