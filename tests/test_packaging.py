"""Packaging sanity: the metadata must always parse."""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PyProjectTests(unittest.TestCase):
    def test_pyproject_parses(self) -> None:
        # A broken pyproject.toml breaks `pip install .` and, in practice,
        # serverless builds that install the project before bundling.
        with (ROOT / "pyproject.toml").open("rb") as fh:
            data = tomllib.load(fh)
        self.assertEqual(data["project"]["name"], "shieldlint")
        self.assertTrue(data["project"]["version"])

    def test_requirements_exist_where_the_builder_looks(self) -> None:
        self.assertTrue((ROOT / "requirements.txt").is_file())
        self.assertTrue((ROOT / "web" / "requirements.txt").is_file())


if __name__ == "__main__":
    unittest.main()
