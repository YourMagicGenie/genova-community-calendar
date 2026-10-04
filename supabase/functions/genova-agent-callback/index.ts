import { withSupabase } from "npm:@supabase/server@1";
import { withGenovaAgentCallbackProtection } from "./protection.mjs";
import { recordGenovaAgentCallback } from "./update.mjs";

function jsonResponse(status: number, value: Record<string, unknown>) {
  return Response.json(value, { status });
}

Deno.serve(withSupabase({ auth: "none" }, (request, context) => {
  const callbackHandler = withGenovaAgentCallbackProtection(async (_request, payload) => {
    const result = await recordGenovaAgentCallback(context.supabaseAdmin, payload);
    return jsonResponse(result.status, result.body);
  }, () => Deno.env.get("GENOVA_AGENT_CALLBACK_SECRET"));

  return callbackHandler(request);
}));
