#!/usr/bin/env python3
"""Verify the one-off reviewed Oct 6 Genova migration batch before db push."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.verify_genova_supabase_bootstrap import (
    BootstrapStateError,
    REQUIRED_RLS_TABLES,
    local_migration_versions,
    parse_snapshot,
)

EXPECTED_PENDING = [
    "20261006124729",
    "20261006130000",
]


def verify_reviewed_batch(snapshot: dict, migrations_dir: Path) -> list[str]:
    local = local_migration_versions(migrations_dir)
    remote = snapshot["migration_versions"]
    if not set(remote).issubset(local):
        raise BootstrapStateError("Remote migration history contains versions absent from the repository.")
    missing_rls = REQUIRED_RLS_TABLES - set(snapshot["public_rls_tables"])
    if missing_rls:
        raise BootstrapStateError("Core Genova tables are missing Row Level Security.")
    pending = sorted(set(local) - set(remote))
    if pending != EXPECTED_PENDING:
        raise BootstrapStateError(
            "Expected exactly the reviewed Oct 6 persistence + submissions migration batch to be pending."
        )
    if local[-2:] != EXPECTED_PENDING:
        raise BootstrapStateError("Reviewed batch is no longer the exact tail of repository migration history.")
    return pending


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--migrations-dir", type=Path, default=Path("supabase/migrations"))
    args = parser.parse_args()
    try:
        snapshot = parse_snapshot(args.snapshot.read_text(encoding="utf-8"))
        pending = verify_reviewed_batch(snapshot, args.migrations_dir)
    except (OSError, BootstrapStateError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("Reviewed batch preflight passed: " + ", ".join(pending))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
