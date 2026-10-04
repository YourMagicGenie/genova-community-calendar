import test from 'node:test';
import assert from 'node:assert/strict';

const runId = '00000000-0000-4000-8000-000000000055';
const revision = '0123456789abcdef0123456789abcdef01234567';

async function loadRunProtection() {
  const module = await import('../supabase/functions/genova-agent-run/protection.mjs').catch(() => null);
  assert.ok(module, 'the Genova run authorization module exists');
  assert.equal(typeof module.withGenovaAgentRunProtection, 'function');
  return module.withGenovaAgentRunProtection;
}

async function loadCallbackProtection() {
  const module = await import('../supabase/functions/genova-agent-callback/protection.mjs').catch(() => null);
  assert.ok(module, 'the Genova callback authorization module exists');
  assert.equal(typeof module.withGenovaAgentCallbackProtection, 'function');
  return module.withGenovaAgentCallbackProtection;
}

function request(body, headers = {}, method = 'POST') {
  return new Request('https://functions.example/genova-agent-run', {
    method,
    headers: { 'content-type': 'application/json', ...headers },
    body: method === 'POST' ? JSON.stringify(body) : undefined,
  });
}

function context(userId = runId) {
  return { userClaims: userId ? { id: userId } : null };
}

test('anonymous requests and signed-in non-admins cannot start runs', async () => {
  const withProtection = await loadRunProtection();
  let starts = 0;
  const handler = withProtection(async () => {
    starts += 1;
    return Response.json({ queued: true }, { status: 202 });
  }, { isAdmin: async (userId) => userId === runId, isConfigured: () => true });

  const anonymous = await handler(request({ mode: 'fixture' }), context(null));
  const nonAdmin = await handler(request({ mode: 'fixture' }), context('00000000-0000-4000-8000-000000000056'));

  assert.equal(anonymous.status, 401);
  assert.equal(nonAdmin.status, 403);
  assert.equal(starts, 0);
});

test('a verified admin may request fixture mode only', async () => {
  const withProtection = await loadRunProtection();
  const modes = [];
  const handler = withProtection(async (_request, { mode }) => {
    modes.push(mode);
    return Response.json({ queued: true }, { status: 202 });
  }, { isAdmin: async () => true, isConfigured: () => true });

  const fixture = await handler(request({ mode: 'fixture' }), context());
  const discover = await handler(request({ mode: 'discover' }), context());
  const collect = await handler(request({ mode: 'collect' }), context());

  assert.equal(fixture.status, 202);
  assert.equal(discover.status, 400);
  assert.equal(collect.status, 400);
  assert.deepEqual(modes, ['fixture']);
});

test('missing remote-run configuration, malformed bodies, and unsupported methods fail closed', async () => {
  const withProtection = await loadRunProtection();
  const handler = withProtection(async () => Response.json({ queued: true }), {
    isAdmin: async () => true,
    isConfigured: () => false,
  });

  const unconfigured = await handler(request({ mode: 'fixture' }), context());
  const wrongMethod = await handler(request({}, {}, 'GET'), context());
  const malformed = await handler(new Request('https://functions.example/run', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: '{not-json',
  }), context());

  assert.equal(unconfigured.status, 503);
  assert.equal(wrongMethod.status, 405);
  assert.equal(malformed.status, 400);
});

test('callback rejects missing or incorrect shared credentials before updating a run', async () => {
  const withProtection = await loadCallbackProtection();
  let updates = 0;
  const handler = withProtection(async () => {
    updates += 1;
    return Response.json({ updated: true });
  }, () => 'callback-secret-0123456789abcdef');

  const payload = { run_id: runId, status: 'running', instruction_revision: revision };
  const missing = await handler(request(payload));
  const wrong = await handler(request(payload, { 'x-genova-agent-callback-secret': 'wrong' }));

  assert.equal(missing.status, 401);
  assert.equal(wrong.status, 401);
  assert.equal(updates, 0);
});

test('callback fails closed when its server-only shared credential is unset', async () => {
  const withProtection = await loadCallbackProtection();
  const handler = withProtection(async () => Response.json({ updated: true }), () => undefined);

  const response = await handler(request({ run_id: runId, status: 'running', instruction_revision: revision }));

  assert.equal(response.status, 503);
});

test('fixture callbacks cannot claim source scans, public event writes, malformed IDs, or unsupported states', async () => {
  const withProtection = await loadCallbackProtection();
  let updates = 0;
  const handler = withProtection(async () => {
    updates += 1;
    return Response.json({ updated: true });
  }, () => 'callback-secret-0123456789abcdef');
  const auth = { 'x-genova-agent-callback-secret': 'callback-secret-0123456789abcdef' };
  const base = {
    run_id: runId,
    status: 'succeeded',
    instruction_revision: revision,
    candidate_count: 1,
    sources_scanned: 0,
    events_found: 2,
    events_needing_review: 1,
    events_added: 0,
    events_updated: 0,
    events_cancelled: 0,
    source_failures: [],
    error_summary: null,
  };

  const scansSource = await handler(request({ ...base, sources_scanned: 1 }, auth));
  const writesPublicEvents = await handler(request({ ...base, events_added: 1 }, auth));
  const badId = await handler(request({ ...base, run_id: '../other-run' }, auth));
  const badState = await handler(request({ ...base, status: 'cancelled' }, auth));
  const badSha = await handler(request({ ...base, instruction_revision: 'latest' }, auth));
  const unsafeSummary = await handler(request({ ...base, error_summary: 'token=secret-value' }, auth));
  const extraField = await handler(request({ ...base, details: 'unexpected body data' }, auth));

  for (const response of [scansSource, writesPublicEvents, badId, badState, badSha, unsafeSummary, extraField]) {
    assert.equal(response.status, 400);
  }
  assert.equal(updates, 0);
});

