import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const signInPanel = document.querySelector("#sign-in-panel");
const adminPanel = document.querySelector("#admin-panel");
const notAdminPanel = document.querySelector("#not-admin-panel");
const signInForm = document.querySelector("#sign-in-form");
const signInButton = document.querySelector("#sign-in-button");
const runButton = document.querySelector("#run-fixture-button");
const refreshButton = document.querySelector("#refresh-button");
const refreshEventsButton = document.querySelector("#refresh-events-button");
const setupMessage = document.querySelector("#setup-message");
const signInMessage = document.querySelector("#sign-in-message");
const adminMessage = document.querySelector("#admin-message");
const eventReviewMessage = document.querySelector("#event-review-message");
const runsBody = document.querySelector("#runs-body");
const eventFactsBody = document.querySelector("#event-facts-body");
let supabase;
let isAdmin = false;
let runInProgress = false;
let eventUpdateInProgress = false;
let refreshTimer;

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
  signInPanel.hidden = false;
  adminPanel.hidden = true;
  notAdminPanel.hidden = true;
  emptyTable(runsBody, 7, "Sign in to view private run history.");
  emptyTable(eventFactsBody, 6, "Sign in to review collected real events.");
  if (refreshTimer) window.clearTimeout(refreshTimer);
}

function showNotAdmin() {
  isAdmin = false;
  signInPanel.hidden = true;
  adminPanel.hidden = true;
  notAdminPanel.hidden = false;
  if (refreshTimer) window.clearTimeout(refreshTimer);
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("it-IT", {
    timeZone: "Europe/Rome", dateStyle: "medium", timeStyle: "short",
  }).format(date);
}

function appendCell(row, value, className = "") {
  const cell = document.createElement("td");
  cell.textContent = value;
  if (className) cell.className = className;
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

function renderEventFacts(events) {
  eventFactsBody.replaceChildren();
  if (!events.length) return emptyTable(eventFactsBody, 6, "No collected real events are waiting for review.");
  for (const event of events) {
    const row = document.createElement("tr");
    appendCell(row, event.review_status, "run-status");
    appendCell(row, formatTime(event.start_time));
    const titleCell = appendCell(row, event.title);
    const link = document.createElement("a");
    link.href = event.direct_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Original listing";
    link.className = "review-source-link";
    titleCell.append(document.createElement("br"), link);
    appendCell(row, event.location || "Unknown");
    appendCell(row, event.publisher_label);
    const actions = document.createElement("td");
    actions.className = "event-actions";
    if (event.review_status === "needs_review") {
      actions.append(actionButton("Validate", "validated", event.id), actionButton("Reject", "rejected", event.id, true));
    } else if (event.review_status === "validated") {
      actions.append(actionButton("Publish", "published", event.id), actionButton("Reject", "rejected", event.id, true));
    } else if (event.review_status === "published") {
      actions.append(actionButton("Unpublish", "validated", event.id, true));
    } else if (event.review_status === "rejected") {
      actions.append(actionButton("Reopen", "needs_review", event.id, true));
    }
    row.append(actions);
    eventFactsBody.append(row);
  }
}

async function refreshRuns() {
  if (!supabase || !isAdmin || runInProgress) return;
  try {
    const { data, error } = await supabase
      .from("agent_runs")
      .select("id, status, queued_at, candidate_count, sources_scanned, events_found, events_needing_review, error_summary")
      .order("queued_at", { ascending: false })
      .limit(20);
    if (error) throw error;
    renderRuns(data || []);
    const hasActiveRun = (data || []).some((run) => run.status === "queued" || run.status === "running");
    if (refreshTimer) window.clearTimeout(refreshTimer);
    if (hasActiveRun) refreshTimer = window.setTimeout(refreshRuns, 5000);
  } catch {
    setMessage(adminMessage, "Run history could not be loaded. Check the Supabase connection and access setup.", "error");
  }
}

async function refreshEventFacts() {
  if (!supabase || !isAdmin || eventUpdateInProgress) return;
  try {
    const { data, error } = await supabase
      .from("genova_event_facts")
      .select("id, title, start_time, location, publisher_label, direct_url, category, category_confidence, review_status, last_seen")
      .is("superseded_by", null)
      .order("start_time", { ascending: true, nullsFirst: false })
      .limit(100);
    if (error) throw error;
    renderEventFacts(data || []);
    setMessage(eventReviewMessage, (data || []).length
      ? "Review collected facts against the original listing before publishing."
      : "No real-source facts have been collected yet.");
  } catch {
    setMessage(eventReviewMessage, "Real event facts could not be loaded. Check the hosted migration and admin access.", "error");
  }
}

async function updateEventStatus(id, nextStatus) {
  const allowed = new Set(["needs_review", "validated", "published", "rejected"]);
  if (!supabase || !isAdmin || eventUpdateInProgress || !Number.isSafeInteger(id) || !allowed.has(nextStatus)) return;
  eventUpdateInProgress = true;
  refreshEventsButton.disabled = true;
  setMessage(eventReviewMessage, "Updating review state…");
  try {
    const { error } = await supabase.from("genova_event_facts").update({ review_status: nextStatus }).eq("id", id);
    if (error) throw error;
    setMessage(eventReviewMessage, nextStatus === "published"
      ? "Published. The event is now eligible for the field-limited public route."
      : "Review state updated.", "success");
    await refreshEventFacts();
  } catch {
    setMessage(eventReviewMessage, "The review state could not be changed. Publishing requires a known start time and an active approved source.", "error");
  } finally {
    eventUpdateInProgress = false;
    refreshEventsButton.disabled = false;
  }
}

async function showAdmin(userId) {
  const { data, error } = await supabase.from("admin_users").select("user_id").eq("user_id", userId).maybeSingle();
  if (error) {
    setMessage(signInMessage, "Admin permission could not be checked. Review the Supabase setup.", "error");
    showSignIn();
    return false;
  }
  if (!data || data.user_id !== userId) {
    showNotAdmin();
    return false;
  }
  isAdmin = true;
  signInPanel.hidden = true;
  notAdminPanel.hidden = true;
  adminPanel.hidden = false;
  setMessage(signInMessage, "");
  setMessage(adminMessage, "Signed in. The fixture runner remains separate from real-source review.");
  await Promise.all([refreshRuns(), refreshEventFacts()]);
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
    const { data, error } = await supabase.auth.signInWithPassword({
      email: String(form.get("email") || "").trim(),
      password: String(form.get("password") || ""),
    });
    if (error || !data.user) {
      setMessage(signInMessage, "Sign-in failed. Check the email and password.", "error");
      return;
    }
    await showAdmin(data.user.id);
  } catch {
    setMessage(signInMessage, "The sign-in request failed. Check your connection and try again.", "error");
  } finally {
    signInButton.disabled = false;
  }
});

