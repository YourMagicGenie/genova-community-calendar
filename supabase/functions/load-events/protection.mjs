const ALLOWED_CITIES = new Set(['genova']);
const MAX_BODY_BYTES = 10 * 1024 * 1024;
const MAX_EVENTS = 10000;
const MIN_TOKEN_LENGTH = 32;

export function canDeleteStaleEvents(upsertErrors) {
  return upsertErrors === 0;
}

export const loadEventsCorsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-load-events-token',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

function jsonResponse(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...loadEventsCorsHeaders, 'Content-Type': 'application/json' },
  });
}

async function readBodyWithLimit(request) {
  const declaredLength = Number(request.headers.get('content-length'));
  if (Number.isFinite(declaredLength) && declaredLength > MAX_BODY_BYTES) return null;
  if (!request.body) return '';

  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BODY_BYTES) {
        await reader.cancel();
        return null;
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(bytes);
}

function validateEvent(event, index) {
  const fail = (reason) => ({ error: `events[${index}] ${reason}` });
  if (!event || typeof event !== 'object' || Array.isArray(event)) return fail('must be an object');
  if (typeof event.source_uid !== 'string' || !event.source_uid.trim() || event.source_uid.length > 512) {
    return fail('must have a non-empty source_uid of at most 512 characters');
  }
  if (typeof event.title !== 'string' || !event.title.trim() || event.title.length > 1000) {
    return fail('must have a non-empty title of at most 1000 characters');
  }
  if (typeof event.start_time !== 'string'
      || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})$/.test(event.start_time)
      || !Number.isFinite(Date.parse(event.start_time))) {
    return fail('must have an ISO 8601 start_time with an explicit timezone');
  }
  if (event.city !== undefined && event.city !== 'genova') return fail('city must be genova');
  return { value: { ...event, city: 'genova' } };
}

export function validateLoadEventsBody(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return { error: 'Request body must be a JSON object.' };
  }

  const hasCity = Object.hasOwn(body, 'city');
  const hasEvents = Object.hasOwn(body, 'events');
  if (hasCity || hasEvents) {
    if (!hasCity || !hasEvents || !Array.isArray(body.events)) {
      return { error: 'Direct mode requires both city and events array.' };
    }
    if (!ALLOWED_CITIES.has(body.city)) return { error: 'Only the Genova city scope is allowed.' };
    if (body.events.length > MAX_EVENTS) return { error: `At most ${MAX_EVENTS} events may be submitted at once.` };

    const events = [];
    for (const [index, event] of body.events.entries()) {
      const result = validateEvent(event, index);
      if (result.error) return result;
      events.push(result.value);
    }
    return { value: { mode: 'direct', city: 'genova', events } };
  }

  if (Object.hasOwn(body, 'cities') && !Array.isArray(body.cities)) {
    return { error: 'Legacy mode cities must be an array.' };
  }
  const cities = body.cities ?? ['genova'];
  if (cities.length > 1 || cities.some((city) => !ALLOWED_CITIES.has(city))) {
    return { error: 'Legacy mode may request Genova only.' };
  }
  return { value: { mode: 'legacy', cities: ['genova'] } };
}

async function tokenMatches(actual, expected) {
  if (typeof actual !== 'string' || typeof expected !== 'string') return false;
  const encoder = new TextEncoder();
  const [actualDigest, expectedDigest] = await Promise.all([
    crypto.subtle.digest('SHA-256', encoder.encode(actual)),
    crypto.subtle.digest('SHA-256', encoder.encode(expected)),
  ]);
  const left = new Uint8Array(actualDigest);
  const right = new Uint8Array(expectedDigest);
  let difference = 0;
  for (let i = 0; i < left.length; i += 1) difference |= left[i] ^ right[i];
  return difference === 0;
}

export function withLoadEventsProtection(handler, getToken) {
  return async (request) => {
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: loadEventsCorsHeaders });
    if (request.method !== 'POST') return jsonResponse({ success: false, error: 'Method not allowed.' }, 405);

    const expectedToken = await getToken();
    if (typeof expectedToken !== 'string' || expectedToken.length < MIN_TOKEN_LENGTH) {
      return jsonResponse({ success: false, error: 'The server-side writer credential is not configured.' }, 503);
    }
    const providedToken = request.headers.get('x-load-events-token');
    if (!await tokenMatches(providedToken, expectedToken)) {
      return jsonResponse({ success: false, error: 'Unauthorized.' }, 401);
    }

    const bodyText = await readBodyWithLimit(request);
    if (bodyText === null) return jsonResponse({ success: false, error: 'Request body exceeds the 10 MiB limit.' }, 413);
    let body;
    try {
      body = JSON.parse(bodyText);
    } catch (_) {
      return jsonResponse({ success: false, error: 'Request body must be valid JSON.' }, 400);
    }
    const validated = validateLoadEventsBody(body);
    if (validated.error) return jsonResponse({ success: false, error: validated.error }, 400);

    return handler(request, validated.value);
  };
}
