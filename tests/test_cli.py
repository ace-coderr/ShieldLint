"""CLI behaviour: exit codes, JSON/SARIF output, address + uri helpers."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from shieldlint.cli import main

from .fixtures import TADDR, UA_SHIELDED, URI_SHIELDED, URI_TRANSPARENT


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_version(self) -> None:
        code, out, _ = run_cli("version")
        self.assertEqual(code, 0)
        self.assertIn("shieldlint", out)

    def test_rules_json(self) -> None:
        code, out, _ = run_cli("rules", "--format", "json")
        self.assertEqual(code, 0)
        rules = json.loads(out)
        self.assertEqual(len({r["id"] for r in rules}), 14)
        self.assertTrue(all("slug" in r and "rationale" in r for r in rules))

    def test_check_clean_and_failing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clean = Path(tmp) / "clean.py"
            clean.write_text(f'ADDR = "{UA_SHIELDED}"\n', encoding="utf-8")
            code, out, _ = run_cli("check", str(clean), "--no-color")
            self.assertEqual(code, 0)
            self.assertIn("no findings", out)

            dirty = Path(tmp) / "dirty.py"
            dirty.write_text(f'ADDR = "{TADDR}"\n', encoding="utf-8")
            code, out, _ = run_cli("check", str(dirty), "--no-color")
            # SL002 is a warning; default fail_on=error keeps CI green
            self.assertEqual(code, 0)
            self.assertIn("SL002", out)

            code, _, _ = run_cli(
                "check", str(dirty), "--no-color", "--fail-on", "warning"
            )
            self.assertEqual(code, 1)

    def test_json_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dirty = Path(tmp) / "dirty.py"
            dirty.write_text(f'ADDR = "{TADDR}"\n', encoding="utf-8")
            report = Path(tmp) / "report.json"
            code, _, _ = run_cli(
                "check", str(dirty), "--format", "json", "-o", str(report)
            )
            self.assertEqual(code, 0)
            payload = json.loads(report.read_text())
            self.assertEqual(payload["summary"]["errors"], 0)
            self.assertEqual(payload["summary"]["warnings"], 1)
            self.assertEqual(payload["findings"][0]["rule"], "SL002")

    def test_sarif_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dirty = Path(tmp) / "dirty.py"
            dirty.write_text(f'URI = "{URI_TRANSPARENT}"\n', encoding="utf-8")
            report = Path(tmp) / "report.sarif"
            run_cli("check", str(dirty), "--format", "sarif", "-o", str(report))
            payload = json.loads(report.read_text())
            self.assertEqual(payload["version"], "2.1.0")
            result = payload["runs"][0]["results"][0]
            self.assertEqual(result["ruleId"], "SL010")
            self.assertEqual(result["level"], "error")

    def test_missing_path(self) -> None:
        code, _, err = run_cli("check", "/nonexistent/path")
        self.assertEqual(code, 2)
        self.assertIn("path not found", err)

    def test_fail_on_never(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dirty = Path(tmp) / "dirty.py"
            dirty.write_text(f'ADDR = "{TADDR}"\n', encoding="utf-8")
            code, _, _ = run_cli("check", str(dirty), "--fail-on", "never")
            self.assertEqual(code, 0)

    def test_address_command(self) -> None:
        code, out, _ = run_cli("address", UA_SHIELDED)
        self.assertEqual(code, 0)
        self.assertIn("unified", out)
        self.assertIn("orchard", out)
        self.assertIn("shielded   yes", out)

    def test_address_command_invalid(self) -> None:
        code, out, _ = run_cli("address", "t1notarealaddress")
        self.assertEqual(code, 1)

    def test_uri_command(self) -> None:
        code, out, _ = run_cli("uri", URI_SHIELDED)
        self.assertEqual(code, 0)
        self.assertIn("valid", out)
        code, out, _ = run_cli("uri", URI_TRANSPARENT)
        self.assertEqual(code, 0)  # valid ZIP 321, just public
        self.assertIn("transparent-p2pkh", out)

    def test_uri_command_invalid(self) -> None:
        code, out, _ = run_cli("uri", "zcash:t1abc?amount=1.2.3")
        self.assertEqual(code, 1)
        self.assertIn("INVALID", out)


if __name__ == "__main__":
    unittest.main()
