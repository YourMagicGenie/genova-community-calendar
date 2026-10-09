import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fromRomeInput, toRomeInput, fromRomeDateInput, toRomeDateInput, validateDemoEvents } from "../xmlui/genova-admin-utils.mjs";

test("Europe/Rome editor round-trips normal local date and time", () => {
  const iso = fromRomeInput("2026-10-08T19:30");
  assert.equal(toRomeInput(iso), "2026-10-08T19:30");
});

test("Europe/Rome editor rejects nonexistent and repeated daylight-saving times", () => {
  assert.equal(fromRomeInput("2026-03-29T02:30"), null);
  assert.equal(fromRomeInput("2026-10-25T02:30"), null);
  assert.equal(fromRomeInput("2026-02-30T12:00"), null);
});

test("Europe/Rome date-only editor round-trips all-day dates without displaying a made-up time", () => {
  const instant = fromRomeDateInput("2026-10-25");
  assert.equal(instant, "2026-10-24T22:00:00.000Z");
  assert.equal(toRomeDateInput(instant), "2026-10-25");
  assert.equal(fromRomeDateInput("2026-02-30"), null);
});

test("admin can restore only the bounded, fictional fixture set", async () => {
  const events = JSON.parse(await readFile(new URL("../xmlui/sample-events.json", import.meta.url), "utf8"));
  assert.equal(validateDemoEvents(events).length, 24);
  assert.throws(() => validateDemoEvents([events[0], { ...events[0] }]), /invalid ID/);
  assert.throws(() => validateDemoEvents([{ ...events[0], sourceUrl: "https://real-events.it/listing" }]), /sample link/);
  assert.throws(() => validateDemoEvents([{ ...events[0], daysFromToday: 61 }]), /date offset/);
});
