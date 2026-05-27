from __future__ import annotations

import unittest

from beatoraja_rows import (
    apply_beatoraja_custom_level_to_level,
    normalize_beatoraja_chart_row,
    row_passes_beatoraja_strict_decoder,
    sanitize_chart_row_for_beatoraja,
    sanitize_header_for_beatoraja,
    strip_keys_cfg,
)


class TestBeatorajaRows(unittest.TestCase):
    def test_strict_decoder_requires_level_and_long_hash(self) -> None:
        self.assertFalse(row_passes_beatoraja_strict_decoder({"level": "12", "md5": "a" * 24}))
        self.assertTrue(
            row_passes_beatoraja_strict_decoder(
                {"level": "12", "md5": "a" * 32, "sha256": None, "title": "x"}
            )
        )

    def test_normalize_empty_title(self) -> None:
        row: dict = {"level": "1", "title": "   ", "md5": "b" * 32}
        normalize_beatoraja_chart_row(row)
        self.assertEqual(row["title"], "（無題）")

    def test_sanitize_strip_source_keys(self) -> None:
        sk = strip_keys_cfg({})
        raw = {"level": "1", "md5": "c" * 32, "source_table_index": 1, "title": "t"}
        clean = sanitize_chart_row_for_beatoraja(raw, sk)
        self.assertNotIn("source_table_index", clean)
        self.assertIn("level", clean)

    def test_sanitize_header_drops_empty_course(self) -> None:
        h: dict = {"name": "x", "course": []}
        sanitize_header_for_beatoraja(h, {})
        self.assertNotIn("course", h)

    def test_output_header_name_forces_name(self) -> None:
        h: dict = {"name": "old", "course": []}
        sanitize_header_for_beatoraja(h, {"output_header_name": "K"})
        self.assertEqual(h["name"], "K")

    def test_beatoraja_folder_tag(self) -> None:
        h: dict = {"name": "x", "tag": "☆", "course": []}
        sanitize_header_for_beatoraja(h, {"beatoraja_folder_tag": "K"})
        self.assertEqual(h["tag"], "K")

    def test_apply_custom_level_overwrites_level_and_strips_field(self) -> None:
        row: dict = {"level": "12", "custom_level": 24, "md5": "a" * 32, "title": "t"}
        apply_beatoraja_custom_level_to_level(row, {})
        self.assertEqual(row["level"], "24")
        self.assertNotIn("custom_level", row)

    def test_apply_custom_level_disabled_keeps_level(self) -> None:
        row: dict = {"level": "12", "custom_level": 24, "md5": "a" * 32}
        apply_beatoraja_custom_level_to_level(row, {"beatoraja_level_from_custom_level": False})
        self.assertEqual(row["level"], "12")
        self.assertNotIn("custom_level", row)


if __name__ == "__main__":
    unittest.main()
