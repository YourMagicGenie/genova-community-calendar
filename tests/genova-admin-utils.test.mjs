import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fromRomeInput, toRomeInput, fromRomeDateInput, toRomeDateInput, validateDemoEvents, normalizeCategorySuggestions, isGenovaCategory } from "../xmlui/genova-admin-utils.mjs";

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

test("admin category suggestions accept only stable taxonomy keys and bounded confidence", () => {
  assert.deepEqual(normalizeCategorySuggestions([
    { category: "music", confidence: 0.94, evidence: "structured category metadata" },
    { category: "date-night", confidence: 0.94, evidence: "not a category" },
    { category: "family", confidence: 2, evidence: "invalid confidence" },
  ]), [{ category: "music", confidence: 0.94, evidence: "structured category metadata" }]);
  assert.equal(isGenovaCategory("theatre-performance"), true);
  assert.equal(isGenovaCategory("date-night"), false);
  assert.deepEqual(normalizeCategorySuggestions(null), []);
});

test("admin can restore only the bounded, fictional fixture set", async () => {
  const events = JSON.parse(await readFile(new URL("../xmlui/sample-events.json", import.meta.url), "utf8"));
  assert.equal(validateDemoEvents(events).length, 24);
  assert.throws(() => validateDemoEvents([events[0], { ...events[0] }]), /invalid ID/);
  assert.throws(() => validateDemoEvents([{ ...events[0], sourceUrl: "https://real-events.it/listing" }]), /sample link/);
  assert.throws(() => validateDemoEvents([{ ...events[0], daysFromToday: 61 }]), /date offset/);
});
