import test from 'node:test';
import assert from 'node:assert/strict';
import { romeInstants } from '../xmlui/submission-time.mjs';

test('Rome event time converts in winter and summer', () => {
  assert.deepEqual(romeInstants('2026-01-15T18:30'), ['2026-01-15T17:30:00.000Z']);
  assert.deepEqual(romeInstants('2026-07-15T18:30'), ['2026-07-15T16:30:00.000Z']);
});
test('clock-change gaps and repeated times are not silently guessed', () => {
  assert.deepEqual(romeInstants('2026-03-29T02:30'), []);
  assert.equal(romeInstants('2026-10-25T02:30').length, 2);
});
test('invalid calendar dates do not roll forward', () => {
  assert.deepEqual(romeInstants('2026-02-30T12:00'), []);
  assert.deepEqual(romeInstants('bad'), []);
});
