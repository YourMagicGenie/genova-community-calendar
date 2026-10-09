import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const live = require("../xmlui/genova-live.js");

test("live route accepts only the field-limited public event shape", () => {
  const event = {
    id: 1,
    title: "Validated event",
    start_time: "2026-10-07T19:00:00+02:00",
    end_time: null,
    is_all_day: false,
    location: "Giardini Luzzati",
    publisher: "Giardini Luzzati / Spazio Comune",
    url: "https://www.spazio-comune.org/prodotto/example/",
    category: null,
  };
  assert.deepEqual(live.validateEvents([event]), [event]);
  assert.throws(() => live.validateEvents([{ ...event, is_all_day: "false" }]), /date precision/);
  assert.match(live.formatTime("2026-10-25T00:00:00+02:00", true), /25 Oct 2026/);
  assert.doesNotMatch(live.formatTime("2026-10-25T00:00:00+02:00", true), /00:00/);
  assert.throws(() => live.validateEvents([{ ...event, description: "not public" }]), /outside the public contract/);
  assert.throws(() => live.validateEvents([{ ...event, start_time: null }]), /valid start time/);
});

test("live page stays separate from fictional sample and never embeds privileged keys", async () => {
  const html = await readFile(new URL("../xmlui/genova-live.html", import.meta.url), "utf8");
  const script = await readFile(new URL("../xmlui/genova-live.js", import.meta.url), "utf8");
  assert.match(html, /Pilot page/);
  assert.match(html, /fictional sample/i);
  assert.match(script, /list_public_genova_events/);
  assert.doesNotMatch(script, /service_role|SUPABASE_SERVICE_ROLE_KEY|description|image_url|transcript/);
});
