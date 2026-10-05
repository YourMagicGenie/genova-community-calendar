#!/usr/bin/env python3
"""Fail closed on unexpected state in a one-migration Genova schema update."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.verify_genova_supabase_bootstrap import (
    BootstrapStateError,
    REQUIRED_RLS_TABLES,
    local_migration_versions,
    parse_snapshot,
)


def verify_single_migration(
    snapshot: dict,
    stage: str,
    migrations_dir: Path,
) -> str:
    local = local_migration_versions(migrations_dir)
    remote = snapshot["migration_versions"]
    if not set(remote).issubset(local):
        raise BootstrapStateError("Remote migration history contains versions absent from the repository.")

    missing_rls = REQUIRED_RLS_TABLES - set(snapshot["public_rls_tables"])
    if missing_rls:
        raise BootstrapStateError("Core Genova tables are missing Row Level Security.")

    if stage == "preflight":
        pending = sorted(set(local) - set(remote))
        if pending != [local[-1]]:
            raise BootstrapStateError("Expected exactly the newest local migration to be pending.")
        return pending[0]

    if stage == "postflight":
        if remote != local:
            raise BootstrapStateError("Postflight migration history does not match the repository.")
        return local[-1]

    raise BootstrapStateError("Unknown migration verification stage.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("preflight", "postflight"), required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--migrations-dir", type=Path, default=Path("supabase/migrations"))
    args = parser.parse_args()

    try:
        snapshot = parse_snapshot(args.snapshot.read_text(encoding="utf-8"))
        version = verify_single_migration(snapshot, args.stage, args.migrations_dir)
    except (OSError, BootstrapStateError) as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"{args.stage.capitalize()} passed for migration {version}; core RLS enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
