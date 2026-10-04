const CALLBACK_BODY_MAX_BYTES = 16 * 1024;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const COMMIT_PATTERN = /^[0-9a-f]{40}$/i;
const COUNT_FIELDS = [
  'candidate_count',
  'sources_scanned',
  'events_found',
  'events_needing_review',
  'events_added',
  'events_updated',
  'events_cancelled',
];
const PAYLOAD_FIELDS = new Set([
  'run_id',
  'status',
  'instruction_revision',
  ...COUNT_FIELDS,
  'source_failures',
  'error_summary',
]);

/** @typedef {{ run_id: string, status: 'running'|'succeeded'|'failed', instruction_revision: string, candidate_count: number, sources_scanned: number, events_found: number, events_needing_review: number, events_added: number, events_updated: number, events_cancelled: number, source_failures: [], error_summary: string|null }} FixtureCallbackPayload */
/** @typedef {(request: Request, payload: FixtureCallbackPayload) => Response | Promise<Response>} FixtureCallbackHandler */

function jsonResponse(status, message) {
  return Response.json({ error: message }, { status });
}

export function constantTimeSecretEquals(provided, expected) {
  if (typeof provided !== 'string' || typeof expected !== 'string' || expected.length === 0) return false;
  const encoder = new TextEncoder();
  const left = encoder.encode(provided);
  const right = encoder.encode(expected);
  let difference = left.length ^ right.length;
  const length = Math.max(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    difference |= (left[index] ?? 0) ^ (right[index] ?? 0);
  }
  return difference === 0;
}

export function validateFixtureCallback(value) {
  if (!value || Array.isArray(value) || typeof value !== 'object') return false;
  if (Object.keys(value).length !== PAYLOAD_FIELDS.size ||
      Object.keys(value).some((field) => !PAYLOAD_FIELDS.has(field))) return false;
  if (!UUID_PATTERN.test(value.run_id || '') || !COMMIT_PATTERN.test(value.instruction_revision || '')) return false;
  if (!['running', 'succeeded', 'failed'].includes(value.status)) return false;
  for (const field of COUNT_FIELDS) {
    if (!Number.isSafeInteger(value[field]) || value[field] < 0 || value[field] > 50000) return false;
  }
  if (value.sources_scanned !== 0 || value.events_added !== 0 ||
      value.events_updated !== 0 || value.events_cancelled !== 0) return false;
  if (!Array.isArray(value.source_failures) || value.source_failures.length !== 0) return false;
  if (value.error_summary !== null && value.error_summary !== 'Fixture validation failed.') return false;
  if (value.status === 'running' &&
      (value.candidate_count !== 0 || value.events_found !== 0 ||
       value.events_needing_review !== 0 || value.source_failures.length > 0 || value.error_summary !== null)) return false;
  if (value.status === 'succeeded' && value.error_summary !== null) return false;
  if (value.status === 'failed' &&
      (value.candidate_count !== 0 || value.events_found !== 0 ||
       value.events_needing_review !== 0 || value.error_summary !== 'Fixture validation failed.')) return false;
  return true;
}

/**
 * @param {FixtureCallbackHandler} handler
 * @param {() => string | undefined} getSecret
 */
export function withGenovaAgentCallbackProtection(handler, getSecret) {
  return async (request) => {
    if (request.method !== 'POST') return jsonResponse(405, 'Use POST to report a fixture run.');
    const expected = getSecret();
    if (typeof expected !== 'string' || expected.length < 24) {
      return jsonResponse(503, 'The callback credential is not configured.');
    }
    const provided = request.headers.get('x-genova-agent-callback-secret') || '';
    if (!constantTimeSecretEquals(provided, expected)) {
      return jsonResponse(401, 'The callback credential is invalid.');
    }

    const declaredLength = Number(request.headers.get('content-length') || 0);
    if (declaredLength > CALLBACK_BODY_MAX_BYTES) return jsonResponse(413, 'The callback body is too large.');
    const reader = request.body?.getReader();
    if (!reader) return jsonResponse(400, 'The callback body must be valid JSON.');
    const chunks = [];
    let totalBytes = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        totalBytes += value.byteLength;
        if (totalBytes > CALLBACK_BODY_MAX_BYTES) {
          await reader.cancel();
          return jsonResponse(413, 'The callback body is too large.');
        }
        chunks.push(value);
      }
    } catch {
      return jsonResponse(400, 'The callback body must be valid JSON.');
    } finally {
      reader.releaseLock();
    }

    let payload;
    try {
      const bytes = new Uint8Array(totalBytes);
      let offset = 0;
      for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.byteLength;
      }
      payload = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    } catch {
      return jsonResponse(400, 'The callback body must be valid JSON.');
    }
    if (!validateFixtureCallback(payload)) {
      return jsonResponse(400, 'The callback does not match the fixture-only result format.');
    }
    return handler(request, payload);
  };
}
