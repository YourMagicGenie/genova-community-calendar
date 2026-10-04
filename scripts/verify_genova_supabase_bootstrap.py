#!/usr/bin/env python3
"""Fail-closed checks for the one-time Genova Supabase schema bootstrap."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_STARTING_MIGRATIONS = ["20261002104614"]
REQUIRED_POSTFLIGHT_TABLES = {
    "admin_users",
    "agent_runs",
    "events",
    "feeds",
    "feed_source_reviews",
}
REQUIRED_RLS_TABLES = {
    "admin_users",
    "agent_runs",
    "events",
    "feeds",
    "feed_source_reviews",
}
MIGRATION_NAME = re.compile(r"^(\d{14})_.+\.sql$")


class BootstrapStateError(ValueError):
    """Raised when remote state differs from the expected bootstrap state."""


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise BootstrapStateError(f"The database snapshot has an invalid {field} value.")
    if len(value) != len(set(value)):
        raise BootstrapStateError(f"The database snapshot has duplicate {field} values.")
    return sorted(value)


def parse_snapshot(raw: str) -> dict[str, Any]:
    """Parse JSON output from the Supabase CLI database query."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise BootstrapStateError("The database snapshot is not valid JSON.") from error

    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise BootstrapStateError("The database snapshot format is not recognized.")

    row = rows[0]
    versions = _string_list(row.get("migration_versions"), "migration history")
    relations = _string_list(row.get("public_relations"), "public relation")
    tables = _string_list(row.get("public_tables"), "public table")
    rls_tables = _string_list(row.get("public_rls_tables"), "RLS table")
    auth_user_count = row.get("auth_user_count")
    if isinstance(auth_user_count, bool) or not isinstance(auth_user_count, int) or auth_user_count < 0:
        raise BootstrapStateError("The database snapshot has an invalid Auth user count.")

    return {
        "migration_versions": versions,
        "public_relations": relations,
        "public_tables": tables,
        "public_rls_tables": rls_tables,
        "auth_user_count": auth_user_count,
    }


def local_migration_versions(migrations_dir: Path) -> list[str]:
    versions: list[str] = []
    for path in migrations_dir.glob("*.sql"):
        match = MIGRATION_NAME.fullmatch(path.name)
        if not match:
            raise BootstrapStateError(f"Migration filename is not timestamped: {path.name}")
        versions.append(match.group(1))
    if not versions:
        raise BootstrapStateError("No local Supabase migrations were found.")
    if len(versions) != len(set(versions)):
        raise BootstrapStateError("Local Supabase migration timestamps are duplicated.")
    return sorted(versions)


def verify_state(
    snapshot: dict[str, Any],
    stage: str,
    migrations_dir: Path = Path("supabase/migrations"),
) -> str:
    """Validate a preflight or postflight snapshot; unexpected state always stops."""
    if stage == "preflight":
        if snapshot["migration_versions"] != EXPECTED_STARTING_MIGRATIONS:
            raise BootstrapStateError("The remote migration history differs from the reviewed starting state.")
        if snapshot["public_relations"]:
            raise BootstrapStateError("The remote project already has public relations; no migration was applied.")
        if snapshot["auth_user_count"] != 0:
            raise BootstrapStateError("The remote project already has Auth users; no migration was applied.")
        return stage

    if stage != "postflight":
        raise BootstrapStateError("Unknown bootstrap verification stage.")

    expected_versions = local_migration_versions(migrations_dir)
    if snapshot["migration_versions"] != expected_versions:
        raise BootstrapStateError("The remote migration history does not match the repository migrations.")

    missing_tables = REQUIRED_POSTFLIGHT_TABLES - set(snapshot["public_tables"])
    if missing_tables:
        raise BootstrapStateError("The remote database is missing required Genova tables.")

    missing_rls = REQUIRED_RLS_TABLES - set(snapshot["public_rls_tables"])
    if missing_rls:
        raise BootstrapStateError("RLS is not enabled on all required Genova tables.")

    if snapshot["auth_user_count"] != 0:
        raise BootstrapStateError("Auth users appeared during schema bootstrap; review the project manually.")
    return stage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("preflight", "postflight"), required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--migrations-dir", type=Path, default=Path("supabase/migrations"))
    args = parser.parse_args()

    try:
        snapshot = parse_snapshot(args.snapshot.read_text(encoding="utf-8"))
        verify_state(snapshot, args.stage, args.migrations_dir)
    except (OSError, BootstrapStateError) as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.stage == "preflight":
        print("Preflight passed: expected migration history; no public tables or Auth users.")
    else:
        print("Postflight passed: migrations match; required tables exist with RLS enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
