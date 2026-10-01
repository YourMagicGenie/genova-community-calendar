"""The Genova planning workflow must fail closed before collection exists."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from plan_genova_collection import plan  # noqa: E402


class GenovaScopeTest(unittest.TestCase):
    def test_missing_or_upstream_scope_is_rejected(self):
        for requested, configured in [
            ("", "genova"),
            ("all", "genova"),
            ("bloomington", "genova"),
            ("genova,bloomington", "genova"),
            ("genova", ""),
            ("genova", "all"),
            ("genova", "Genova,bloomington"),
        ]:
            with self.subTest(requested=requested, configured=configured):
                with self.assertRaises(ValueError):
                    plan(requested, configured)

    def test_explicit_genova_scope_is_read_only(self):
        self.assertEqual(
            plan("genova", "genova"),
            {"scope": "genova", "approved_sources": [], "collection_enabled": False, "writes_enabled": False},
        )
