const RUN_BODY_MAX_BYTES = 4096;
const CORS_HEADERS = {
  'access-control-allow-origin': '*',
  'access-control-allow-headers': 'authorization, x-client-info, apikey, content-type',
  'access-control-allow-methods': 'POST, OPTIONS',
};

/** @typedef {{ userClaims?: { id?: string } | null }} RunAuthContext */
/** @typedef {(request: Request, details: { userId: string, mode: 'fixture', context: any }) => Response | Promise<Response>} GenovaRunHandler */
/** @typedef {{ isAdmin: (userId: string, context: any) => boolean | Promise<boolean>, isConfigured: () => boolean }} RunProtectionOptions */

function jsonResponse(status, message) {
  return Response.json({ error: message }, { status, headers: CORS_HEADERS });
}

async function readJson(request, maxBytes) {
  const declaredLength = Number(request.headers.get('content-length') || 0);
  if (declaredLength > maxBytes) return { error: 413 };
  const reader = request.body?.getReader();
  if (!reader) return { error: 400 };
  const chunks = [];
  let totalBytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      totalBytes += value.byteLength;
      if (totalBytes > maxBytes) {
        await reader.cancel();
        return { error: 413 };
      }
      chunks.push(value);
    }
  } catch {
    return { error: 400 };
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(totalBytes);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return { value: JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)) };
  } catch {
    return { error: 400 };
  }
}

/**
 * @param {GenovaRunHandler} handler
 * @param {RunProtectionOptions} options
 */
export function withGenovaAgentRunProtection(handler, { isAdmin, isConfigured }) {
  return async (request, context) => {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }
    if (request.method !== 'POST') return jsonResponse(405, 'Use POST to request a fixture run.');

    const userId = context?.userClaims?.id;
    if (typeof userId !== 'string' || !userId) {
      return jsonResponse(401, 'Sign in with the approved admin account.');
    }

    let admin;
    try {
      admin = await isAdmin(userId, context);
    } catch {
      return jsonResponse(503, 'Admin access could not be checked. Try again later.');
    }
    if (admin !== true) return jsonResponse(403, 'This account is not approved to run the Genova agent.');

    const parsed = await readJson(request, RUN_BODY_MAX_BYTES);
    if (parsed.error === 413) return jsonResponse(413, 'The request is too large.');
    if (parsed.error) return jsonResponse(400, 'The request body must be valid JSON.');
    const body = parsed.value;
    if (!body || Array.isArray(body) || typeof body !== 'object' ||
        body.mode !== 'fixture' || Object.keys(body).some((key) => key !== 'mode')) {
      return jsonResponse(400, 'Only mode=fixture is available in this pilot.');
    }

    let configured;
    try {
      configured = isConfigured() === true;
    } catch {
      configured = false;
    }
    if (!configured) return jsonResponse(503, 'The remote fixture runner is not configured yet.');

    return handler(request, { userId, mode: 'fixture', context });
  };
}
