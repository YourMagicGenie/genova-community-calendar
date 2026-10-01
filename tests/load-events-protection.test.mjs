import test from 'node:test';
import assert from 'node:assert/strict';
import { canDeleteStaleEvents, withLoadEventsProtection } from '../supabase/functions/load-events/protection.mjs';

const SECRET = 'test-load-events-token-0123456789abcdef';
const validEvent = {
  source_uid: 'genova:event:1',
  title: 'Example event',
  start_time: '2026-10-02T19:00:00+02:00',
};

function createRequest(body, token = SECRET, method = 'POST') {
  return new Request('https://function.example/load-events', {
    method,
    headers: token ? { 'x-load-events-token': token, 'content-type': 'application/json' } : {},
    body: method === 'POST' ? JSON.stringify(body) : undefined,
  });
}

test('missing or wrong server token is rejected before the writer runs', async () => {
  const databaseActions = { upserts: 0, staleDeletions: 0 };
  const handler = withLoadEventsProtection(async () => {
    databaseActions.upserts += 1;
    databaseActions.staleDeletions += 1;
    return new Response('written');
  }, () => SECRET);

  const missing = await handler(createRequest({ city: 'genova', events: [validEvent] }, null));
  const wrong = await handler(createRequest({ city: 'genova', events: [validEvent] }, 'wrong-token'));

  assert.equal(missing.status, 401);
  assert.equal(wrong.status, 401);
  assert.deepEqual(databaseActions, { upserts: 0, staleDeletions: 0 });
});

test('missing server configuration fails closed before the writer runs', async () => {
  const databaseActions = { upserts: 0, staleDeletions: 0 };
  const handler = withLoadEventsProtection(async () => {
    databaseActions.upserts += 1;
    databaseActions.staleDeletions += 1;
    return new Response('written');
  }, () => undefined);

  const response = await handler(createRequest({ city: 'genova', events: [validEvent] }));

  assert.equal(response.status, 503);
  assert.deepEqual(databaseActions, { upserts: 0, staleDeletions: 0 });
});

test('malformed and non-Genova payloads are rejected before the writer runs', async () => {
  const databaseActions = { upserts: 0, staleDeletions: 0 };
  const handler = withLoadEventsProtection(async () => {
    databaseActions.upserts += 1;
    databaseActions.staleDeletions += 1;
    return new Response('written');
  }, () => SECRET);

  const malformed = await handler(createRequest({ city: 'genova', events: [{ title: 'Missing identity and date' }] }));
  const otherCity = await handler(createRequest({ city: 'asheville', events: [validEvent] }));
  const otherLegacyCity = await handler(createRequest({ cities: ['genova', 'toronto'] }));

  assert.equal(malformed.status, 400);
  assert.equal(otherCity.status, 400);
  assert.equal(otherLegacyCity.status, 400);
  assert.deepEqual(databaseActions, { upserts: 0, staleDeletions: 0 });
});

test('authorized Genova fixture reaches the writer with a normalized one-city payload', async () => {
  let written;
  const handler = withLoadEventsProtection(async (_request, payload) => {
    written = payload;
    return new Response('written');
  }, () => SECRET);

  const response = await handler(createRequest({ city: 'genova', events: [validEvent] }));

  assert.equal(response.status, 200);
  assert.deepEqual(written, { mode: 'direct', city: 'genova', events: [{ ...validEvent, city: 'genova' }] });
});

test('authorized legacy mode defaults to Genova and never discovers inherited cities', async () => {
  let written;
  const handler = withLoadEventsProtection(async (_request, payload) => {
    written = payload;
    return new Response('written');
  }, () => SECRET);

  const response = await handler(createRequest({}));

  assert.equal(response.status, 200);
  assert.deepEqual(written, { mode: 'legacy', cities: ['genova'] });
});

test('oversized request bodies and unsupported methods never reach the writer', async () => {
  let writerCalls = 0;
  const handler = withLoadEventsProtection(async () => {
    writerCalls += 1;
    return new Response('written');
  }, () => SECRET);

  const large = new Request('https://function.example/load-events', {
    method: 'POST',
    headers: { 'x-load-events-token': SECRET, 'content-length': String(11 * 1024 * 1024) },
    body: '{}',
  });
  const tooLarge = await handler(large);
  const get = await handler(createRequest(undefined, SECRET, 'GET'));

  assert.equal(tooLarge.status, 413);
  assert.equal(get.status, 405);
  assert.equal(writerCalls, 0);
});

test('stale cleanup is allowed only after every upsert batch succeeds', () => {
  assert.equal(canDeleteStaleEvents(0), true);
  assert.equal(canDeleteStaleEvents(1), false);
  assert.equal(canDeleteStaleEvents(500), false);
});
