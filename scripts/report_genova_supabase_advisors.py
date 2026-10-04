#!/usr/bin/env python3
"""Print the Genova project's security advisors through the read-only Management API."""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    token = os.environ["SUPABASE_ACCESS_TOKEN"]
    project_ref = os.environ["PROJECT_REF"]
    url = f"https://api.supabase.com/v1/projects/{project_ref}/advisors/security"
    request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as error:
        detail = error.read(2048).decode("utf-8", errors="replace")
        print(f"Security Advisor API returned HTTP {error.code}: {detail}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"Could not read Security Advisor response: {error}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict) or not isinstance(payload.get("lints"), list):
        print("Security Advisor response has no lints list.", file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
