import json
import subprocess
import sys
from pathlib import Path


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


def test_manual_workflow_has_no_schedule_or_write_permissions():
    workflow_path = REPO_ROOT / ".github/workflows/genova-agent-fixture.yml"
    assert workflow_path.exists(), "fixture workflow is required for the remote run"
    workflow = workflow_path.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "contents: read" in workflow
    assert "contents: write" not in workflow
    assert "mode: fixture" in workflow
