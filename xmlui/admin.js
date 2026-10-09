import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { fromRomeInput, toRomeInput, fromRomeDateInput, toRomeDateInput, GENOVA_CATEGORIES, validateDemoEvents } from "./genova-admin-utils.mjs";

const signInPanel = document.querySelector("#sign-in-panel");
const adminPanel = document.querySelector("#admin-panel");
const notAdminPanel = document.querySelector("#not-admin-panel");
const signInForm = document.querySelector("#sign-in-form");
const signInButton = document.querySelector("#sign-in-button");
const runButton = document.querySelector("#run-fixture-button");
const refreshButton = document.querySelector("#refresh-button");
const refreshEventsButton = document.querySelector("#refresh-events-button");
const loadDemoButton = document.querySelector("#load-demo-events-button");
const clearDemoButton = document.querySelector("#clear-demo-events-button");
const setupMessage = document.querySelector("#setup-message");
const signInMessage = document.querySelector("#sign-in-message");
const adminMessage = document.querySelector("#admin-message");
const eventReviewMessage = document.querySelector("#event-review-message");
const demoMessage = document.querySelector("#demo-message");
const demoCount = document.querySelector("#demo-count");
const runsBody = document.querySelector("#runs-body");
const eventFactsBody = document.querySelector("#event-facts-body");
let supabase;
let isAdmin = false;
let runInProgress = false;
let eventUpdateInProgress = false;
let demoUpdateInProgress = false;
let refreshTimer;
let adminUserId = null;

