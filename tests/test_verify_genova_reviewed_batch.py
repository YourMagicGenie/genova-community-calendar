from pathlib import Path

import pytest

from scripts.verify_genova_reviewed_batch import EXPECTED_PENDING, verify_reviewed_batch
from scripts.verify_genova_supabase_bootstrap import BootstrapStateError, REQUIRED_RLS_TABLES


def write_migrations(root: Path, versions):
    root.mkdir()
    for version in versions:
        (root / f"{version}_fixture.sql").write_text("-- fixture\n", encoding="utf-8")


def snapshot(remote):
    return {
        "migration_versions": remote,
        "public_rls_tables": sorted(REQUIRED_RLS_TABLES),
    }


def test_reviewed_batch_requires_exact_two_migration_tail(tmp_path):
    older = ["20261005213000"]
    write_migrations(tmp_path / "migrations", older + EXPECTED_PENDING)
    assert verify_reviewed_batch(snapshot(older), tmp_path / "migrations") == EXPECTED_PENDING


@pytest.mark.parametrize(
    "remote",
    [
        ["20261005213000", "20261006124729"],
        [],
        ["20261005213000", "20990101000000"],
    ],
)
def test_reviewed_batch_fails_closed_on_unexpected_history(tmp_path, remote):
    write_migrations(tmp_path / "migrations", ["20261005213000"] + EXPECTED_PENDING)
    with pytest.raises(BootstrapStateError):
        verify_reviewed_batch(snapshot(remote), tmp_path / "migrations")
