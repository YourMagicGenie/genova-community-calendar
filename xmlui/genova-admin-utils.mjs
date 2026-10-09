export const GENOVA_CATEGORIES = [
  ["music", "Music"], ["theatre-performance", "Theatre / performance"],
  ["art-exhibitions", "Art / exhibitions"], ["sports", "Sports"],
  ["food-drink", "Food / drink"], ["festivals-markets", "Festivals / markets"],
  ["talks-workshops", "Talks / workshops"], ["family", "Family"],
  ["outdoors-tours", "Outdoors / tours"], ["community-social", "Community / social"],
];
const CATEGORY_KEYS = new Set(GENOVA_CATEGORIES.map(([key]) => key));

export function normalizeCategorySuggestions(value) {
  if (!Array.isArray(value)) return [];
  return value.filter((item) => item && typeof item === "object" &&
    CATEGORY_KEYS.has(item.category) && Number.isFinite(item.confidence) &&
    item.confidence >= 0 && item.confidence <= 1 && typeof item.evidence === "string");
}

export function isGenovaCategory(value) {
  return CATEGORY_KEYS.has(value);
}

const ROME = "Europe/Rome";
const parts = (date, timeZone = ROME) => Object.fromEntries(new Intl.DateTimeFormat("en-GB", {
  timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hourCycle: "h23",
}).formatToParts(date).map((part) => [part.type, part.value]));

export function toRomeInput(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const p = parts(date);
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

export function toRomeDateInput(value) {
  return toRomeInput(value).slice(0, 10);
}

function offsetAt(instant) {
  const name = new Intl.DateTimeFormat("en", { timeZone: ROME, timeZoneName: "longOffset" })
    .formatToParts(new Date(instant)).find((part) => part.type === "timeZoneName")?.value;
  if (name === "GMT" || name === "UTC") return 0;
  const match = /^GMT([+-])(\d{2}):(\d{2})$/.exec(name || "");
  if (!match) return null;
  const minutes = Number(match[2]) * 60 + Number(match[3]);
  return (match[1] === "+" ? 1 : -1) * minutes;
}

export function fromRomeInput(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value || "");
  if (!match) return null;
  const [, ys, ms, ds, hs, mins] = match;
  const [year, month, day, hour, minute] = [ys, ms, ds, hs, mins].map(Number);
  const wall = Date.UTC(year, month - 1, day, hour, minute);
  const check = new Date(wall);
  if (check.getUTCFullYear() !== year || check.getUTCMonth() !== month - 1 ||
      check.getUTCDate() !== day || check.getUTCHours() !== hour || check.getUTCMinutes() !== minute) return null;
  const offsets = new Set([-36, -24, -12, 0, 12, 24, 36].map((delta) => offsetAt(wall + delta * 3600000)));
  const candidates = [...offsets].filter((offset) => offset !== null).map((offset) => wall - offset * 60000)
    .filter((instant) => {
      const p = parts(new Date(instant));
      return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}` === value;
    });
  return candidates.length === 1 ? new Date(candidates[0]).toISOString() : null;
}

export function fromRomeDateInput(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return null;
  return fromRomeInput(`${value}T00:00`);
}

export function validateDemoEvents(events) {
  if (!Array.isArray(events) || events.length > 100) throw new Error("Demo data must be a list of at most 100 examples.");
  const allowed = new Set(GENOVA_CATEGORIES.map(([key]) => key));
  const ids = new Set();
  for (const [index, event] of events.entries()) {
    if (!event || typeof event !== "object" || !/^sample-[a-z0-9-]+$/.test(event.id || "")) throw new Error(`Demo event ${index + 1} has an invalid ID.`);
    if (ids.has(event.id)) throw new Error(`Demo event ${index + 1} has an invalid ID.`);
    ids.add(event.id);
    if (!event.title?.trim() || !event.venue?.trim() || !event.sourceName?.trim()) throw new Error(`Demo event ${index + 1} is missing a required label.`);
    const categories = Array.isArray(event.categories) && event.categories.length ? event.categories : [event.category];
    if (!allowed.has(event.category) || !categories.includes(event.category) || categories.some((category) => !allowed.has(category))) throw new Error(`Demo event ${index + 1} has an invalid category.`);
    if (!Number.isInteger(event.daysFromToday) || event.daysFromToday < 0 || event.daysFromToday > 60) throw new Error(`Demo event ${index + 1} has an invalid date offset.`);
    if (event.startTime !== null && !/^([01]\d|2[0-3]):[0-5]\d$/.test(event.startTime || "")) throw new Error(`Demo event ${index + 1} has an invalid time.`);
    if (!Array.isArray(event.tags) || event.tags.some((tag) => tag !== "date-night")) throw new Error(`Demo event ${index + 1} has an invalid tag.`);
    let url;
    try { url = new URL(event.sourceUrl); } catch { throw new Error(`Demo event ${index + 1} has an invalid sample link.`); }
    if (url.protocol !== "https:" || !["example.org", "www.example.org"].includes(url.hostname)) throw new Error(`Demo event ${index + 1} has an invalid sample link.`);
  }
  return events;
}
