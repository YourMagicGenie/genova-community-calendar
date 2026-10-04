import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_genova_supabase_bootstrap import (
    BootstrapStateError,
    parse_snapshot,
    verify_state,
)


EXPECTED_START = ["20261002104614"]
REQUIRED_TABLES = {"admin_users", "agent_runs", "events", "feeds", "feed_source_reviews"}


def state(*, migrations=None, tables=None, rls_tables=None, auth_users=0):
    return {
        "rows": [
            {
                "migration_versions": EXPECTED_START if migrations is None else migrations,
                "public_tables": [] if tables is None else tables,
                "public_rls_tables": [] if rls_tables is None else rls_tables,
                "auth_user_count": auth_users,
            }
        ]
    }


class BootstrapGuardTests(unittest.TestCase):
    def test_workflow_limits_supabase_secrets_to_steps_that_need_them(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/supabase-bootstrap.yml").read_text(encoding="utf-8")
        job_environment = workflow.split("    steps:", maxsplit=1)[0]
        self.assertNotIn("secrets.SUPABASE_ACCESS_TOKEN", job_environment)
        self.assertNotIn("secrets.SUPABASE_DB_PASSWORD", job_environment)
        self.assertGreaterEqual(workflow.count("secrets.SUPABASE_ACCESS_TOKEN"), 5)
        self.assertGreaterEqual(workflow.count("secrets.SUPABASE_DB_PASSWORD"), 5)

    def test_preflight_accepts_only_the_known_empty_project_state(self):
        snapshot = parse_snapshot(json.dumps(state()))
        self.assertEqual(verify_state(snapshot, "preflight"), "preflight")

    def test_preflight_rejects_unexpected_migration_history(self):
        snapshot = parse_snapshot(json.dumps(state(migrations=["20260101000000", *EXPECTED_START])))
        with self.assertRaisesRegex(BootstrapStateError, "migration history"):
            verify_state(snapshot, "preflight")

    def test_preflight_rejects_existing_public_tables(self):
        snapshot = parse_snapshot(json.dumps(state(tables=["events"])))
        with self.assertRaisesRegex(BootstrapStateError, "public tables"):
            verify_state(snapshot, "preflight")

    def test_preflight_rejects_existing_auth_users(self):
        snapshot = parse_snapshot(json.dumps(state(auth_users=1)))
        with self.assertRaisesRegex(BootstrapStateError, "Auth users"):
            verify_state(snapshot, "preflight")

    def test_postflight_requires_all_local_migrations_and_core_rls_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            migrations_dir = Path(directory)
            versions = ["20260101000000", "20261002104614", "20261002112029"]
            for version in versions:
                (migrations_dir / f"{version}_test.sql").write_text("-- test\n", encoding="utf-8")
            snapshot = parse_snapshot(
                json.dumps(
                    state(
                        migrations=versions,
                        tables=sorted(REQUIRED_TABLES),
                        rls_tables=["admin_users", "agent_runs", "events", "feeds", "feed_source_reviews"],
                    )
                )
            )
            self.assertEqual(verify_state(snapshot, "postflight", migrations_dir), "postflight")

    def test_postflight_rejects_missing_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            migrations_dir = Path(directory)
            versions = ["20260101000000", "20261002104614", "20261002112029"]
            for version in versions:
                (migrations_dir / f"{version}_test.sql").write_text("-- test\n", encoding="utf-8")
            snapshot = parse_snapshot(
                json.dumps(
                    state(
                        migrations=versions[:-1],
                        tables=sorted(REQUIRED_TABLES),
                        rls_tables=["admin_users", "agent_runs", "feeds", "feed_source_reviews"],
                    )
                )
            )
            with self.assertRaisesRegex(BootstrapStateError, "migration history"):
                verify_state(snapshot, "postflight", migrations_dir)

    def test_postflight_rejects_sensitive_tables_without_rls(self):
        with tempfile.TemporaryDirectory() as directory:
            migrations_dir = Path(directory)
            versions = ["20260101000000", "20261002104614", "20261002112029"]
            for version in versions:
                (migrations_dir / f"{version}_test.sql").write_text("-- test\n", encoding="utf-8")
            snapshot = parse_snapshot(
                json.dumps(
                    state(
                        migrations=versions,
                        tables=sorted(REQUIRED_TABLES),
                        rls_tables=["admin_users", "events", "feeds", "feed_source_reviews"],
                    )
                )
            )
            with self.assertRaisesRegex(BootstrapStateError, "RLS"):
                verify_state(snapshot, "postflight", migrations_dir)

    def test_parser_fails_closed_when_cli_result_shape_changes(self):
        with self.assertRaisesRegex(BootstrapStateError, "snapshot format"):
            parse_snapshot(json.dumps({"rows": []}))


if __name__ == "__main__":
    unittest.main()
