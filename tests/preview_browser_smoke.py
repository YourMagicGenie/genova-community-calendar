#!/usr/bin/env python3
"""Real Chromium smoke test for the isolated, fictional Genova calendar preview."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import re

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "browser-smoke-artifacts"
VIEWPORTS = (
    ("desktop", 1280, 900),
    ("phone", 390, 844),
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


def run_viewport(browser, base_url, name, width, height):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        is_mobile=name == "phone",
        has_touch=name == "phone",
        device_scale_factor=1,
    )
    page = context.new_page()
    console_errors = []
    page_errors = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    # Browsers may probe this conventional path even though the sample page
    # intentionally has no favicon. Keep that implicit request out of the test.
    page.route("**/favicon.ico", lambda route: route.fulfill(status=204))

    try:
        response = page.goto(f"{base_url}/?city=genova&preview=sample", wait_until="networkidle")
        assert response and response.ok, "the Genova preview route should load successfully"
        assert "genova-sample-preview.html" in page.url, f"unexpected preview route: {page.url}"

        status = page.locator("#calendar-status")
        status.wait_for()
        fixture_count = page.evaluate("""async () => {
            const response = await fetch('sample-events.json');
            if (!response.ok) return -1;
            return (await response.json()).length;
        }""")
        assert fixture_count >= 15, f"fictional sample fixture did not load at least 15 events: {fixture_count}"

        status_text = status.inner_text()
        count_match = re.fullmatch(r"\d+ sample events?", status_text)
        if count_match:
            initial_count = int(status_text.split()[0])
        else:
            assert status_text == "No sample events match these filters.", f"unexpected calendar status: {status_text}"
            initial_count = 0

        month_heading = page.locator("#calendar-month")
        month_heading.wait_for()
        current_month = month_heading.inner_text()
        page.locator("#next-month").click()
        next_month = month_heading.inner_text()
        assert next_month and next_month != current_month, "Next should change the displayed month"
        page.locator("#previous-month").click()
        assert month_heading.inner_text() == current_month, "Previous should return to the original month"
        page.locator("#current-month").click()

        # All fifteen-plus crowded-date examples are four days from today.
        # Around a month boundary that date can be in the next month instead.
        more = page.locator("#calendar-grid .calendar-day-more")
        if more.count() == 0:
            page.locator("#next-month").click()
            more = page.locator("#calendar-grid .calendar-day-more")
        assert more.count() > 0, "the dense sample date should show a +N more expander"

        expander = more.first
        summary = expander.locator("summary")
        match = re.fullmatch(r"\+(\d+) more", summary.inner_text())
        assert match, f"unexpected dense-date control: {summary.inner_text()}"
        expected_overflow = int(match.group(1))
        summary.click()
        assert expander.evaluate("(element) => element.open"), "the dense date should expand when selected"
        actual_overflow = expander.locator(".calendar-day-overflow .calendar-event").count()
        assert actual_overflow == expected_overflow, (
            f"expanded date should reveal all {expected_overflow} overflow events; found {actual_overflow}"
        )

        # Test a real checkbox change against the rendered event count.
        music = page.locator('input[name="category-filter"][value="music"]')
        assert music.count() == 1, "the Music category checkbox should be present"
        before_filter = int(status.inner_text().split()[0])
        music.uncheck()
        after_filter_text = status.inner_text()
        after_filter = int(after_filter_text.split()[0]) if after_filter_text[0].isdigit() else 0
        assert after_filter < before_filter, "unchecking Music should remove matching events"
        music.check()
        restored = int(status.inner_text().split()[0])
        assert restored == before_filter, "checking Music again should restore the matching events"

        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        )
        assert overflow, f"{name} viewport has horizontal page overflow"

        # The community form is intentionally gated until the hosted migration
        # and field-limited public route are ready. Its layout and local preview
        # must still work at both desktop and phone sizes.
        form_response = page.goto(f"{base_url}/xmlui/submit-event.html", wait_until="networkidle")
        assert form_response and form_response.ok, "community form should load"
        assert page.locator("#send-button").is_disabled(), "unactivated form must not accept submissions"
        assert page.locator("#setup-error").is_visible(), "unactivated form should explain availability"
        page.locator('input[name="title"]').fill("A local test event")
        page.locator('input[name="start"]').fill("2026-12-15T18:00")
        page.locator('textarea[name="description"]').fill("An original example description.")
        page.locator('input[name="rights_confirmed"]').check()
        page.locator("#preview-button").click()
        assert "A local test event" in page.locator("#preview").inner_text()
        assert page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"), (
            f"{name} submission page has horizontal overflow"
        )

        if console_errors or page_errors:
            raise AssertionError(
                f"browser errors: console={console_errors!r}; page={page_errors!r}"
            )
    except Exception as error:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        screenshot = ARTIFACTS / f"genova-preview-{name}.png"
        try:
            page.screenshot(path=str(screenshot), full_page=True)
        except Exception:
            pass
        (ARTIFACTS / f"genova-preview-{name}-error.txt").write_text(
            f"{type(error).__name__}: {error}\n"
            f"console errors: {console_errors!r}\n"
            f"page errors: {page_errors!r}\n",
            encoding="utf-8",
        )
        raise
    finally:
        context.close()


def main():
    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for name, width, height in VIEWPORTS:
                    run_viewport(browser, base_url, name, width, height)
                    print(f"PASS: Genova sample preview at {name} size {width}x{height}")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
