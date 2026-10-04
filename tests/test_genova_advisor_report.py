"""Offline checks for the read-only Genova Security Advisor request."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import report_genova_supabase_advisors


class AdvisorReportTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {"PROJECT_REF": "eginljyhnnczeeqxwfia", "SUPABASE_ACCESS_TOKEN": "test-token"},
    )
    def test_gets_and_prints_advisors_without_a_database_write(self):
        body = io.BytesIO(json.dumps({"lints": [{"title": "Review RLS"}]}).encode())
        output = io.StringIO()

        with patch.object(report_genova_supabase_advisors, "urlopen", return_value=body) as fetch:
            with redirect_stdout(output):
                self.assertEqual(report_genova_supabase_advisors.main(), 0)

        request = fetch.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(
            request.full_url,
            "https://api.supabase.com/v1/projects/eginljyhnnczeeqxwfia/advisors/security",
        )
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(json.loads(output.getvalue())["lints"][0]["title"], "Review RLS")

    @patch.dict(
        "os.environ",
        {"PROJECT_REF": "eginljyhnnczeeqxwfia", "SUPABASE_ACCESS_TOKEN": "test-token"},
    )
    def test_permission_error_fails_before_migration(self):
        error = HTTPError(
            "https://api.supabase.com/v1/projects/eginljyhnnczeeqxwfia/advisors/security",
            403,
            "Forbidden",
            {},
            io.BytesIO(b'{"missing_permissions":["advisors_read"]}'),
        )
        output = io.StringIO()
        with patch.object(report_genova_supabase_advisors, "urlopen", side_effect=error):
            with redirect_stderr(output):
                self.assertEqual(report_genova_supabase_advisors.main(), 1)
        self.assertIn("advisors_read", output.getvalue())
        self.assertNotIn("test-token", output.getvalue())


if __name__ == "__main__":
    unittest.main()