runButton.addEventListener("click", async () => {
  if (!supabase || !isAdmin || runInProgress) return;
  runInProgress = true;
  runButton.disabled = true;
  setMessage(adminMessage, "Requesting the fixture-only check…");
  try {
    const { data, error } = await supabase.functions.invoke("genova-agent-run", { body: { mode: "fixture" } });
    if (error) {
      setMessage(adminMessage, "The fixture run could not be queued. Check the connection and required setup.", "error");
      return;
    }
    setMessage(adminMessage, "Fixture run queued. This does not scan websites or change public events.", "success");
    if (data?.run_id) await refreshRuns();
  } catch {
    setMessage(adminMessage, "The fixture run request failed. Check your connection and try again.", "error");
  } finally {
    runInProgress = false;
    runButton.disabled = false;
  }
});

runsBody.addEventListener("click", () => {});
eventFactsBody.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-event-action][data-event-id]");
  if (!button) return;
  const id = Number(button.dataset.eventId);
  updateEventStatus(id, button.dataset.eventAction);
});
refreshButton.addEventListener("click", refreshRuns);
refreshEventsButton.addEventListener("click", refreshEventFacts);
document.querySelector("#sign-out-button").addEventListener("click", signOut);
document.querySelector("#not-admin-sign-out").addEventListener("click", signOut);

async function initialize() {
  try {
    const response = await fetch("config.json", { cache: "no-store" });
    const config = await response.json();
    const globals = config?.appGlobals;
    if (!response.ok || typeof globals?.supabaseUrl !== "string" ||
        typeof globals?.supabasePublishableKey !== "string" ||
        !globals.supabasePublishableKey.startsWith("sb_publishable_")) {
      throw new Error("Missing publishable Supabase settings.");
    }
    supabase = createClient(globals.supabaseUrl, globals.supabasePublishableKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
    });
    const { data, error } = await supabase.auth.getSession();
    if (!error && data.session?.user?.id) await showAdmin(data.session.user.id);
  } catch {
    setupMessage.hidden = false;
    signInButton.disabled = true;
    runButton.disabled = true;
    refreshEventsButton.disabled = true;
  }
}

initialize();
