"""Check local Markdown link targets from the repository root.

Usage: python scripts/check_markdown_links.py
Remote URLs and fragment-only links are outside this file-existence check.
"""

from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+['\"][^'\"]*['\"])?\)")
FENCE = re.compile(r"^\s*(```|~~~)")


def main() -> int:
    broken = []
    for document in sorted(ROOT.rglob("*.md")):
        if any(part in {".git", "node_modules", ".venv"} for part in document.parts):
            continue
        in_fence = False
        for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for match in LINK.finditer(line):
                href = match.group(1) or match.group(2)
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc or href.startswith(("#", "/")):
                    continue
                # The ADR index shows a naming template, not a real document.
                if href == "NNNN-title.md":
                    continue
                target = document.parent / unquote(parsed.path)
                if not target.exists():
                    broken.append(f"{document.relative_to(ROOT)}:{line_number}: {href}")
    if broken:
        print("Broken local Markdown links:\n" + "\n".join(broken))
        return 1
    print("Local Markdown links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
