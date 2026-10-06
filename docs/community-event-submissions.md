# Community event submissions — rollout

Issue #68 adds an optional public event-suggestion path. The code is merged in stages while the main calendar still shows fictional fixtures. Both `xmlui/config.json` and the server-owned `community_submission_settings.accepting` switch start disabled. Applying the schema alone cannot accept public proposals.

## Data flow

1. A visitor submits title, Europe/Rome start, original description, optional end/venue/link/name/contact, and a text-rights confirmation. The browser writes only those columns to `event_submissions`. The database defaults to `pending`; public roles have no review-status write or queue-read access.
2. The registered admin signs into `xmlui/admin.html`, edits a proposal, and explicitly approves or rejects it. The review RPC checks the server-side `admin_users` registry. Approval writes one stable `community:<uuid>` record to `events`; withdrawal removes it. Contact email is never copied into the event record.
3. The database's field-limited `list_public_genova_events()` route includes approved community records alongside published source facts. `get_public_community_description(id)` returns only the reviewed description for an approved community event. Issue #51 owns wiring that route into the visible calendar and later category subscriptions. Never expose raw `events` or the pending queue to the browser.

The table limits intake to 50 proposals per rolling day and rejects exact title/start duplicates within that day. This is a small pilot safeguard, not a complete anti-spam solution. The form also has a bot trap. If the queue attracts abuse, add a server-verified challenge or stronger rate limits before increasing the cap.

## Activation checklist

- Complete the public UI and category-feed integration in #51, including correct handling of community event `source_uid`, edits, and withdrawals. The database route already returns approved community records; the current public page still displays fictional fixtures.
- Review and apply migration `20261006130000_community_event_submissions.sql` through the guarded Supabase preview/apply workflow. Verify hosted RLS, column grants, admin authorization, and an anonymous proposal in a controlled test. Do not run a production migration from a PR preview.
- Publish a specific submission privacy notice with the operator's contact, purpose, retention and deletion process for pending/rejected proposals and optional contact email. Set an operational queue-cleanup practice. The placeholder text on the draft form is not a complete notice.
- Review form and admin queue on a phone and laptop. Submit a fictional proposal, check that it is private, approve it, verify the published card and feed, edit it, withdraw it, and verify disappearance. Remove the fictional record afterward.
- In a later activation PR, set `communitySubmissionsEnabled` to `true` in `xmlui/config.json` and add the `submit-event.html` link to the public calendar. After hosted checks and the privacy notice, explicitly set the server-owned `community_submission_settings.accepting` switch to true through a reviewed database change. Verify anonymous submission only then. Do not enable either switch before all earlier checks pass.

Image upload is not in this stage. It needs private storage, limits, image rights confirmation, admin review, an explicit public copy decision, and cleanup of abandoned uploads.
