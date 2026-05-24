from __future__ import annotations

import unittest

from level_stats import merge_level_compare_rows, sort_level_stat_keys


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


if __name__ == "__main__":
    unittest.main()
