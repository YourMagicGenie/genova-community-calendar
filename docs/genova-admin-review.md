# Genova calendar admin review

Open the calendar and choose **Admin** in the top navigation. Sign in with an account already approved in the private `admin_users` allowlist. Visitor accounts and signed-out visitors cannot see collected event facts or change demo data.

## Remove or restore the fictional calendar examples

In **Fictional demo events**, review the count and use **Remove demo events**. Confirm the prompt; only the isolated demo set is cleared. Refresh the public sample calendar to confirm it is empty. **Restore demo events** reloads the clearly fictional `example.org` fixtures. The controls do not touch collected source facts, community suggestions, or published events.

## Review collected events

The review list separates current dated occurrences from records that still need date extraction. Expired occurrences are filtered from active review, while their source facts, scan provenance, and correction history remain stored. Unpublished expired occurrences are not published; published events disappear from the public route after their end time (or start time if no end is known). Date-only occurrences stay current through their local calendar date in `Europe/Rome`.

Each card shows the publisher and source link, the candidate's current details, category suggestions with confidence and short evidence summaries, and the last-seen time. Select the best-supported primary category from the suggested options or the full stable taxonomy; category names cannot be free-typed. A low-confidence guess is labeled, and an empty suggestion does not block saving other corrections. Edit the title, Rome-local start/end or all-day date, venue, primary category, date-night tag, or source link and save. Mark an event reviewed only after its title, date or date/time, venue, category, and source link are complete. The page explains which details are missing. Publishing is available only for validated rows with those details; the database also requires an active approved source and a known date. Use **Change history** to see private corrections and review-state changes.

Date/time input is interpreted as `Europe/Rome`. Ambiguous or nonexistent local times during daylight-saving changes must be corrected before saving.

## Release review

Preview: https://yourmagicgenie.github.io/genova-community-calendar/

On a phone, open the preview, select **Admin**, sign in, and check that the demo controls and event cards fit the screen. On a laptop, edit a demo event only through restore/clear, then confirm the preview count; inspect an event card's correction fields and its missing-details explanation. Do not use real events for a UI smoke test.
