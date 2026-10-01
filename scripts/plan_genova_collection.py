"""Read-only scope check for the Genova collection planning workflow.

Collection remains unavailable until approved sources, a fork-owned backend,
and server-side admin authorization are implemented and reviewed.
"""

import argparse
import json


def plan(requested: str, configured: str) -> dict:
    if requested != "genova" or configured != "genova":
        raise ValueError(
            "Refusing collection: both the requested scope and the reviewed "
            "ENABLED_CITIES repository variable must be exactly 'genova'."
        )
    return {
        "scope": "genova",
        "approved_sources": [],
        "collection_enabled": False,
        "writes_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Show the Genova-only, read-only collection plan")
    parser.add_argument("--scope", required=True)
    parser.add_argument("--enabled-cities", required=True)
    args = parser.parse_args()
    try:
        result = plan(args.scope, args.enabled_cities)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    print("No sources will be scanned and no data will be written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
