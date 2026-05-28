from __future__ import annotations

import unittest

from level_stats import (
    build_merged_custom_level_rows,
    merge_level_compare_rows,
    sort_level_stat_keys,
    source_indices_for_merged_row,
)


class TestLevelStats(unittest.TestCase):
    def test_sort_numeric_then_unknown(self) -> None:
        keys = ["10", "2", "(未設定)", "foo"]
        out = sort_level_stat_keys(keys)
        self.assertEqual(out[0], "2")
        self.assertEqual(out[1], "10")
        self.assertEqual(out[-1], "(未設定)")

    def test_merge_compare_rows(self) -> None:
        rows = merge_level_compare_rows({"1": 2}, {"1": 5, "2": 1})
        self.assertTrue(any(r["level"] == "1" and r["after_sql"] == 2 and r["before_sql"] == 5 for r in rows))

    def test_source_indices_for_merged_row(self) -> None:
        idxs = source_indices_for_merged_row(
            {
                "source_table_index": 2,
                "source_table_names": ["通常難易度表", "第2通常難易度表"],
                "source_table_short_names": ["☆", "▽"],
            },
            display_name_to_index={"通常難易度表": 1, "第2通常難易度表": 2},
            short_name_to_index={"☆": 1, "▽": 2},
        )
        self.assertEqual(idxs, [1, 2])

    def test_build_merged_custom_level_rows_by_source(self) -> None:
        sources = [
            {"index": 1, "display_name": "通常難易度表", "short_name": "☆"},
            {"index": 2, "display_name": "第2通常難易度表", "short_name": "▽"},
        ]
        rows = [
            {"custom_level": 1, "source_table_index": 1, "source_table_names": ["通常難易度表"]},
            {
                "custom_level": 1,
                "source_table_index": 2,
                "source_table_names": ["通常難易度表", "第2通常難易度表"],
                "source_table_short_names": ["☆", "▽"],
            },
        ]
        cols, cl_rows = build_merged_custom_level_rows(
            rows, custom_level_field="custom_level", source_stats=sources
        )
        self.assertEqual(len(cols), 2)
        self.assertEqual(cl_rows[0]["level"], "1")
        self.assertEqual(cl_rows[0]["count"], 2)
        self.assertEqual(cl_rows[0]["by_source"], {"1": 2, "2": 1})


if __name__ == "__main__":
    unittest.main()
