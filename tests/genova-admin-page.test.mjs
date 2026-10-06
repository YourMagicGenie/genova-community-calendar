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

test('admin page offers sign-in only, labels the owner account, and contains no public calendar or signup path', async () => {
  const html = await readAdminPage('../xmlui/admin.html');
  const script = await readAdminPage('../xmlui/admin.js');

  assert.match(html, /YMGAdmin/);
  assert.match(html, /type="password"/);
  assert.doesNotMatch(html, /genova-sample-preview|sign.?up|create account/i);
  assert.doesNotMatch(script, /signUp\s*\(|SUPABASE_SERVICE_ROLE_KEY|sb_secret_/i);
  assert.match(script, /admin_users/);
  assert.match(script, /genova-agent-run/);
  assert.match(script, /isAdmin/);
  assert.match(html, /Event review/);
  assert.match(script, /genova_event_facts/);
  assert.match(script, /review_status/);
  assert.match(script, /published/);
  assert.doesNotMatch(script, /\.insert\([^)]*genova_event_facts|service_role|SUPABASE_SERVICE_ROLE_KEY/i);
});
