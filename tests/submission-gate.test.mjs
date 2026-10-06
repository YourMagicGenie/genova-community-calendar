import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

test('unapplied submission schema cannot expose a working public form', async () => {
  const config = JSON.parse(await readFile(new URL('../xmlui/config.json', import.meta.url)));
  const form = await readFile(new URL('../xmlui/submit-event.js', import.meta.url), 'utf8');
  const preview = await readFile(new URL('../xmlui/genova-sample-preview.html', import.meta.url), 'utf8');
  assert.equal(config.appGlobals.communitySubmissionsEnabled, false);
  assert.match(form, /communitySubmissionsEnabled !== true/);
  assert.doesNotMatch(preview, /href="submit-event.html"/);
});
