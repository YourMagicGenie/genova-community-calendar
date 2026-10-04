import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import genova_agent_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_fixture_run_is_offline_and_writes_no_public_events():
    runner_source = (REPO_ROOT / "scripts/genova_agent_fixture.py").read_text(encoding="utf-8")
    assert "urllib" not in runner_source
    assert "requests" not in runner_source
    assert "httpx" not in runner_source

    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/genova_agent_fixture.py"), "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report == {
        "candidate_count": 1,
        "sources_scanned": 0,
        "events_found": 2,
        "events_needing_review": 1,
        "events_added": 0,
        "events_updated": 0,
        "events_cancelled": 0,
        "source_failures": [],
    }


def test_fixture_source_and_events_are_explicitly_fictional():
    fixture_path = REPO_ROOT / "tests/fixtures/genova/agent-fixture.json"
    assert fixture_path.exists(), "fixture-only run must read a checked-in fictional fixture"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert fixture["fictional"] is True
    assert all(event["source_url"].startswith("https://example.org/") for event in fixture["events"])
    assert all(event["city"] == "genova" for event in fixture["events"])


@pytest.mark.parametrize("city", [None, "savona", "Genova"])
def test_fixture_rejects_events_without_the_exact_genova_city(city):
    fixture_path = REPO_ROOT / "tests/fixtures/genova/agent-fixture.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    event = fixture["events"][0]
    if city is None:
        event.pop("city", None)
    else:
        event["city"] = city

    with pytest.raises(ValueError, match="city must be genova"):
        genova_agent_fixture.validate_fixture(fixture)


def test_manual_workflow_has_no_schedule_or_write_permissions():
    workflow_path = REPO_ROOT / ".github/workflows/genova-agent-fixture.yml"
    assert workflow_path.exists(), "fixture workflow is required for the remote run"
    workflow = workflow_path.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "contents: read" in workflow
    assert "contents: write" not in workflow
    assert re.search(r"options:\s*\n\s*-\s*fixture(?:\s|$)", workflow)
    assert "${{ github.ref == 'refs/heads/main' && inputs.mode == 'fixture' }}" in workflow
    assert "environment: genova-agent-main" in workflow
    assert re.search(r"ref:\s*main\b", workflow)
    assert "steps.mark_succeeded.outcome == 'failure'" in workflow