test('valid fixture callbacks with the shared credential reach the state updater', async () => {
  const withProtection = await loadCallbackProtection();
  let received;
  const handler = withProtection(async (_request, payload) => {
    received = payload;
    return Response.json({ updated: true });
  }, () => 'callback-secret-0123456789abcdef');
  const payload = {
    run_id: runId,
    status: 'running',
    instruction_revision: revision,
    candidate_count: 0,
    sources_scanned: 0,
    events_found: 0,
    events_needing_review: 0,
    events_added: 0,
    events_updated: 0,
    events_cancelled: 0,
    source_failures: [],
    error_summary: null,
  };

  const response = await handler(request(payload, { 'x-genova-agent-callback-secret': 'callback-secret-0123456789abcdef' }));

  assert.equal(response.status, 200);
  assert.deepEqual(received, payload);
});

test('callback payloads and request bodies have a strict size limit', async () => {
  const withProtection = await loadCallbackProtection();
  const handler = withProtection(async () => Response.json({ updated: true }), () => 'callback-secret-0123456789abcdef');
  const response = await handler(new Request('https://functions.example/callback', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'content-length': String(20 * 1024),
      'x-genova-agent-callback-secret': 'callback-secret-0123456789abcdef',
    },
    body: '{}',
  }));
  const actualOversize = await handler(new Request('https://functions.example/callback', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-genova-agent-callback-secret': 'callback-secret-0123456789abcdef',
    },
    body: 'x'.repeat(20 * 1024),
  }));

  assert.equal(response.status, 413);
  assert.equal(actualOversize.status, 413);
});

test('run request bodies have a strict size limit', async () => {
  const withProtection = await loadRunProtection();
  const handler = withProtection(async () => Response.json({ queued: true }), { isAdmin: async () => true, isConfigured: () => true });
  const response = await handler(new Request('https://functions.example/run', {
    method: 'POST',
    headers: { 'content-length': String(8 * 1024), 'content-type': 'application/json' },
    body: '{}',
  }), context());
  const actualOversize = await handler(new Request('https://functions.example/run', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: 'x'.repeat(8 * 1024),
  }), context());

  assert.equal(response.status, 413);
  assert.equal(actualOversize.status, 413);
});

test('stale fixture runs are failed after the recovery grace period', async () => {
  const { recoverStaleGenovaAgentRuns } = await import('../supabase/functions/genova-agent-run/recovery.mjs');
  const calls = {};
  const query = {
    update(value) { calls.patch = value; return this; },
    in(column, values) { calls.in = [column, values]; return this; },
    lt(column, value) { calls.lt = [column, value]; return this; },
    then(resolve, reject) { return Promise.resolve({ error: null }).then(resolve, reject); },
  };
  const client = { from(table) { calls.table = table; return query; } };

  await recoverStaleGenovaAgentRuns(client, new Date('2026-10-02T12:00:00.000Z'));

  assert.equal(calls.table, 'agent_runs');
  assert.deepEqual(calls.in, ['status', ['queued', 'running']]);
  assert.deepEqual(calls.lt, ['queued_at', '2026-10-02T11:45:00.000Z']);
  assert.equal(calls.patch.status, 'failed');
  assert.equal(calls.patch.finished_at, '2026-10-02T12:00:00.000Z');
});

test('callback completion retries are idempotent and cannot reopen or downgrade runs', async () => {
  const { recordGenovaAgentCallback } = await import('../supabase/functions/genova-agent-callback/update.mjs');
  const run = { id: runId, run_mode: 'fixture', status: 'running' };

  function clientFor(currentRun) {
    return {
      from(table) {
        assert.equal(table, 'agent_runs');
        return {
          update(patch) {
            const filters = [];
            const builder = {
              eq(column, value) { filters.push([column, value]); return this; },
              in(column, values) { filters.push([column, values]); return this; },
              select() { return this; },
              async maybeSingle() {
                const matches = filters.every(([column, value]) => {
                  if (column === 'status' && Array.isArray(value)) return value.includes(currentRun.status);
                  return currentRun[column] === value;
                });
                if (!matches) return { data: null, error: null };
                Object.assign(currentRun, patch);
                return { data: { id: currentRun.id }, error: null };
              },
            };
            return builder;
          },
          select() {
            const filters = [];
            return {
              eq(column, value) { filters.push([column, value]); return this; },
              async maybeSingle() {
                const matches = filters.every(([column, value]) => currentRun[column] === value);
                return { data: matches ? { status: currentRun.status } : null, error: null };
              },
            };
          },
        };
      },
    };
  }

  const payload = {
    run_id: runId,
    status: 'succeeded',
    instruction_revision: revision,
    candidate_count: 1,
    sources_scanned: 0,
    events_found: 2,
    events_needing_review: 1,
    events_added: 0,
    events_updated: 0,
    events_cancelled: 0,
    source_failures: [],
    error_summary: null,
  };
  const first = await recordGenovaAgentCallback(clientFor(run), payload, new Date('2026-10-02T12:00:00.000Z'));
  const duplicate = await recordGenovaAgentCallback(clientFor(run), payload, new Date('2026-10-02T12:01:00.000Z'));
  const lateFailure = await recordGenovaAgentCallback(clientFor(run), { ...payload, status: 'failed', error_summary: 'Fixture validation failed.', candidate_count: 0, events_found: 0, events_needing_review: 0 }, new Date('2026-10-02T12:02:00.000Z'));

  assert.equal(first.status, 200);
  assert.equal(duplicate.status, 200);
  assert.equal(duplicate.body.duplicate, true);
  assert.equal(lateFailure.status, 409);
  assert.equal(run.status, 'succeeded');
});
