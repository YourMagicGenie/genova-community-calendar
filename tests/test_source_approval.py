"""Regression tests for the source approval boundary."""

import json
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import download_feeds
import process_pending_feeds
import run_scrapers_from_db


class SourceApprovalTests(unittest.TestCase):
    def test_new_scraper_and_ics_sources_both_enter_pending(self):
        feeds = [
            {"name": "Candidate scraper", "url": "cities/genova/candidate.ics",
             "feed_type": "scraper", "scraper_cmd": "python scrapers/candidate.py"},
            {"name": "Candidate feed", "url": "https://example.org/events.ics",
             "feed_type": "ics_url", "scraper_cmd": None},
        ]
        captured = []

        class Response:
            status = 201
            def __enter__(self): return self
            def __exit__(self, *args): return False

        def fake_urlopen(request):
            captured.append((request.full_url.rsplit("/", 1)[-1], json.loads(request.data.decode())))
            return Response()

        with patch.object(process_pending_feeds.urllib.request, "urlopen", fake_urlopen):
            result = process_pending_feeds.insert_feeds("genova", feeds, "https://db.invalid", "key")

        self.assertEqual(result, (2, 0, 0))
        feed_rows = [row for table, row in captured if table == "feeds"]
        review_rows = [row for table, row in captured if table == "feed_source_reviews"]
        self.assertEqual([row["status"] for row in feed_rows], ["pending", "pending"])
        self.assertEqual([row["discovery_method"] for row in feed_rows], ["scraper", "ics"])
        self.assertIsNone(feed_rows[0]["publisher_url"])
        self.assertEqual(feed_rows[1]["publisher_url"], feeds[1]["url"])
        self.assertEqual([row["genova_fit"] for row in review_rows], ["unknown", "unknown"])
        self.assertEqual(review_rows[0]["source_provenance"], "submitted through pending_feeds.txt")
        self.assertIsNone(review_rows[0]["access_notes"])

    def test_review_metadata_failure_is_reported_and_prevents_inbox_reset(self):
        feed = [{"name": "Candidate feed", "url": "https://example.org/events.ics",
                 "feed_type": "ics_url", "scraper_cmd": None}]

        class Response:
            status = 201
            def __enter__(self): return self
            def __exit__(self, *args): return False

        def fake_urlopen(request):
            if request.full_url.endswith("/feed_source_reviews"):
                raise process_pending_feeds.urllib.error.HTTPError(
                    request.full_url, 500, "metadata unavailable", {}, io.BytesIO(b"unavailable")
                )
            return Response()

        with patch.object(process_pending_feeds.urllib.request, "urlopen", fake_urlopen):
            result = process_pending_feeds.insert_feeds("genova", feed, "https://db.invalid", "key")

        self.assertEqual(result, (1, 0, 1))

    def test_ics_downloader_refuses_unfiltered_text_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            city_dir = Path(tmp) / "cities" / "genova"
            city_dir.mkdir(parents=True)
            (city_dir / "feeds.txt").write_text("# Candidate\nhttps://example.org/events.ics\n")
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                with patch.dict(os.environ, {}, clear=True), \
                     patch.object(download_feeds, "fetch_feeds_from_db", return_value=None), \
                     patch.object(download_feeds.subprocess, "run") as run:
                    with self.assertRaisesRegex(RuntimeError, "active source records"):
                        download_feeds.download_feeds("genova")
                    run.assert_not_called()
            finally:
                os.chdir(previous)

    def test_scraper_runner_does_not_fall_back_to_text_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            city_dir = Path(tmp) / "cities" / "genova"
            city_dir.mkdir(parents=True)
            (city_dir / "feeds.txt").write_text(
                "# Candidate scraper\n"
                "# cmd: python scrapers/should_not_run.py\n"
                "cities/genova/should_not_run.ics\n"
            )
            with patch.object(run_scrapers_from_db, "ROOT", Path(tmp)), \
                 patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_KEY": ""}, clear=False):
                rows, info = run_scrapers_from_db.load_scraper_rows("genova")

            self.assertEqual(rows, [])
            self.assertEqual(info["mode"], "unavailable")
            self.assertFalse(info["fallback_used"])
            self.assertTrue(info["source_state_unavailable"])

    def test_scraper_dry_run_without_database_does_not_execute_candidate(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(run_scrapers_from_db, "load_dotenv", return_value=[]), \
             patch.object(run_scrapers_from_db, "run_rows") as run_rows, \
             patch.object(sys, "argv", ["run_scrapers_from_db.py", "--city", "genova"]):
            result = run_scrapers_from_db.main()

        self.assertEqual(result, 1)
        run_rows.assert_not_called()

    def test_ics_query_requests_only_active_rows(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b"[]"

        with patch.dict(os.environ, {"SUPABASE_URL": "https://db.invalid", "SUPABASE_SERVICE_KEY": "key"}), \
             patch.object(download_feeds.urllib.request, "urlopen", return_value=Response()) as urlopen:
            rows = download_feeds.fetch_feeds_from_db("genova")

        self.assertEqual(rows, [])
        self.assertIn("status=eq.active", urlopen.call_args.args[0].full_url)
        self.assertNotIn("pending", urlopen.call_args.args[0].full_url)

    def test_scraper_query_requests_only_active_rows(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b"[]"

        with patch.dict(os.environ, {"SUPABASE_URL": "https://db.invalid", "SUPABASE_SERVICE_KEY": "key"}), \
             patch.object(run_scrapers_from_db.urllib.request, "urlopen", return_value=Response()) as urlopen:
            rows, error = run_scrapers_from_db.query_db_scraper_rows("genova")

        self.assertEqual(rows, [])
        self.assertIsNone(error)
        self.assertIn("status=eq.active", urlopen.call_args.args[0].full_url)
        self.assertNotIn("pending", urlopen.call_args.args[0].full_url)


if __name__ == "__main__":
    unittest.main()
