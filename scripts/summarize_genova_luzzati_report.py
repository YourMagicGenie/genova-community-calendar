#!/usr/bin/env python3
"""Render the transient facts-only pilot report for a human Actions review."""
import argparse
import json
from pathlib import Path


def cell(value):
    if isinstance(value, list):
        value = ', '.join(str(item) for item in value)
    return str(value if value is not None else '—').replace('|', '\\|').replace('\n', ' ')


def summarize(report):
    rows = [
        '# Luzzati candidate diagnostics', '',
        f"Result: {cell(report.get('status'))}. No publication is performed by this report.", '',
        '| Title / source URL | Coverage / HTTP | Date / year | Local time / normalized start | Location | Category | Unresolved reasons |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for candidate in report.get('diagnostics', {}).get('candidates', []):
        fields = candidate.get('fields') or {}
        rows.append('| ' + ' | '.join(cell(value) for value in [
            f"{candidate.get('title') or 'Title missing'} — {candidate['url']}",
            f"{candidate['coverage']} / {candidate.get('http_status') or '—'}",
            f"{cell(fields.get('date_text', []))} / {cell(fields.get('explicit_years', []))}",
            f"{cell(fields.get('local_times', []))} / {cell(fields.get('normalized_starts', []))}",
            fields.get('locations', []), fields.get('categories', []),
            candidate.get('unresolved_reasons', []),
        ]) + ' |')
    rows.extend(['', 'The JSON artifact includes extraction methods, text scope, precision, and redirect host.',
                 'A visible-page fallback needs review: facts could come from outside the event content.',
                 'No HTML, publisher descriptions, or images are retained.', ''])
    return '\n'.join(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(summarize(json.loads(Path(args.report).read_text())), encoding='utf-8')
