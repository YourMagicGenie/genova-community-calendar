import { withSupabase } from "npm:@supabase/server@1";
import { withGenovaAgentRunProtection } from "./protection.mjs";

const GITHUB_REPOSITORY = "YourMagicGenie/genova-community-calendar";
const GITHUB_API = "https://api.github.com";
const SHA_PATTERN = /^[0-9a-f]{40}$/i;
const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "authorization, x-client-info, apikey, content-type",
  "access-control-allow-methods": "POST, OPTIONS",
};

function jsonResponse(status: number, value: Record<string, unknown>) {
  return Response.json(value, { status, headers: CORS_HEADERS });
}

function githubHeaders(token: string) {
  return {
    authorization: "Bearer " + token,
    accept: "application/vnd.github+json",
    "x-github-api-version": "2022-11-28",
    "content-type": "application/json",
  };
}

const runHandler = withGenovaAgentRunProtection(async (_request, { userId, context }) => {
  const token = Deno.env.get("GENOVA_AGENT_GITHUB_TOKEN")!;
  const supabaseAdmin = context.supabaseAdmin;

  let latestCommit: Response;
  try {
    latestCommit = await fetch(
      GITHUB_API + "/repos/" + GITHUB_REPOSITORY + "/commits/main",
      { headers: githubHeaders(token) },
    );
  } catch {
    return jsonResponse(502, { error: "GitHub could not be reached. No run was queued." });
  }
  if (!latestCommit.ok) {
    return jsonResponse(502, { error: "GitHub could not verify the current agent instructions. No run was queued." });
  }
  const latestCommitData = await latestCommit.json().catch(() => null);
  const instructionRevision = latestCommitData?.sha;
  if (typeof instructionRevision !== "string" || !SHA_PATTERN.test(instructionRevision)) {
    return jsonResponse(502, { error: "GitHub returned an invalid instruction revision. No run was queued." });
  }

  const { data: run, error: insertError } = await supabaseAdmin
    .from("agent_runs")
    .insert({
      run_mode: "fixture",
      status: "queued",
      requested_by: userId,
      instruction_revision: instructionRevision,
    })
    .select("id")
    .single();
  if (insertError) {
    if (insertError.code === "23505") {
      return jsonResponse(409, { error: "A Genova agent run is already queued or running." });
    }
    return jsonResponse(503, { error: "The run could not be recorded. No workflow was started." });
  }

  let dispatch: Response;
  try {
    dispatch = await fetch(
      GITHUB_API + "/repos/" + GITHUB_REPOSITORY + "/actions/workflows/genova-agent-fixture.yml/dispatches",
      {
        method: "POST",
        headers: githubHeaders(token),
        body: JSON.stringify({
          ref: "main",
          inputs: { run_id: run.id, mode: "fixture" },
        }),
      },
    );
  } catch {
    await supabaseAdmin.from("agent_runs").update({
      status: "failed",
      finished_at: new Date().toISOString(),
      error_summary: "GitHub could not queue the fixture workflow.",
    }).eq("id", run.id);
    return jsonResponse(502, { error: "GitHub could not queue the fixture workflow. Check the run history." });
  }

  if (!dispatch.ok) {
    await supabaseAdmin.from("agent_runs").update({
      status: "failed",
      finished_at: new Date().toISOString(),
      error_summary: "GitHub could not queue the fixture workflow (HTTP " + dispatch.status + ").",
    }).eq("id", run.id);
    return jsonResponse(502, { error: "GitHub could not queue the fixture workflow. Check the run history." });
  }

  return jsonResponse(202, { run_id: run.id, mode: "fixture", status: "queued" });
}, {
  isAdmin: async (userId, context) => {
    const { data, error } = await context.supabaseAdmin
      .from("admin_users")
      .select("user_id")
      .eq("user_id", userId)
      .maybeSingle();
    if (error) throw error;
    return data?.user_id === userId;
  },
  isConfigured: () => {
    const token = Deno.env.get("GENOVA_AGENT_GITHUB_TOKEN");
    const callbackSecret = Deno.env.get("GENOVA_AGENT_CALLBACK_SECRET");
    return typeof token === "string" && token.length >= 20 &&
      typeof callbackSecret === "string" && callbackSecret.length >= 24;
  },
});

Deno.serve(withSupabase({ auth: "user" }, (request, context) => runHandler(request, context)));
