#!/usr/bin/env python3
"""Send a small, allowlisted fixture-run update to the private Supabase callback."""

import argparse
import json
import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CALLBACK_URL = "https://eginljyhnnczeeqxwfia.supabase.co/functions/v1/genova-agent-callback"
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.I)
COUNT_FIELDS = (
    "candidate_count",
    "sources_scanned",
    "events_found",
    "events_needing_review",
    "events_added",
    "events_updated",
    "events_cancelled",
)
MAX_CALLBACK_ATTEMPTS = 3
RETRYABLE_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}


def make_payload(status, report_path=None):
    run_id = os.environ.get("RUN_ID", "")
    revision = os.environ.get("GITHUB_SHA", "")
    if not UUID_PATTERN.fullmatch(run_id) or not SHA_PATTERN.fullmatch(revision):
        raise ValueError("The workflow run ID or Git revision is invalid.")

    payload = {
        "run_id": run_id,
        "status": status,
        "instruction_revision": revision,
        **{field: 0 for field in COUNT_FIELDS},
        "source_failures": [],
        "error_summary": None,
    }
    if status == "succeeded":
        if not report_path:
            raise ValueError("A successful run needs its local fixture report.")
        with open(report_path, encoding="utf-8") as report_file:
            report = json.load(report_file)
        for field in COUNT_FIELDS:
            value = report.get(field)
            if not isinstance(value, int) or value < 0:
                raise ValueError("The fixture report contains an invalid count.")
            payload[field] = value
        if payload["sources_scanned"] != 0 or any(
            payload[field] != 0 for field in ("events_added", "events_updated", "events_cancelled")
        ):
            raise ValueError("Fixture mode cannot scan sources or write public events.")
    elif status == "failed":
        payload["error_summary"] = "Fixture validation failed."
    return payload


def send_callback(payload):
    secret = os.environ.get("GENOVA_AGENT_CALLBACK_TOKEN", "")
    if len(secret) < 24:
        raise ValueError("The callback credential is not configured.")
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    for attempt in range(MAX_CALLBACK_ATTEMPTS):
        request = Request(
            CALLBACK_URL,
            data=body,
            headers={
                "content-type": "application/json",
                "x-genova-agent-callback-secret": secret,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                if response.status != 200:
                    raise ValueError("Supabase did not accept the fixture run update.")
                return
        except HTTPError as error:
            if error.code not in RETRYABLE_HTTP_CODES or attempt + 1 == MAX_CALLBACK_ATTEMPTS:
                raise ValueError("Supabase rejected the fixture run update (HTTP " + str(error.code) + ").") from None
        except (URLError, TimeoutError):
            if attempt + 1 == MAX_CALLBACK_ATTEMPTS:
                raise ValueError("Supabase could not be reached to record the fixture run.") from None
        time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, choices=("running", "succeeded", "failed"))
    parser.add_argument("--report")
    args = parser.parse_args()
    try:
        send_callback(make_payload(args.status, args.report))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("Fixture run status recorded in the private admin history.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
