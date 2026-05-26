"""
Contract: minimal filtered_data + build_pages_table produces browser_rows.json
that passes check_browser_rows_pages_ui (meta.pages_ui from real pages_ui_config).

Catches regressions where new columns break pages_ui embedding without CI noticing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from check_browser_rows_pages_ui import validate_browser_rows

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD_SCRIPT = REPO_ROOT / "tools" / "table-filter" / "build_pages_table.py"
PAGES_UI = REPO_ROOT / "docs" / "table" / "pages_ui_config.json"


class TestFilterBuildPagesContract(unittest.TestCase):
    def test_build_pages_then_check_browser_rows_pages_ui(self) -> None:
        if not PAGES_UI.is_file():
            self.skipTest("pages_ui_config.json が無いためスキップ")
        if not BUILD_SCRIPT.is_file():
            self.skipTest("build_pages_table.py が無いためスキップ")

        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            filtered_path = tdir / "filtered_data.json"
            # One row with valid-length hashes (no songdata.db: db column stays null).
            filtered_path.write_text(
                json.dumps(
                    [
                        {
                            "title": "contract-fixture",
                            "md5": "a" * 32,
                            "sha256": "b" * 64,
                            "level": "1",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cfg_path = tdir / "filter_config.contract.json"
            cfg = {
                "output_dir": str(tdir),
                "output_data_filename": "filtered_data.json",
                "output_data_enriched_filename": "filtered_data_enriched.json",
                "browser_rows_filename": "browser_rows.json",
                "songdata_db": str(tdir / "no_such_songdata.db"),
                "pages_ui_config_path": str(PAGES_UI.resolve()),
                "sql_where": "minbpm IS NOT NULL",
                "source_tables": [
                    {
                        "header_url": "https://example.invalid/contract-header.json",
                        "display_name": "ContractFixture",
                    }
                ],
                "page_title": "Contract fixture",
            }
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            proc = subprocess.run(
                [sys.executable, str(BUILD_SCRIPT), "--config", str(cfg_path)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            self.assertEqual(
                proc.returncode,
                0,
                f"build_pages_table failed:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
            )

            out_path = tdir / "browser_rows.json"
            self.assertTrue(out_path.is_file(), "browser_rows.json was not written")
            data = json.loads(out_path.read_text(encoding="utf-8"))
            errs = validate_browser_rows(data)
            self.assertEqual(
                errs,
                [],
                "check_browser_rows_pages_ui should accept pipeline output: " + "; ".join(errs),
            )
            self.assertIsInstance(data.get("rows"), list)
            self.assertEqual(len(data["rows"]), 1)


if __name__ == "__main__":
    unittest.main()
