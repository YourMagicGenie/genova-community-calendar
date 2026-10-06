(function attachGenovaLive(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.GenovaLive = api;
})(typeof window === "undefined" ? globalThis : window, function createGenovaLive() {
  const TIME_ZONE = "Europe/Rome";
  const PUBLIC_FIELDS = new Set(["id", "title", "start_time", "end_time", "location", "publisher", "url", "category"]);

  function validateEvents(value) {
    if (!Array.isArray(value)) throw new Error("Live events response must be a list.");
    for (const event of value) {
      if (!event || typeof event !== "object" || Object.keys(event).some((key) => !PUBLIC_FIELDS.has(key))) {
        throw new Error("Live events response contains fields outside the public contract.");
      }
      if (!Number.isInteger(event.id) || typeof event.title !== "string" || !event.title.trim()) {
        throw new Error("Live event identity or title is invalid.");
      }
      const start = new Date(event.start_time);
      if (!event.start_time || Number.isNaN(start.getTime())) throw new Error("Published events require a valid start time.");
      if (typeof event.publisher !== "string" || !event.publisher.trim()) throw new Error("Published events require a publisher.");
      let url;
      try { url = new URL(event.url); } catch { throw new Error("Published events require a valid source link."); }
      if (url.protocol !== "https:") throw new Error("Published event links must use HTTPS.");
    }
    return value;
  }

  function formatTime(value) {
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: TIME_ZONE, weekday: "short", day: "numeric", month: "short",
      year: "numeric", hour: "2-digit", minute: "2-digit",
    }).format(new Date(value));
  }

  async function loadConfig(fetcher = globalThis.fetch) {
    const response = await fetcher("config.json", { cache: "no-store" });
    const config = await response.json();
    const globals = config?.appGlobals;
    if (!response.ok || typeof globals?.supabaseUrl !== "string" ||
        typeof globals?.supabasePublishableKey !== "string" ||
        !globals.supabasePublishableKey.startsWith("sb_publishable_")) {
      throw new Error("The public calendar connection is not configured.");
    }
    return globals;
  }

  async function loadEvents(fetcher = globalThis.fetch) {
    const config = await loadConfig(fetcher);
    const response = await fetcher(config.supabaseUrl.replace(/\/$/, "") + "/rest/v1/rpc/list_public_genova_events", {
      method: "POST",
      headers: {
        apikey: config.supabasePublishableKey,
        "content-type": "application/json",
      },
      body: "{}",
    });
    if (!response.ok) throw new Error("Validated live events could not be loaded.");
    return validateEvents(await response.json());
  }

  function render(document, container, status, events) {
    const cards = events.map((event) => {
      const article = document.createElement("article");
      article.className = "event-card";
      const meta = document.createElement("p");
      meta.className = "event-meta";
      meta.textContent = formatTime(event.start_time);
      const title = document.createElement("h3");
      title.textContent = event.title;
      const location = document.createElement("p");
      location.className = "event-location";
      location.textContent = event.location || "Location not listed";
      const category = document.createElement("p");
      category.className = "event-category";
      category.textContent = event.category || "Category pending";
      const source = document.createElement("a");
      source.className = "event-source";
      source.href = event.url;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = "Original listing · " + event.publisher;
      article.append(meta, title, location, category, source);
      return article;
    });
    if (!cards.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No validated real events are published yet.";
      cards.push(empty);
    }
    container.replaceChildren(...cards);
    status.textContent = events.length
      ? events.length + " validated " + (events.length === 1 ? "event" : "events")
      : "The real-source pilot is connected, but nothing has been published yet.";
  }

  async function start(document = globalThis.document, fetcher = globalThis.fetch) {
    const container = document.querySelector("#live-events");
    const status = document.querySelector("#live-status");
    try {
      const events = await loadEvents(fetcher);
      render(document, container, status, events);
    } catch (error) {
      container.replaceChildren();
      status.textContent = error.message;
    }
  }

  return { TIME_ZONE, PUBLIC_FIELDS, formatTime, loadConfig, loadEvents, render, start, validateEvents };
});
