/** @typedef {{ from: (table: string) => any }} AdminSupabaseClient */
/** @typedef {{
 * run_id: string,
 * status: 'running'|'succeeded'|'failed',
 * instruction_revision: string,
 * candidate_count: number,
 * sources_scanned: number,
 * events_found: number,
 * events_needing_review: number,
 * events_added: number,
 * events_updated: number,
 * events_cancelled: number,
 * source_failures: [],
 * error_summary: string|null
 * }} FixtureCallbackPayload */

/**
 * Record a fixture callback with guarded state transitions and idempotent retries.
 * @param {AdminSupabaseClient} supabaseAdmin
 * @param {FixtureCallbackPayload} payload
 * @param {Date} [now]
 */
export async function recordGenovaAgentCallback(supabaseAdmin, payload, now = new Date()) {
  const values = {
    instruction_revision: payload.instruction_revision,
    ...(payload.status === 'running'
      ? { status: 'running', started_at: now.toISOString() }
      : {
        status: payload.status,
        finished_at: now.toISOString(),
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
  };

  let query = supabaseAdmin.from('agent_runs').update(values)
    .eq('id', payload.run_id)
    .eq('run_mode', 'fixture');
  if (payload.status === 'running') {
    query = query.eq('status', 'queued');
  } else if (payload.status === 'failed') {
    query = query.in('status', ['queued', 'running']);
  } else {
    query = query.eq('status', 'running');
  }

  const { data, error } = await query.select('id').maybeSingle();
  if (error) return { status: 503, body: { error: 'The run result could not be recorded.' } };
  if (data) return { status: 200, body: { run_id: data.id, status: payload.status } };

  const { data: current, error: lookupError } = await supabaseAdmin
    .from('agent_runs')
    .select('status')
    .eq('id', payload.run_id)
    .eq('run_mode', 'fixture')
    .maybeSingle();
  if (lookupError) return { status: 503, body: { error: 'The run result could not be verified.' } };
  if (current?.status === payload.status) {
    return { status: 200, body: { run_id: payload.run_id, status: payload.status, duplicate: true } };
  }
  return { status: 409, body: { error: 'The run is missing, finished, or in an invalid state.' } };
}
