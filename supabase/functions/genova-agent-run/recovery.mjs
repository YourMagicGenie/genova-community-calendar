const STALE_RUN_TIMEOUT_MS = 15 * 60 * 1000;

/** @typedef {{ from: (table: string) => any }} AdminSupabaseClient */

/**
 * Free the single-run slot when an earlier workflow never reports completion.
 * @param {AdminSupabaseClient} supabaseAdmin
 * @param {Date} [now]
 */
export async function recoverStaleGenovaAgentRuns(supabaseAdmin, now = new Date()) {
  const finishedAt = now.toISOString();
  const staleBefore = new Date(now.getTime() - STALE_RUN_TIMEOUT_MS).toISOString();
  return await supabaseAdmin
    .from('agent_runs')
    .update({
      status: 'failed',
      finished_at: finishedAt,
      error_summary: 'No completion callback arrived within 15 minutes.',
    })
    .in('status', ['queued', 'running'])
    .lt('queued_at', staleBefore);
}
