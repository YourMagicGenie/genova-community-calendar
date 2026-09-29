(function attachSamplePreview(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.GenovaSamplePreview = api;
})(typeof window === 'undefined' ? globalThis : window, function createSamplePreview() {
  const TIME_ZONE = 'Europe/Rome';
  const CATEGORIES = new Set(['music', 'theatre', 'art', 'sports', 'food', 'outdoors', 'community']);
  const CATEGORY_LABELS = {
    music: 'Music',
    theatre: 'Theatre',
    art: 'Art & exhibitions',
    sports: 'Sports',
    food: 'Food & drink',
    outdoors: 'Outdoor',
    community: 'Community',
  };

  function matchesSampleRoute(value) {
    const url = value instanceof URL ? value : new URL(value, 'https://calendar.example/');
    return url.searchParams.get('city') === 'genova' && url.searchParams.get('preview') === 'sample';
  }

  function validateSampleEvents(events) {
    if (!Array.isArray(events)) throw new Error('Sample events must be a list.');

    for (const [index, event] of events.entries()) {
      const prefix = `Sample event ${index + 1}`;
      for (const field of ['id', 'title', 'sourceName', 'sourceUrl', 'venue']) {
        if (typeof event[field] !== 'string' || !event[field].trim()) {
          throw new Error(`${prefix} is missing ${field}.`);
        }
      }
      if (!CATEGORIES.has(event.category)) throw new Error(`${prefix} has an unknown category.`);
      if (!Number.isInteger(event.daysFromToday) || event.daysFromToday < 0 || event.daysFromToday > 60) {
        throw new Error(`${prefix} has an invalid daysFromToday value.`);
      }
      if (event.startTime !== null && !/^([01]\d|2[0-3]):[0-5]\d$/.test(event.startTime)) {
        throw new Error(`${prefix} has an invalid startTime; use null when the time is unknown.`);
      }
      if (!Array.isArray(event.tags) || event.tags.some((tag) => typeof tag !== 'string')) {
        throw new Error(`${prefix} has invalid tags.`);
      }

      let sourceUrl;
      try {
        sourceUrl = new URL(event.sourceUrl);
      } catch (_) {
        throw new Error(`${prefix} must link to example.org sample content.`);
      }
      if (sourceUrl.protocol !== 'https:' || !['example.org', 'www.example.org'].includes(sourceUrl.hostname)) {
        throw new Error(`${prefix} must link to example.org sample content.`);
      }
    }
    return events;
  }

  async function loadSampleEvents(fetcher) {
    if (typeof fetcher !== 'function') throw new Error('Sample events could not be loaded.');
    let response;
    try {
      response = await fetcher('sample-events.json', { cache: 'no-store' });
      if (!response || !response.ok) throw new Error('Fixture request failed.');
      return validateSampleEvents(await response.json());
    } catch (_) {
      throw new Error('Sample events could not be loaded. Reload the preview or report the broken sample file.');
    }
  }

  function dateAtOffset(daysFromToday, now = new Date(), timeZone = TIME_ZONE) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(now);
    const dateParts = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    const date = new Date(Date.UTC(
      Number(dateParts.year),
      Number(dateParts.month) - 1,
      Number(dateParts.day) + daysFromToday,
    ));
    return [date.getUTCFullYear(), String(date.getUTCMonth() + 1).padStart(2, '0'), String(date.getUTCDate()).padStart(2, '0')].join('-');
  }

  function isWeekend(dateString) {
    const [year, month, day] = dateString.split('-').map(Number);
    const weekday = new Date(Date.UTC(year, month - 1, day, 12)).getUTCDay();
    return weekday === 0 || weekday === 6;
  }

  function filterSampleEvents(events, options = {}) {
    const now = options.now || new Date();
    const timeZone = options.timeZone || TIME_ZONE;
    const category = options.category || 'all';
    const dateWindow = options.dateWindow || 'week';
    const dateNightOnly = options.dateNightOnly || false;

    return events
      .filter((event) => category === 'all' || event.category === category)
      .filter((event) => !dateNightOnly || event.tags.includes('date-night'))
      .map((event) => ({ ...event, date: dateAtOffset(event.daysFromToday, now, timeZone) }))
      .filter((event) => {
        if (dateWindow === 'week') return event.daysFromToday <= 6;
        if (dateWindow === 'weekend') return event.daysFromToday <= 6 && isWeekend(event.date);
        return true;
      })
      .sort((a, b) => a.date.localeCompare(b.date) || (a.startTime || '99:99').localeCompare(b.startTime || '99:99'));
  }

  function formatDate(dateString, timeZone = TIME_ZONE) {
    const date = new Date(`${dateString}T12:00:00.000Z`);
    return new Intl.DateTimeFormat('en-GB', {
      timeZone,
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    }).format(date);
  }

  function createEventCard(document, event) {
    const article = document.createElement('article');
    article.className = 'event-card';
    article.dataset.category = event.category;

    const meta = document.createElement('p');
    meta.className = 'event-meta';
    meta.textContent = `${formatDate(event.date)} · ${event.startTime || 'Time not listed'}${event.startTime ? ` · ${TIME_ZONE}` : ''}`;

    const title = document.createElement('h2');
    title.textContent = event.title;

    const venue = document.createElement('p');
    venue.className = 'event-venue';
    venue.textContent = event.venue;

    const tags = document.createElement('div');
    tags.className = 'event-tags';
    const category = document.createElement('span');
    category.className = 'tag';
    category.textContent = CATEGORY_LABELS[event.category];
    tags.append(category);
    if (event.tags.includes('date-night')) {
      const dateNight = document.createElement('span');
      dateNight.className = 'tag tag-accent';
      dateNight.textContent = 'Date night';
      tags.append(dateNight);
    }

    const source = document.createElement('a');
    source.className = 'event-source';
    source.href = event.sourceUrl;
    source.target = '_blank';
    source.rel = 'noopener noreferrer';
    source.textContent = `Example source: ${event.sourceName}`;

    article.append(meta, title, venue, tags, source);
    return article;
  }

  function renderSampleEvents(document, list, status, events, options = {}) {
    const visible = filterSampleEvents(events, options);
    const cards = visible.map((event) => createEventCard(document, event));
    if (cards.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = 'No sample events match these filters.';
      cards.push(empty);
    }
    list.replaceChildren(...cards);
    status.textContent = `${visible.length} sample ${visible.length === 1 ? 'event' : 'events'}`;
    return visible;
  }

  async function startSamplePreview(document = globalThis.document, fetcher = globalThis.fetch) {
    const list = document.querySelector('#event-list');
    const status = document.querySelector('#event-status');
    const categoryFilter = document.querySelector('#category-filter');
    const dateFilter = document.querySelector('#date-filter');
    const dateNightFilter = document.querySelector('#date-night-filter');

    try {
      const events = await loadSampleEvents(fetcher);
      function render() {
        renderSampleEvents(document, list, status, events, {
          category: categoryFilter.value,
          dateWindow: dateFilter.value,
          dateNightOnly: dateNightFilter.getAttribute('aria-pressed') === 'true',
        });
      }
      categoryFilter.addEventListener('change', render);
      dateFilter.addEventListener('change', render);
      dateNightFilter.addEventListener('click', () => {
        const pressed = dateNightFilter.getAttribute('aria-pressed') === 'true';
        dateNightFilter.setAttribute('aria-pressed', String(!pressed));
        render();
      });
      render();
    } catch (error) {
      list.replaceChildren();
      status.textContent = error.message;
    }
  }

  return {
    CATEGORY_LABELS,
    TIME_ZONE,
    dateAtOffset,
    filterSampleEvents,
    formatDate,
    loadSampleEvents,
    matchesSampleRoute,
    renderSampleEvents,
    startSamplePreview,
    validateSampleEvents,
  };
});
