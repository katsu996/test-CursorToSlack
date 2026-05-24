from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

# テスト実行時の import パス（tools/table-filter をルートに）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import filter_table  # noqa: E402


class TestBmstableResolve(unittest.TestCase):
    @mock.patch.object(filter_table, "fetch_bytes")
    def test_resolve_from_html_meta(self, fb: mock.MagicMock) -> None:
        fb.return_value = (
            b'<html><head><meta name="bmstable" content="sub/header.json" /></head></html>'
        )
        u = filter_table._resolve_bmstable_header_url("https://example.com/tables/page.html")
        self.assertEqual(u, "https://example.com/tables/sub/header.json")

    def test_json_url_passthrough(self) -> None:
        self.assertEqual(
            filter_table._resolve_bmstable_header_url("https://example.com/h.json"),
            "https://example.com/h.json",
        )


if __name__ == "__main__":
    unittest.main()
