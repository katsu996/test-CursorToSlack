from __future__ import annotations

import unittest

from sql_where_guard import SQL_WHERE_PRESETS, resolve_sql_where, validate_sql_where


class TestSqlWhereGuard(unittest.TestCase):
    def test_preset_const_bpm(self) -> None:
        sql = resolve_sql_where({"sql_where_preset": "const_bpm", "sql_where": "1=1"})
        self.assertEqual(sql, SQL_WHERE_PRESETS["const_bpm"])

    def test_free_sql_when_no_preset(self) -> None:
        sql = resolve_sql_where({"sql_where": "minbpm = maxbpm"})
        self.assertEqual(sql, "minbpm = maxbpm")

    def test_unknown_preset_dies(self) -> None:
        with self.assertRaises(SystemExit):
            resolve_sql_where({"sql_where_preset": "nope"})

    def test_validate_bans_semicolon(self) -> None:
        with self.assertRaises(SystemExit):
            validate_sql_where("md5 = md5;", strict_identifiers=False)

    def test_strict_identifier_whitelist(self) -> None:
        validate_sql_where("minbpm IS NOT NULL AND maxbpm IS NOT NULL", strict_identifiers=True)
        with self.assertRaises(SystemExit):
            validate_sql_where("evil_column = 1", strict_identifiers=True)

    def test_strict_allows_keywords(self) -> None:
        validate_sql_where("minbpm IS NULL OR maxbpm IS NOT NULL", strict_identifiers=True)


if __name__ == "__main__":
    unittest.main()
