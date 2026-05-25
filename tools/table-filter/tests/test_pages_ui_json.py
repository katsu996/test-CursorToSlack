import json
import tempfile
import unittest
from pathlib import Path

from pages_ui_json import load_pages_ui_config, strip_jsonc_style_comments


class TestStripJsonc(unittest.TestCase):
    def test_line_comment_outside_string(self) -> None:
        s = '{"a": 1, // c\n "b": 2}'
        self.assertEqual(json.loads(strip_jsonc_style_comments(s)), {"a": 1, "b": 2})

    def test_line_comment_not_inside_double_quoted(self) -> None:
        s = '{"a": "http://x", "b": 2}'
        self.assertEqual(json.loads(strip_jsonc_style_comments(s)), {"a": "http://x", "b": 2})

    def test_block_comment(self) -> None:
        s = '{"a": 1 /* x */ , "b": 2}'
        self.assertEqual(json.loads(strip_jsonc_style_comments(s)), {"a": 1, "b": 2})

    def test_url_in_string_preserved(self) -> None:
        s = '{"url": "https://example.com/a//b"}'
        self.assertEqual(json.loads(strip_jsonc_style_comments(s)), {"url": "https://example.com/a//b"})


class TestLoadPagesUiConfig(unittest.TestCase):
    def test_load_file_with_comments(self) -> None:
        body = """// top
{
  "version": 1,
  "column_widths": {
    // "t:level": "6ch",
    "t:title": "40ch"
  },
  "column_visible_defaults": {
    "table": { // inline
      "id": false
    },
    "db": {}
  }
}
"""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".json") as tmp:
            tmp.write(body)
            path = tmp.name
        try:
            d = load_pages_ui_config(path)
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(d["version"], 1)
        self.assertEqual(d["column_widths"]["t:title"], "40ch")
        self.assertNotIn("t:level", d["column_widths"])
        self.assertEqual(d["column_visible_defaults"]["table"]["id"], False)

    def test_repo_pages_ui_has_index_table(self) -> None:
        repo = Path(__file__).resolve().parents[3] / "docs" / "table" / "pages_ui_config.json"
        d = load_pages_ui_config(str(repo))
        it = d.get("index_table")
        self.assertIsInstance(it, dict)
        self.assertIsInstance(it.get("table_column_order"), list)
        self.assertIsInstance(it.get("db_column_order"), list)
        self.assertIsInstance(it.get("column_labels"), dict)
        self.assertIsInstance(it.get("ir_subcolumns"), list)
        self.assertGreaterEqual(len(it["ir_subcolumns"]), 1)
        for col in it["ir_subcolumns"]:
            self.assertIn("colgroup_key", col)
            self.assertIn("href_template", col)
        cc = it.get("chart_column")
        self.assertIsInstance(cc, dict)
        self.assertEqual(cc.get("colgroup_key"), "chart")
        trail = it.get("trailing_table_columns")
        self.assertIsInstance(trail, list)
        self.assertIn("custom_level", trail)
