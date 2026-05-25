"""
`docs/table/pages_ui_config.json` 用の読み込み。

標準の `json.load` は `//` 行コメントや `/* */` を解釈しないため、
編集しやすい JSONC 風のファイルを読めるようにする（標準ライブラリのみ）。
"""

from __future__ import annotations

import json
from typing import Any


def strip_jsonc_style_comments(text: str) -> str:
    """ダブルクォート／シングルクォート文字列の外側だけで `//` と `/* */` を除去する。"""
    out: list[str] = []
    i = 0
    n = len(text)
    in_string: str | None = None
    escape = False
    while i < n:
        c = text[i]
        if in_string is not None:
            out.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == in_string:
                in_string = None
            i += 1
            continue
        if c in "\"'":
            in_string = c
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                i += 2
                while i < n and text[i] not in "\r\n":
                    i += 1
                continue
            if nxt == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i = min(i + 2, n)
                continue
        out.append(c)
        i += 1
    return "".join(out)


def load_pages_ui_config(path: str) -> dict[str, Any]:
    """pages_ui_config を読み込み、辞書で返す。ルートがオブジェクトでなければ空辞書。"""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    cleaned = strip_jsonc_style_comments(raw)
    loaded = json.loads(cleaned)
    return loaded if isinstance(loaded, dict) else {}