function setMessage(element, message, kind = "") {
  element.textContent = message;
  if (kind) element.dataset.kind = kind;
  else delete element.dataset.kind;
}
function emptyTable(body, colspan, message) {
  body.replaceChildren();
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = colspan;
  cell.textContent = message;
  row.append(cell);
  body.append(row);
}
function showSignIn() {
  isAdmin = false;
  adminUserId = null;
  signInPanel.hidden = false;
  adminPanel.hidden = true;
  notAdminPanel.hidden = true;
  emptyTable(runsBody, 7, "Sign in to view private run history.");
  eventFactsBody.replaceChildren(document.createTextNode("Sign in to review collected real events."));
  if (refreshTimer) window.clearTimeout(refreshTimer);
}
function showNotAdmin() {
  isAdmin = false;
  adminUserId = null;
  signInPanel.hidden = true;
  adminPanel.hidden = true;
  notAdminPanel.hidden = false;
  if (refreshTimer) window.clearTimeout(refreshTimer);
}
function formatTime(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Rome", dateStyle: "medium", timeStyle: "short" }).format(date);
}
function formatAuditValue(key, value) {
  if (value == null || value === "") return "Unknown";
  if (["start_time", "end_time"].includes(key)) return formatTime(value);
  if (Array.isArray(value)) return value.join(", ") || "None";
  return String(value);
}
function appendCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  row.append(cell);
  return cell;
}
function renderRuns(runs) {
  runsBody.replaceChildren();
  if (!runs.length) return emptyTable(runsBody, 7, "No fixture runs yet.");
  for (const run of runs) {
    const row = document.createElement("tr");
    const statusCell = document.createElement("td");
    const status = document.createElement("span");
    status.className = "run-status";
    status.textContent = run.status;
    statusCell.append(status);
    const id = document.createElement("span");
    id.className = "run-id";
    id.textContent = run.id;
    statusCell.append(id);
    row.append(statusCell);
    appendCell(row, formatTime(run.queued_at));
    appendCell(row, String(run.candidate_count));
    appendCell(row, String(run.sources_scanned));
    appendCell(row, String(run.events_found));
    appendCell(row, String(run.events_needing_review));
    appendCell(row, run.error_summary || "Fixture only; public calendar unchanged.");
    runsBody.append(row);
  }
}
function actionButton(label, action, id, secondary = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.dataset.eventAction = action;
  button.dataset.eventId = String(id);
  if (secondary) button.className = "button-secondary";
  return button;
}
function fieldLabel(labelText, control, name) {
  const label = document.createElement("label");
  label.textContent = labelText;
  if (name) control.name = name;
  label.append(control);
  return label;
}
function categorySelect(category) {
  const select = document.createElement("select");
  select.name = "category";
  const unknown = document.createElement("option");
  unknown.value = "";
  unknown.textContent = "Choose a category";
  select.append(unknown);
  for (const [key, label] of GENOVA_CATEGORIES) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = label;
    select.append(option);
  }
  select.value = category || "";
  return select;
}
function normalizedEventUrl(value) {
  const url = new URL(value);
  const path = url.pathname.replace(/\/+$/, "") + "/";
  return `${url.protocol.toLowerCase()}//${url.host.toLowerCase()}${path}`;
}
function missingReviewDetails(event) {
  const required = [
    ["title", "event title"], ["start_time", "date and time"],
    ["location", "venue or location"], ["category", "category"],
    ["direct_url", "original source link"],
  ];
  return required.filter(([field]) => !String(event[field] ?? "").trim()).map(([, label]) => label);
}
function renderEventFacts(events) {
  eventFactsBody.replaceChildren();
  if (!events.length) {
    const empty = document.createElement("p");
    empty.textContent = "No collected events are waiting for review.";
    eventFactsBody.append(empty);
    return;
  }
  const appendGroup = (headingText, groupEvents) => {
    if (!groupEvents.length) return;
    const section = document.createElement("section");
    section.className = "review-group";
    const heading = document.createElement("h3");
    heading.textContent = `${headingText} (${groupEvents.length})`;
    section.append(heading);
    const list = document.createElement("div");
    list.className = "event-card-list";
    section.append(list);
    eventFactsBody.append(section);
    for (const event of groupEvents) renderEventCard(event, list);
  };
  appendGroup("Needs date extraction", events.filter((event) => event.date_state === "needs_date_extraction"));
  appendGroup("Current events for review", events.filter((event) => event.date_state === "current" && event.review_status !== "published"));
  appendGroup("Currently published", events.filter((event) => event.date_state === "current" && event.review_status === "published"));
}
function renderEventCard(event, container) {
    const card = document.createElement("article");
    card.className = "event-review-card";
    card.dataset.eventId = String(event.id);
    const head = document.createElement("div");
    head.className = "event-review-head";
    const title = document.createElement("h3");
    title.textContent = event.title;
    const status = document.createElement("span");
    status.className = "review-badge";
    status.textContent = `${event.review_status.replaceAll("_", " ")}${event.is_all_day ? " · all day" : ""}`;
    head.append(title, status);
    card.append(head);
    const original = document.createElement("a");
    original.href = event.direct_url;
    original.target = "_blank";
    original.rel = "noopener noreferrer";
    original.textContent = `Original listing: ${event.publisher_label}`;
    original.className = "review-source-link";
    card.append(original);

    const form = document.createElement("form");
    form.className = "event-edit-form";
    form.dataset.eventId = String(event.id);
    form.append(fieldLabel("Event title", Object.assign(document.createElement("input"), { type: "text", value: event.title, required: true }), "title"));
    const temporalType = event.is_all_day ? "date" : "datetime-local";
    const startValue = event.is_all_day ? toRomeDateInput(event.start_time) : toRomeInput(event.start_time);
    const endValue = event.is_all_day ? toRomeDateInput(event.end_time) : toRomeInput(event.end_time);
    form.append(fieldLabel(event.is_all_day ? "Date (Europe/Rome)" : "Date and time (Europe/Rome)", Object.assign(document.createElement("input"), { type: temporalType, value: startValue, required: event.review_status === "published" }), "start_time"));
    form.append(fieldLabel(event.is_all_day ? "Last date (optional)" : "End date and time (optional)", Object.assign(document.createElement("input"), { type: temporalType, value: endValue }), "end_time"));
    const allDayValue = document.createElement("input");
    allDayValue.type = "hidden";
    allDayValue.name = "is_all_day";
    allDayValue.value = event.is_all_day ? "true" : "false";
    form.append(allDayValue);
    form.append(fieldLabel("Venue / location", Object.assign(document.createElement("input"), { type: "text", value: event.location || "" }), "location"));
    form.append(fieldLabel("Category", categorySelect(event.category), "category"));
    form.append(fieldLabel("Original source link", Object.assign(document.createElement("input"), { type: "url", value: event.direct_url, required: true }), "direct_url"));
    const tagWrap = document.createElement("label");
    tagWrap.className = "tag-option";
    const tag = document.createElement("input");
    tag.type = "checkbox";
    tag.name = "date_night";
    tag.checked = Array.isArray(event.tags) && event.tags.includes("date-night");
    tagWrap.append(tag, document.createTextNode(" Date night"));
    form.append(tagWrap);
    const evidence = document.createElement("p");
    evidence.className = "event-evidence";
    const lastSeen = event.last_seen ? ` Last seen: ${formatTime(event.last_seen)}.` : "";
    evidence.textContent = `Category confidence: ${event.category_confidence == null ? "not provided" : `${Math.round(Number(event.category_confidence) * 100)}%`}. ${event.evidence_note || "No evidence note."}${lastSeen}`;
    form.append(evidence);
    const missing = missingReviewDetails(event);
    if (missing.length) {
      const requirements = document.createElement("p");
      requirements.className = "event-requirements";
      requirements.textContent = `To approve or publish, add: ${missing.join(", ")}.`;
      form.append(requirements);
    }
    const actions = document.createElement("div");
    actions.className = "actions event-actions";
    const save = document.createElement("button");
    save.type = "submit";
    save.textContent = "Save edits";
    actions.append(save);
    if (event.review_status === "needs_review") {
      const review = actionButton("Approve for publishing", "validated", event.id);
      review.disabled = missing.length > 0;
      actions.append(review);
    }
    else if (event.review_status === "validated") {
      const publish = actionButton("Publish", "published", event.id);
      publish.disabled = missing.length > 0;
      actions.append(publish);
    }
    else if (event.review_status === "published") actions.append(actionButton("Unpublish", "validated", event.id, true));
    else if (event.review_status === "rejected") actions.append(actionButton("Reopen", "needs_review", event.id, true));
    if (event.review_status !== "published" && event.review_status !== "rejected") actions.append(actionButton("Reject", "rejected", event.id, true));
    const history = document.createElement("button");
    history.type = "button";
    history.className = "button-secondary";
    history.dataset.auditId = String(event.id);
    history.textContent = "Change history";
    actions.append(history);
    form.append(actions);
    const historyBox = document.createElement("div");
    historyBox.className = "event-history";
    historyBox.hidden = true;
    historyBox.dataset.historyFor = String(event.id);
    form.append(historyBox);
    card.append(form);
    container.append(card);
}
async function refreshRuns() {
  if (!supabase || !isAdmin || runInProgress) return;
  try {
    const { data, error } = await supabase.from("agent_runs")
      .select("id,status,queued_at,candidate_count,sources_scanned,events_found,events_needing_review,error_summary")
      .order("queued_at", { ascending: false }).limit(20);
    if (error) throw error;
    renderRuns(data || []);
    const hasActive = (data || []).some((run) => run.status === "queued" || run.status === "running");
    if (refreshTimer) window.clearTimeout(refreshTimer);
    if (hasActive) refreshTimer = window.setTimeout(refreshRuns, 5000);
  } catch {
    setMessage(adminMessage, "Run history could not be loaded. Check the connection and admin access.", "error");
  }
}
async function refreshEventFacts() {
  if (!supabase || !isAdmin || eventUpdateInProgress) return;
  try {
    const { data, error } = await supabase.rpc("list_admin_genova_event_review_queue");
    if (error) throw error;
    renderEventFacts(data || []);
    setMessage(eventReviewMessage, (data || []).length
      ? "Check the source link, correct details, then mark the event reviewed."
      : "No collected events are waiting for review.");
  } catch {
    setMessage(eventReviewMessage, "Event facts could not be loaded. Check the hosted migration and admin access.", "error");
  }
}
async function refreshDemoEvents() {
  if (!supabase || !isAdmin) return;
  try {
    const { data, error } = await supabase.rpc("list_genova_demo_events");
    if (error) throw error;
    demoCount.textContent = `${(data || []).length} fictional demo ${(data || []).length === 1 ? "event" : "events"} appear on the sample calendar.`;
    clearDemoButton.disabled = !(data || []).length || demoUpdateInProgress;
  } catch {
    demoCount.textContent = "Demo data tools are unavailable until the current database migration is applied.";
    loadDemoButton.disabled = true;
    clearDemoButton.disabled = true;
  }
}
async function updateEventStatus(id, nextStatus) {
  const allowed = new Set(["needs_review", "validated", "published", "rejected"]);
  if (!supabase || !isAdmin || eventUpdateInProgress || !Number.isSafeInteger(id) || !allowed.has(nextStatus)) return;
  eventUpdateInProgress = true;
  refreshEventsButton.disabled = true;
  setMessage(eventReviewMessage, "Updating review status…");
  try {
    const { error } = await supabase.from("genova_event_facts").update({ review_status: nextStatus }).eq("id", id).is("superseded_by", null);
    if (error) throw error;
    eventUpdateInProgress = false;
    setMessage(eventReviewMessage, nextStatus === "published" ? "Published. This event can now appear on the live calendar." : "Review status updated.", "success");
    await refreshEventFacts();
  } catch {
    setMessage(eventReviewMessage, "The status could not be changed. Publishing requires a validated event with a title, date/time, venue, category, source link, and active approved source.", "error");
  } finally {
    eventUpdateInProgress = false;
    refreshEventsButton.disabled = false;
  }
}
async function saveEventEdits(form) {
  if (!supabase || !isAdmin || eventUpdateInProgress) return;
  const id = Number(form.dataset.eventId);
  const data = new FormData(form);
  const startText = String(data.get("start_time") || "");
  const endText = String(data.get("end_time") || "");
  const isAllDay = data.get("is_all_day") === "true";
  const startTime = startText ? (isAllDay ? fromRomeDateInput(startText) : fromRomeInput(startText)) : null;
  const endTime = endText ? (isAllDay ? fromRomeDateInput(endText) : fromRomeInput(endText)) : null;
  if ((startText && !startTime) || (endText && !endTime)) {
    setMessage(eventReviewMessage, "That date/time is invalid or ambiguous in Europe/Rome. Check the clock change and try again.", "error");
    return;
  }
  if (endTime && startTime && new Date(endTime) < new Date(startTime)) {
    setMessage(eventReviewMessage, "The end must be after the start.", "error");
    return;
  }
  const category = String(data.get("category") || "") || null;
  const patch = {
    title: String(data.get("title") || "").trim(), start_time: startTime, end_time: endTime, is_all_day: isAllDay,
    location: String(data.get("location") || "").trim() || null,
    direct_url: String(data.get("direct_url") || "").trim(), category,
    category_confidence: category ? 1 : null,
    tags: data.get("date_night") ? ["date-night"] : [],
  };
  if (!patch.title || !/^https:\/\//i.test(patch.direct_url)) {
    setMessage(eventReviewMessage, "Enter an event title and a secure https source link.", "error");
    return;
  }
  try { patch.normalized_url = normalizedEventUrl(patch.direct_url); }
  catch {
    setMessage(eventReviewMessage, "Enter a valid original event link.", "error");
    return;
  }
  eventUpdateInProgress = true;
  refreshEventsButton.disabled = true;
  setMessage(eventReviewMessage, "Saving your corrections…");
  try {
    const { data: updated, error } = await supabase.from("genova_event_facts").update(patch)
      .eq("id", id).is("superseded_by", null).select("id").maybeSingle();
    if (error || !updated) throw error || new Error("Event unavailable");
    eventUpdateInProgress = false;
    setMessage(eventReviewMessage, "Corrections saved to the private review record.", "success");
    await refreshEventFacts();
  } catch {
    setMessage(eventReviewMessage, "Corrections could not be saved. Check the event and current database migration.", "error");
  } finally {
    eventUpdateInProgress = false;
    refreshEventsButton.disabled = false;
  }
}
async function showHistory(button) {
  const id = Number(button.dataset.auditId);
  const box = eventFactsBody.querySelector(`[data-history-for="${id}"]`);
  if (!box || !isAdmin || !supabase) return;
  if (!box.hidden) { box.hidden = true; return; }
  box.hidden = false;
  box.textContent = "Loading change history…";
  try {
    const { data, error } = await supabase.from("genova_event_fact_audit")
      .select("changed_by,changed_at,old_values,new_values").eq("event_fact_id", id)
      .order("changed_at", { ascending: false }).limit(20);
    if (error) throw error;
    box.replaceChildren();
    if (!data?.length) { box.textContent = "No corrections recorded yet."; return; }
    for (const entry of data) {
      const item = document.createElement("article");
      item.className = "audit-entry";
      const changed = entry.changed_by === adminUserId ? "You" : entry.changed_by ? `Admin ${entry.changed_by.slice(0, 8)}` : "Collector";
      const keys = Object.keys(entry.new_values || {}).filter((key) =>
        JSON.stringify(entry.old_values?.[key]) !== JSON.stringify(entry.new_values?.[key]));
      const heading = document.createElement("p");
      heading.textContent = `${formatTime(entry.changed_at)} · ${changed}`;
      item.append(heading);
      const changes = document.createElement("ul");
      for (const key of keys) {
        const change = document.createElement("li");
        const label = key.replaceAll("_", " ");
        change.textContent = `${label}: ${formatAuditValue(key, entry.old_values?.[key])} → ${formatAuditValue(key, entry.new_values?.[key])}`;
        changes.append(change);
      }
      if (!keys.length) changes.textContent = "Record update";
      item.append(changes);
      box.append(item);
    }
  } catch {
    box.textContent = "Change history could not be loaded.";
  }
}
async function updateDemoEvents(clear) {
  if (!supabase || !isAdmin || demoUpdateInProgress) return;
  if (clear && !window.confirm("Remove all fictional demo events from the sample calendar? Real collected and published events are not affected.")) return;
  if (!clear && !window.confirm("Restore the fictional example events on the sample calendar? This replaces only the demo set.")) return;
  demoUpdateInProgress = true;
  loadDemoButton.disabled = true;
  clearDemoButton.disabled = true;
  setMessage(demoMessage, clear ? "Removing demo events…" : "Restoring demo events…");
  try {
    let result;
    if (clear) result = await supabase.rpc("clear_genova_demo_events");
    else {
      const response = await fetch("sample-events.json", { cache: "no-store" });
      if (!response.ok) throw new Error("Example data unavailable");
      const events = validateDemoEvents(await response.json());
      result = await supabase.rpc("replace_genova_demo_events", { p_events: events });
    }
    if (result.error) throw result.error;
    setMessage(demoMessage, clear
      ? `${result.data} fictional demo events removed. Refresh the public calendar to see it empty.`
      : `${result.data} fictional demo events restored. They are labeled examples, not real events.`, "success");
    await refreshDemoEvents();
  } catch {
    setMessage(demoMessage, "Demo events could not be changed. Check the connection and admin access.", "error");
  } finally {
    demoUpdateInProgress = false;
    loadDemoButton.disabled = false;
    await refreshDemoEvents();
  }
}
async function showAdmin(userId) {
  const { data, error } = await supabase.from("admin_users").select("user_id").eq("user_id", userId).maybeSingle();
  if (error) {
    setMessage(signInMessage, "Admin permission could not be checked. Review the Supabase setup.", "error");
    showSignIn();
    return false;
  }
  if (!data || data.user_id !== userId) { showNotAdmin(); return false; }
  isAdmin = true;
  adminUserId = userId;
  signInPanel.hidden = true;
  notAdminPanel.hidden = true;
  adminPanel.hidden = false;
  setMessage(signInMessage, "");
  setMessage(adminMessage, "Signed in. Demo data, collected events, and community submissions are managed separately.");
  await Promise.all([refreshRuns(), refreshEventFacts(), refreshDemoEvents()]);
  return true;
}
async function signOut() {
  if (supabase) await supabase.auth.signOut();
  showSignIn();
  setMessage(signInMessage, "You have signed out.");
}
signInForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!supabase) return;
  signInButton.disabled = true;
  setMessage(signInMessage, "Signing in…");
  try {
    const form = new FormData(signInForm);
    const { data, error } = await supabase.auth.signInWithPassword({ email: String(form.get("email") || "").trim(), password: String(form.get("password") || "") });
    if (error || !data.user) { setMessage(signInMessage, "Sign-in failed. Check the email and password.", "error"); return; }
    await showAdmin(data.user.id);
  } catch { setMessage(signInMessage, "The sign-in request failed. Check your connection and try again.", "error"); }
  finally { signInButton.disabled = false; }
});
runButton.addEventListener("click", async () => {
  if (!supabase || !isAdmin || runInProgress) return;
  runInProgress = true;
  runButton.disabled = true;
  setMessage(adminMessage, "Requesting the fixture-only check…");
  try {
    const { data, error } = await supabase.functions.invoke("genova-agent-run", { body: { mode: "fixture" } });
    if (error) { setMessage(adminMessage, "The fixture run could not be queued. Check the connection and setup.", "error"); return; }
    setMessage(adminMessage, "Fixture run queued. It scans zero websites and changes zero calendar events.", "success");
    if (data?.run_id) await refreshRuns();
  } catch { setMessage(adminMessage, "The fixture run request failed. Check your connection and try again.", "error"); }
  finally { runInProgress = false; runButton.disabled = false; }
});
runsBody.addEventListener("click", () => {});
eventFactsBody.addEventListener("submit", (event) => {
  const form = event.target.closest("form[data-event-id]");
  if (!form) return;
  event.preventDefault();
  saveEventEdits(form);
});
eventFactsBody.addEventListener("click", (event) => {
  const action = event.target.closest("button[data-event-action][data-event-id]");
  if (action) { updateEventStatus(Number(action.dataset.eventId), action.dataset.eventAction); return; }
  const history = event.target.closest("button[data-audit-id]");
  if (history) showHistory(history);
});
refreshButton.addEventListener("click", refreshRuns);
refreshEventsButton.addEventListener("click", refreshEventFacts);
loadDemoButton.addEventListener("click", () => updateDemoEvents(false));
clearDemoButton.addEventListener("click", () => updateDemoEvents(true));
document.querySelector("#sign-out-button").addEventListener("click", signOut);
document.querySelector("#not-admin-sign-out").addEventListener("click", signOut);
async function initialize() {
  try {
    const response = await fetch("config.json", { cache: "no-store" });
    const config = await response.json();
    const globals = config?.appGlobals;
    if (!response.ok || typeof globals?.supabaseUrl !== "string" || typeof globals?.supabasePublishableKey !== "string" || !globals.supabasePublishableKey.startsWith("sb_publishable_")) throw new Error("Missing publishable Supabase settings.");
    supabase = createClient(globals.supabaseUrl, globals.supabasePublishableKey, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false } });
    const { data, error } = await supabase.auth.getSession();
    if (!error && data.session?.user?.id) await showAdmin(data.session.user.id);
  } catch {
    setupMessage.hidden = false;
    for (const button of [signInButton, runButton, refreshEventsButton, loadDemoButton, clearDemoButton]) button.disabled = true;
  }
}
initialize();
