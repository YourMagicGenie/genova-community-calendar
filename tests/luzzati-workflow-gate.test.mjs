import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("manual Luzzati workflow verifies hosted persistence state before source contact", async () => {
  const workflow = await readFile(new URL("../.github/workflows/genova-luzzati-pilot.yml", import.meta.url), "utf8");
  const hostedGate = workflow.indexOf("Require the hosted Issue 51 persistence boundary");
  const collector = workflow.indexOf("Collect one bounded index report");
  assert.ok(hostedGate >= 0 && collector > hostedGate);
  assert.match(workflow, /to_regclass\('public\.genova_event_facts'\)/);
  assert.match(workflow, /to_regclass\('public\.genova_source_scans'\)/);
  assert.match(workflow, /status='active'/);
  assert.match(workflow, /feed_type='web_index'/);
  assert.match(workflow, /luzzati-source\.json/);
  assert.match(workflow, /--source "\$RUNNER_TEMP\/luzzati-source\.json"/);
  assert.doesNotMatch(workflow, /grep -q "20261006124729"/);
});
