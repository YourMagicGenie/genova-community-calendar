import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

async function readAdminPage(path) {
  try {
    return await readFile(new URL(path, import.meta.url), 'utf8');
  } catch {
    assert.fail('the Genova admin page asset ' + path + ' exists');
  }
}

test('admin page links to the calendar, labels the owner account, and exposes no signup path', async () => {
  const html = await readAdminPage('../xmlui/admin.html');
  const script = await readAdminPage('../xmlui/admin.js');

  assert.match(html, /YMGAdmin/);
  assert.match(html, /type="password"/);
  assert.match(html, /genova-sample-preview\.html/);
  assert.doesNotMatch(html, /sign.?up|create account/i);
  assert.doesNotMatch(script, /signUp\s*\(|SUPABASE_SERVICE_ROLE_KEY|sb_secret_/i);
  assert.match(script, /admin_users/);
  assert.match(script, /genova-agent-run/);
  assert.match(script, /isAdmin/);
  assert.match(html, /Collected event review/);
  assert.match(script, /genova_event_facts/);
  assert.match(script, /review_status/);
  assert.match(script, /published/);
  assert.match(script, /clear_genova_demo_events/);
  assert.match(script, /replace_genova_demo_events/);
  assert.match(script, /genova_event_fact_audit/);
  assert.match(script, /Approve for publishing/);
  assert.match(script, /To approve or publish, add:/);
  assert.match(script, /normalized_url = normalizedEventUrl/);
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /Remove demo events/);
  assert.match(html, /Restore demo events/);
  assert.doesNotMatch(script, /service_role|SUPABASE_SERVICE_ROLE_KEY/i);
});


test("source review queue excludes superseded audit placeholders", async () => {
  const source = await readFile(new URL("../xmlui/admin.js", import.meta.url), "utf8");
  assert.match(source, /\.is\("superseded_by", null\)/);
});
