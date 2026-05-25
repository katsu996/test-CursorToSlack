"""source_tables 正規化・外部ファイル・レベルマップのテスト。"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from source_tables import (
    effective_custom_level_maps,
    load_resolved_filter_config,
    normalize_source_tables,
    resolve_source_tables_path,
)


class TestSourceTables(unittest.TestCase):
    def test_load_resolved_merges_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            st_path = os.path.join(td, "st.json")
            with open(st_path, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "header_url": "https://example.com/a.json",
                            "display_name": "A",
                            "short_name": "a",
                            "custom_level_mapping": {"1": 10},
                        }
                    ],
                    f,
                )
            cfg_path = os.path.join(td, "filter_config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "source_tables_path": "st.json",
                        "source_tables": [],
                        "custom_level_mapping": [{"2": 99}],
                    },
                    f,
                )
            cfg = load_resolved_filter_config(cfg_path)
            self.assertEqual(len(cfg["source_tables"]), 1)
            self.assertEqual(cfg["source_tables"][0]["header_url"], "https://example.com/a.json")
            maps = effective_custom_level_maps(cfg)
            self.assertEqual(maps[0].get("1"), 10)

    def test_effective_fallback_top_level(self) -> None:
        cfg = {
            "source_tables": [
                {"header_url": "https://x/1.json", "display_name": "", "short_name": ""},
                {"header_url": "https://x/2.json"},
            ],
            "custom_level_mapping": [{"5": 55}, {"9": 99}],
        }
        maps = effective_custom_level_maps(cfg)
        self.assertEqual(maps[0]["5"], 55)
        self.assertEqual(maps[1]["9"], 99)

    def test_embedded_overrides_legacy(self) -> None:
        cfg = {
            "source_tables": [
                {
                    "header_url": "https://x/1.json",
                    "custom_level_mapping": {"3": 33},
                }
            ],
            "custom_level_mapping": [{"3": 300}],
        }
        self.assertEqual(effective_custom_level_maps(cfg)[0]["3"], 33)

    def test_resolve_rejects_bad_file_shape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = os.path.join(td, "bad.json")
            with open(bad, "w", encoding="utf-8") as f:
                json.dump({"not_source_tables": []}, f)
            cfg_path = os.path.join(td, "fc.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"source_tables_path": "bad.json"}, f)
            with self.assertRaises(ValueError):
                load_resolved_filter_config(cfg_path)

    def test_normalize_legacy_split_arrays(self) -> None:
        cfg = {
            "source_header_urls": ["https://a/h.json", "https://b/h.json"],
            "source_table_display_names": ["Ta", ""],
            "source_table_short_names": ["sa", "sb"],
        }
        u, d, s = normalize_source_tables(cfg)
        self.assertEqual(u, ["https://a/h.json", "https://b/h.json"])
        self.assertEqual(d, ["Ta", ""])
        self.assertEqual(s, ["sa", "sb"])

    def test_resolve_mutates_cfg(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            st = os.path.join(td, "x.json")
            with open(st, "w", encoding="utf-8") as f:
                json.dump([{"header_url": "https://z/z.json"}], f)
            cfg = {"source_tables_path": "x.json", "source_tables": [{"header_url": "https://ignore/"}]}
            resolve_source_tables_path(cfg, config_path=os.path.join(td, "fc.json"))
            self.assertEqual(cfg["source_tables"][0]["header_url"], "https://z/z.json")


if __name__ == "__main__":
    unittest.main()
