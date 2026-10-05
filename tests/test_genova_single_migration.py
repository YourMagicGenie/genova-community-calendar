"""Guard later Genova migrations against drift and accidental multi-pushes."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_genova_single_migration import verify_single_migration
from scripts.verify_genova_supabase_bootstrap import BootstrapStateError, parse_snapshot


CORE = ["admin_users", "agent_runs", "events", "feeds", "feed_source_reviews"]
VERSIONS = ["20261002104614", "20261004211200"]


class SingleMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.migrations = Path(self.temp.name)
        for version in VERSIONS:
            (self.migrations / f"{version}_test.sql").write_text("-- fixture\n", encoding="utf-8")

    def snapshot(self, *, versions, rls=CORE):
        return parse_snapshot(json.dumps({"rows": [{
            "migration_versions": versions,
            "public_relations": CORE,
            "public_tables": CORE,
            "public_rls_tables": rls,
            "auth_user_count": 1,
        }]}))

    def test_parse_snapshot_accepts_direct_postgres_json_object(self):
        payload = {
            "migration_versions": VERSIONS,
            "public_relations": CORE,
            "public_tables": CORE,
            "public_rls_tables": CORE,
            "auth_user_count": 0,
        }
        snapshot = parse_snapshot(json.dumps(payload))
        self.assertEqual(snapshot["migration_versions"], VERSIONS)
        self.assertEqual(snapshot["public_rls_tables"], CORE)
        self.assertEqual(snapshot["auth_user_count"], 0)

    def test_preflight_accepts_only_the_newest_pending_migration(self):
        self.assertEqual(
            verify_single_migration(self.snapshot(versions=VERSIONS[:-1]), "preflight", self.migrations),
            VERSIONS[-1],
        )

    def test_preflight_rejects_more_than_one_pending_migration(self):
        with self.assertRaisesRegex(BootstrapStateError, "exactly the newest"):
            verify_single_migration(self.snapshot(versions=[]), "preflight", self.migrations)

    def test_preflight_rejects_unknown_remote_history(self):
        with self.assertRaisesRegex(BootstrapStateError, "absent from the repository"):
            verify_single_migration(
                self.snapshot(versions=["20261002104614", "20261003120000"]),
                "preflight",
                self.migrations,
            )

    def test_postflight_requires_matching_history_and_core_rls(self):
        self.assertEqual(
            verify_single_migration(self.snapshot(versions=VERSIONS), "postflight", self.migrations),
            VERSIONS[-1],
        )
        with self.assertRaisesRegex(BootstrapStateError, "Row Level Security"):
            verify_single_migration(
                self.snapshot(versions=VERSIONS, rls=CORE[:-1]), "postflight", self.migrations
            )


if __name__ == "__main__":
    unittest.main()
