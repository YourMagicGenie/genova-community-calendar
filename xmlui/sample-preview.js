(function attachSamplePreview(root, factory) {
  const taxonomy = typeof module === 'object' && module.exports ? require('../genova-taxonomy.json') : null;
  const api = factory(taxonomy);
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.GenovaSamplePreview = api;
})(typeof window === 'undefined' ? globalThis : window, function createSamplePreview(initialTaxonomy) {
  const TIME_ZONE = 'Europe/Rome';
  let taxonomy = initialTaxonomy;

  function validateTaxonomy(value) {
    if (!value || !Array.isArray(value.categories) || !Array.isArray(value.tags)) {
      throw new Error('Genova category settings could not be loaded.');
    }
    const keys = value.categories.map((category) => category.key);
    if (keys.some((key) => typeof key !== 'string' || !key.trim()) || new Set(keys).size !== keys.length) {
      throw new Error('Genova category settings could not be loaded.');
    }
    if (value.tags.some((tag) => keys.includes(tag.key))) {
      throw new Error('Genova category settings could not be loaded.');
    }
    return value;
  }

  function categoryKeys() {
    return taxonomy.categories.map((category) => category.key);
  }

  function categoryLabels() {
    return Object.fromEntries(taxonomy.categories.map((category) => [category.key, category.label]));
  }

  function tagLabel(key) {
    return taxonomy.tags.find((tag) => tag.key === key)?.label || key;
  }

  async function loadTaxonomy(fetcher = globalThis.fetch) {
    if (taxonomy) return validateTaxonomy(taxonomy);
    try {
      const response = await fetcher('../genova-taxonomy.json', { cache: 'no-store' });
      if (!response || !response.ok) throw new Error('Taxonomy request failed.');
      taxonomy = validateTaxonomy(await response.json());
      return taxonomy;
    } catch (_) {
      throw new Error('Genova category settings could not be loaded. Reload the preview or report the broken category file.');
    }
  }

  function buildCategoryFilters(document, container, selectedKeys = categoryKeys()) {
    const selected = new Set(selectedKeys);
    const labels = taxonomy.categories.map((category) => {
      const label = document.createElement('label');
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.name = 'category-filter';
      input.value = category.key;
      input.checked = selected.has(category.key);
      label.append(input, document.createTextNode(category.label));
      return label;
    });
    container.replaceChildren(...labels);
    return labels;
  }

  function matchesSampleRoute(value) {
    const url = value instanceof URL ? value : new URL(value, 'https://calendar.example/');
    const city = url.searchParams.get('city');
    return city === null || city === 'genova';
  }

  function categoriesFor(event) {
    const values = Array.isArray(event.categories) && event.categories.length
      ? event.categories
      : [event.category];
    return [...new Set(values)];
  }

  function validateSampleEvents(events, categoryTaxonomy = taxonomy) {
    if (!Array.isArray(events)) throw new Error('Sample events must be a list.');
    const validCategories = new Set(validateTaxonomy(categoryTaxonomy).categories.map((category) => category.key));
    const validTags = new Set(categoryTaxonomy.tags.map((tag) => tag.key));

    for (const [index, event] of events.entries()) {
      const prefix = `Sample event ${index + 1}`;
      for (const field of ['id', 'title', 'sourceName', 'sourceUrl', 'venue']) {
        if (typeof event[field] !== 'string' || !event[field].trim()) {
          throw new Error(`${prefix} is missing ${field}.`);
        }
      }
      if (categoriesFor(event).some((category) => !validCategories.has(category))) {
        throw new Error(`${prefix} has an unknown category.`);
      }
      if (!Number.isInteger(event.daysFromToday) || event.daysFromToday < 0 || event.daysFromToday > 60) {
        throw new Error(`${prefix} has an invalid daysFromToday value.`);
      }
      if (event.startTime !== null && !/^([01]\d|2[0-3]):[0-5]\d$/.test(event.startTime)) {
        throw new Error(`${prefix} has an invalid startTime; use null when the time is unknown.`);
      }
      if (!Array.isArray(event.tags) || event.tags.some((tag) => !validTags.has(tag))) {
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

  async function loadSampleEvents(fetcher, categoryTaxonomy = taxonomy) {
    if (typeof fetcher !== 'function') throw new Error('Sample events could not be loaded.');
    try {
      const response = await fetcher('sample-events.json', { cache: 'no-store' });
      if (!response || !response.ok) throw new Error('Fixture request failed.');
      return validateSampleEvents(await response.json(), categoryTaxonomy);
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

  function localDateParts(date, timeZone = TIME_ZONE) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(date);
    return Object.fromEntries(parts.map((part) => [part.type, part.value]));
  }

  function isoDate(year, monthIndex, day) {
    const value = new Date(Date.UTC(year, monthIndex, day));
    return [value.getUTCFullYear(), String(value.getUTCMonth() + 1).padStart(2, '0'), String(value.getUTCDate()).padStart(2, '0')].join('-');
  }

  function calendarMonthInfo(now = new Date(), monthOffset = 0, timeZone = TIME_ZONE) {
    const parts = localDateParts(now, timeZone);
    const first = new Date(Date.UTC(Number(parts.year), Number(parts.month) - 1 + monthOffset, 1, 12));
    const year = first.getUTCFullYear();
    const monthIndex = first.getUTCMonth();
    return {
      year,
      monthIndex,
      key: `${year}-${String(monthIndex + 1).padStart(2, '0')}`,
      label: new Intl.DateTimeFormat('en-GB', { timeZone, month: 'long', year: 'numeric' }).format(first),
    };
  }

  function calendarMonthCells(now = new Date(), monthOffset = 0, timeZone = TIME_ZONE) {
    const month = calendarMonthInfo(now, monthOffset, timeZone);
    const firstWeekday = new Date(Date.UTC(month.year, month.monthIndex, 1, 12)).getUTCDay();
    const leadingDays = (firstWeekday + 6) % 7;
    const daysInMonth = new Date(Date.UTC(month.year, month.monthIndex + 1, 0, 12)).getUTCDate();
    const count = Math.ceil((leadingDays + daysInMonth) / 7) * 7;
    return Array.from({ length: count }, (_, index) => {
      const dayNumber = index - leadingDays + 1;
      const value = new Date(Date.UTC(month.year, month.monthIndex, dayNumber, 12));
      return {
        date: isoDate(value.getUTCFullYear(), value.getUTCMonth(), value.getUTCDate()),
        dayNumber: value.getUTCDate(),
        inMonth: value.getUTCMonth() === month.monthIndex,
      };
    });
  }

  function isWeekend(dateString) {
    const [year, month, day] = dateString.split('-').map(Number);
    const weekday = new Date(Date.UTC(year, month - 1, day, 12)).getUTCDay();
    return weekday === 0 || weekday === 6;
  }

  function sortEvents(events) {
    return [...events].sort((a, b) => a.date.localeCompare(b.date) || (a.startTime || '99:99').localeCompare(b.startTime || '99:99'));
  }

  function filterSampleEvents(events, options = {}) {
    const now = options.now || new Date();
    const timeZone = options.timeZone || TIME_ZONE;
    const category = options.category || 'all';
    const dateWindow = options.dateWindow || 'week';
    const dateNightOnly = options.dateNightOnly || false;

    return sortEvents(events
      .filter((event) => category === 'all' || categoriesFor(event).includes(category))
      .filter((event) => !dateNightOnly || event.tags.includes('date-night'))
      .map((event) => ({ ...event, date: dateAtOffset(event.daysFromToday, now, timeZone) }))
      .filter((event) => {
        if (dateWindow === 'week') return event.daysFromToday <= 6;
        if (dateWindow === 'weekend') return event.daysFromToday <= 6 && isWeekend(event.date);
        return true;
      }));
  }

  function filterCalendarEvents(events, options = {}) {
    const now = options.now || new Date();
    const monthOffset = options.monthOffset || 0;
    const timeZone = options.timeZone || TIME_ZONE;
    const selectedCategories = options.selectedCategories === undefined
      ? categoryKeys()
      : options.selectedCategories;
    const selected = new Set(selectedCategories);
    const cells = calendarMonthCells(now, monthOffset, timeZone);
    const firstDate = cells[0].date;
    const lastDate = cells.at(-1).date;

    return sortEvents(events
      .map((event) => ({ ...event, date: dateAtOffset(event.daysFromToday, now, timeZone) }))
      .filter((event) => event.date >= firstDate && event.date <= lastDate)
      .filter((event) => categoriesFor(event).some((category) => selected.has(category)))
      .filter((event) => !options.dateNightOnly || event.tags.includes('date-night')));
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

  function appendCategoryTags(document, container, event) {
    for (const value of categoriesFor(event)) {
      const category = document.createElement('span');
      category.className = 'tag';
      category.textContent = categoryLabels()[value];
      container.append(category);
    }
    if (event.tags.includes('date-night')) {
      const dateNight = document.createElement('span');
      dateNight.className = 'tag tag-accent';
      dateNight.textContent = tagLabel('date-night');
      container.append(dateNight);
    }
  }

  function createEventCard(document, event) {
    const article = document.createElement('article');
    article.className = 'event-card';
    article.dataset.category = categoriesFor(event).join(' ');

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
    appendCategoryTags(document, tags, event);

    const source = document.createElement('a');
    source.className = 'event-source';
    source.href = event.sourceUrl;
    source.target = '_blank';
    source.rel = 'noopener noreferrer';
    source.textContent = `Example source: ${event.sourceName}`;

    article.append(meta, title, venue, tags, source);
    return article;
  }

  function createCompactEvent(document, event) {
    const item = document.createElement('li');
    item.className = 'calendar-event';
    const link = document.createElement('a');
    link.className = 'calendar-event-link';
    link.href = event.sourceUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    const title = document.createElement('span');
    title.className = 'calendar-event-title';
    title.textContent = event.title;
    const time = document.createElement('span');
    time.className = 'calendar-event-time';
    time.textContent = event.startTime || 'Time not listed';
    link.append(title, time);
    const source = document.createElement('span');
    source.className = 'calendar-event-source';
    source.textContent = `Example source: ${event.sourceName}`;
    item.append(link, source);
    const tags = document.createElement('span');
    tags.className = 'calendar-event-categories';
    tags.textContent = categoriesFor(event).map((value) => categoryLabels()[value]).join(' · ');
    if (event.tags.includes('date-night')) tags.textContent += ` · ${tagLabel('date-night')}`;
    item.append(tags);
    return item;
  }

  function renderCalendar(document, grid, status, events, options = {}) {
    const visible = filterCalendarEvents(events, options);
    const byDate = new Map();
    for (const event of visible) {
      if (!byDate.has(event.date)) byDate.set(event.date, []);
      byDate.get(event.date).push(event);
    }

    const cells = calendarMonthCells(options.now || new Date(), options.monthOffset || 0, options.timeZone || TIME_ZONE);
    const calendarCells = cells.map((cell) => {
      const day = document.createElement('li');
      day.className = `calendar-day${cell.inMonth ? '' : ' calendar-day-adjacent'}`;
      day.dataset.date = cell.date;

      const heading = document.createElement('h3');
      heading.className = 'calendar-day-heading';
      const date = document.createElement('time');
      date.dateTime = cell.date;
      date.textContent = String(cell.dayNumber);
      heading.append(date);
      const fullDate = document.createElement('span');
      fullDate.className = 'calendar-day-full-date';
      fullDate.textContent = formatDate(cell.date, options.timeZone || TIME_ZONE);
      heading.append(fullDate);
      day.append(heading);

      const dayEvents = byDate.get(cell.date) || [];
      if (dayEvents.length) {
        const list = document.createElement('ul');
        list.className = 'calendar-day-events';
        for (const event of dayEvents.slice(0, 3)) list.append(createCompactEvent(document, event));
        day.append(list);
        if (dayEvents.length > 3) {
          const details = document.createElement('details');
          details.className = 'calendar-day-more';
          const summary = document.createElement('summary');
          summary.textContent = `+${dayEvents.length - 3} more`;
          details.append(summary);
          const overflow = document.createElement('ul');
          overflow.className = 'calendar-day-events calendar-day-overflow';
          for (const event of dayEvents.slice(3)) overflow.append(createCompactEvent(document, event));
          details.append(overflow);
          day.append(details);
        }
      } else {
        day.className += ' calendar-day-empty';
        const emptyMessage = document.createElement('p');
        emptyMessage.className = 'calendar-day-empty-message';
        emptyMessage.textContent = 'No events listed';
        day.append(emptyMessage);
      }
      return day;
    });
    grid.replaceChildren(...calendarCells);
    status.textContent = visible.length
      ? `${visible.length} sample ${visible.length === 1 ? 'event' : 'events'}`
      : 'No sample events match these filters.';
    return visible;
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
    const grid = document.querySelector('#calendar-grid');
    const status = document.querySelector('#calendar-status');
    const monthTitle = document.querySelector('#calendar-month');
    const dateNightFilter = document.querySelector('#date-night-filter');
    const previousMonth = document.querySelector('#previous-month');
    const nextMonth = document.querySelector('#next-month');
    const currentMonth = document.querySelector('#current-month');
    const categoryFilterContainer = document.querySelector('#category-filter-options');
    let monthOffset = 0;

    try {
      const categoryTaxonomy = await loadTaxonomy(fetcher);
      buildCategoryFilters(document, categoryFilterContainer, categoryTaxonomy.categories.map((category) => category.key));
      dateNightFilter.textContent = tagLabel('date-night');
      const events = await loadSampleEvents(fetcher, categoryTaxonomy);
      const categoryFilters = [...document.querySelectorAll('input[name="category-filter"]')];
      function render() {
        const now = new Date();
        monthTitle.textContent = calendarMonthInfo(now, monthOffset).label;
        renderCalendar(document, grid, status, events, {
          monthOffset,
          selectedCategories: categoryFilters.filter((input) => input.checked).map((input) => input.value),
          dateNightOnly: dateNightFilter.getAttribute('aria-pressed') === 'true',
          now,
        });
      }
      for (const input of categoryFilters) input.addEventListener('change', render);
      dateNightFilter.addEventListener('click', () => {
        const pressed = dateNightFilter.getAttribute('aria-pressed') === 'true';
        dateNightFilter.setAttribute('aria-pressed', String(!pressed));
        render();
      });
      previousMonth.addEventListener('click', () => { monthOffset -= 1; render(); });
      nextMonth.addEventListener('click', () => { monthOffset += 1; render(); });
      currentMonth.addEventListener('click', () => { monthOffset = 0; render(); });
      render();
    } catch (error) {
      grid.replaceChildren();
      status.textContent = error.message;
    }
  }

  return {
    TIME_ZONE,
    buildCategoryFilters,
    calendarMonthCells,
    calendarMonthInfo,
    categoriesFor,
    categoryKeys,
    get CATEGORY_LABELS() { return categoryLabels(); },
    dateAtOffset,
    filterCalendarEvents,
    filterSampleEvents,
    formatDate,
    loadSampleEvents,
    loadTaxonomy,
    matchesSampleRoute,
    renderCalendar,
    renderSampleEvents,
    startSamplePreview,
    validateSampleEvents,
  };
});
