import json
import unittest
from pathlib import Path

from check_browser_rows_pages_ui import validate_browser_rows, validate_pages_ui


class TestValidatePagesUi(unittest.TestCase):
    def test_minimal_valid(self) -> None:
        pu = {
            "column_widths": {"t:title": "40ch", "chart": "4rem"},
            "column_visible_defaults": {"table": {"title": True}, "db": {"minbpm": True}},
            "index_table": {
                "table_column_order": ["title"],
                "db_column_order": ["minbpm"],
                "ir_subcolumns": [
                    {
                        "colgroup_key": "ir:lr2ir",
                        "href_template": "http://example/?md5={value}",
                        "hash_kind": "md5",
                    }
                ],
                "chart_column": {
                    "colgroup_key": "chart",
                    "href_template": "https://example/?md5={value}",
                    "hash_kind": "md5",
                },
            },
        }
        self.assertEqual(validate_pages_ui(pu), [])

    def test_missing_ir(self) -> None:
        pu = {
            "column_widths": {},
            "column_visible_defaults": {"table": {}, "db": {}},
            "index_table": {
                "table_column_order": [],
                "db_column_order": [],
                "ir_subcolumns": [],
                "chart_column": {"colgroup_key": "chart", "href_template": "x", "hash_kind": "md5"},
            },
        }
        err = validate_pages_ui(pu)
        self.assertTrue(any("ir_subcolumns" in e for e in err))

    def test_repo_browser_rows_if_present(self) -> None:
        path = Path(__file__).resolve().parents[3] / "docs" / "table" / "browser_rows.json"
        if not path.is_file():
            self.skipTest("browser_rows.json が無いためスキップ")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(validate_browser_rows(data), [])


if __name__ == "__main__":
    unittest.main()
