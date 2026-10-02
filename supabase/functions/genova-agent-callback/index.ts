import { withSupabase } from "npm:@supabase/server@1";
import { withGenovaAgentCallbackProtection } from "./protection.mjs";

function jsonResponse(status: number, value: Record<string, unknown>) {
  return Response.json(value, { status });
}

Deno.serve(withSupabase({ auth: "none" }, (request, context) => {
  const callbackHandler = withGenovaAgentCallbackProtection(async (_request, payload) => {
    const supabaseAdmin = context.supabaseAdmin;
    let query = supabaseAdmin.from("agent_runs").update({
      instruction_revision: payload.instruction_revision,
      ...(payload.status === "running"
        ? { status: "running", started_at: new Date().toISOString() }
        : {
          status: payload.status,
          finished_at: new Date().toISOString(),
          candidate_count: payload.candidate_count,
          sources_scanned: payload.sources_scanned,
          events_found: payload.events_found,
          events_needing_review: payload.events_needing_review,
          events_added: payload.events_added,
          events_updated: payload.events_updated,
          events_cancelled: payload.events_cancelled,
          source_failures: payload.source_failures,
          error_summary: payload.error_summary,
        }),
    }).eq("id", payload.run_id).eq("run_mode", "fixture");

    if (payload.status === "running") {
      query = query.eq("status", "queued");
    } else if (payload.status === "failed") {
      query = query.in("status", ["queued", "running"]);
    } else {
      query = query.eq("status", "running");
    }

    const { data, error } = await query.select("id").maybeSingle();
    if (error) return jsonResponse(503, { error: "The run result could not be recorded." });
    if (!data) return jsonResponse(409, { error: "The run is missing, finished, or in an invalid state." });
    return jsonResponse(200, { run_id: data.id, status: payload.status });
  }, () => Deno.env.get("GENOVA_AGENT_CALLBACK_SECRET"));

  return callbackHandler(request);
}));
