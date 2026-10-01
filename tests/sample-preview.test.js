const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

let preview;
try {
  preview = require('../xmlui/sample-preview.js');
} catch (_) {
  preview = null;
}

function requirePreview() {
  assert.ok(preview, 'the isolated Genova sample preview module must exist');
  return preview;
}

function event(overrides = {}) {
  return {
    id: 'example-jazz',
    title: 'Jazz by the harbour',
    category: 'music',
    daysFromToday: 4,
    startTime: '19:30',
    venue: 'Example venue, Genova',
    sourceName: 'Example local publisher',
    sourceUrl: 'https://example.org/events/jazz',
    tags: ['date-night'],
    ...overrides,
  };
}

class FakeElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this._textContent = '';
  }
  append(...elements) { this.children.push(...elements); }
  replaceChildren(...elements) { this.children = [...elements]; }
  set textContent(value) { this._textContent = value; this.children = []; }
  get textContent() { return this._textContent + this.children.map((child) => child.textContent).join(''); }
  setAttribute(name, value) { this.attributes[name] = value; }
}

class FakeDocument {
  createElement(tagName) { return new FakeElement(tagName); }
  createTextNode(text) { const node = new FakeElement('#text'); node.textContent = text; return node; }
}

test('sample preview route is the default and only serves Genova', () => {
  const api = requirePreview();
  assert.equal(api.matchesSampleRoute('https://calendar.example/'), true);
  assert.equal(api.matchesSampleRoute('https://calendar.example/?city=genova'), true);
  assert.equal(api.matchesSampleRoute('https://calendar.example/?city=genova&preview=sample'), true);
  assert.equal(api.matchesSampleRoute('https://calendar.example/?city=asheville&preview=sample'), false);
});

test('site entry defaults to the Genova preview and never opens the inherited app', () => {
  const html = readFileSync(new URL('../index.html', `file://${__filename}`), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/i)?.[1];
  assert.ok(script, 'site entry should include its route selector');

  function destination(search) {
    let target = '';
    vm.runInNewContext(script, {
      URLSearchParams,
      window: { location: { search, hash: '#events', replace: (value) => { target = value; } } },
    });
    return target;
  }

  assert.equal(destination(''), 'xmlui/genova-sample-preview.html?city=genova&preview=sample#events');
  assert.equal(destination('?city=genova'), 'xmlui/genova-sample-preview.html?city=genova&preview=sample#events');
  assert.equal(destination('?city=asheville'), 'xmlui/not-configured.html?city=asheville#events');
  const notConfigured = readFileSync(new URL('../xmlui/not-configured.html', `file://${__filename}`), 'utf8');
  assert.match(notConfigured, /currently scoped to Genova/);
  assert.match(notConfigured, /There is no live event feed yet/);
});

test('direct inherited app entry is disabled and contains no upstream database config', () => {
  const html = readFileSync(new URL('../xmlui/index.html', `file://${__filename}`), 'utf8');
  const config = JSON.parse(readFileSync(new URL('../xmlui/config.json', `file://${__filename}`), 'utf8'));
  assert.match(html, /genova-sample-preview\.html/);
  assert.doesNotMatch(html, /shell\.js|config\.json|supabase-js|dzpdualvwspgqghrysyz/);
  assert.equal(config.supabaseUrl, undefined);
  assert.equal(config.supabasePublishableKey, undefined);
});

test('public source and city defaults contain Genova only and no approved publishers', () => {
  const cities = JSON.parse(readFileSync(new URL('../cities.json', `file://${__filename}`), 'utf8'));
  const priorities = JSON.parse(readFileSync(new URL('../source_priority.json', `file://${__filename}`), 'utf8'));
  assert.deepEqual(cities, { genova: { timezone: 'Europe/Rome' } });
  assert.deepEqual(priorities, { aggregators: [] });
});

test('sample page labels itself as fictional and uses only local runtime assets', () => {
  const html = readFileSync(new URL('../xmlui/genova-sample-preview.html', `file://${__filename}`), 'utf8');
  assert.match(html, /Live status:[\s\S]*No live Genova event feed is connected yet/);
  assert.match(html, /Preview only:[\s\S]*fictional example data/);
  assert.match(html, /href="\.\.\/\?city=genova&amp;preview=sample"/);
  assert.doesNotMatch(html, /<(?:script|link)[^>]+(?:src|href)=["']https?:/i);
});

test('sample page includes month navigation, a calendar grid and category checkboxes', () => {
  const html = readFileSync(new URL('../xmlui/genova-sample-preview.html', `file://${__filename}`), 'utf8');
  assert.match(html, /id="previous-month"/);
  assert.match(html, /id="next-month"/);
  assert.match(html, /id="current-month"/);
  assert.match(html, /id="calendar-grid"/);
  assert.match(html, /id="category-filter-options"/);
  assert.match(readFileSync(new URL('../xmlui/sample-preview.js', `file://${__filename}`), 'utf8'), /buildCategoryFilters\(document, categoryFilterContainer/);
});

test('fixture validation requires source attribution and safe example links', () => {
  const api = requirePreview();
  assert.equal(api.validateSampleEvents([event()]).length, 1);
  assert.throws(
    () => api.validateSampleEvents([event({ sourceUrl: 'https://real-publisher.it/event' })]),
    /example\.org/,
  );
  assert.throws(
    () => api.validateSampleEvents([event({ sourceName: '' })]),
    /sourceName/,
  );
  assert.throws(
    () => api.validateSampleEvents([event({ tags: ['date-night-category'] })]),
    /invalid tags/,
  );
});

test('preview categories and labels come from the shared Genova taxonomy', () => {
  const taxonomy = JSON.parse(readFileSync(new URL('../genova-taxonomy.json', `file://${__filename}`), 'utf8'));
  const api = requirePreview();
  const keys = taxonomy.categories.map((category) => category.key);
  assert.deepEqual([...api.categoryKeys()].sort(), [...keys].sort());
  for (const category of taxonomy.categories) {
    assert.equal(api.CATEGORY_LABELS[category.key], category.label);
  }
  assert.equal(taxonomy.tags.find((tag) => tag.key === 'date-night').label, 'Date night');
  assert.equal(keys.includes('date-night'), false);
  const container = new FakeElement('div');
  api.buildCategoryFilters(new FakeDocument(), container);
  assert.equal(container.children.length, taxonomy.categories.length);
  assert.deepEqual(container.children.map((label) => label.children[1].textContent), taxonomy.categories.map((category) => category.label));
});

test('browser preview loads the shared taxonomy JSON before building filters', async () => {
  const source = readFileSync(new URL('../xmlui/sample-preview.js', `file://${__filename}`), 'utf8');
  const taxonomy = JSON.parse(readFileSync(new URL('../genova-taxonomy.json', `file://${__filename}`), 'utf8'));
  const browserWindow = {};
  vm.runInNewContext(source, { window: browserWindow, URL, Set, Object, Array, Promise, Intl, Date });
  let requestedPath = '';

  await browserWindow.GenovaSamplePreview.loadTaxonomy(async (path) => {
    requestedPath = path;
    return { ok: true, json: async () => taxonomy };
  });

  assert.equal(requestedPath, '../genova-taxonomy.json');
  assert.deepEqual([...browserWindow.GenovaSamplePreview.categoryKeys()], taxonomy.categories.map((category) => category.key));
});

test('sample fixture includes all categories and retains multi-category events', () => {
  const taxonomy = JSON.parse(readFileSync(new URL('../genova-taxonomy.json', `file://${__filename}`), 'utf8'));
  const events = JSON.parse(readFileSync(new URL('../xmlui/sample-events.json', `file://${__filename}`), 'utf8'));
  const eventCategories = new Set(events.flatMap((item) => item.categories || [item.category]));
  assert.deepEqual([...eventCategories].sort(), taxonomy.categories.map((category) => category.key).sort());
  assert.ok(events.some((item) => (item.categories || []).length > 1));
  assert.ok(events.some((item) => item.tags.includes('date-night')));
});

test('time filters use Europe/Rome calendar dates and retain unknown times as unknown', () => {
  const api = requirePreview();
  const now = new Date('2026-09-29T07:00:00.000Z');
  const events = [
    event({ id: 'weekday', daysFromToday: 1, startTime: null }),
    event({ id: 'saturday', daysFromToday: 4, category: 'art-exhibitions' }),
    event({ id: 'outside-window', daysFromToday: 10 }),
    event({ id: 'next-weekend', daysFromToday: 11 }),
  ];

  const weekend = api.filterSampleEvents(events, {
    category: 'all',
    dateWindow: 'weekend',
    now,
  });
  assert.deepEqual(weekend.map((item) => item.id), ['saturday']);
  assert.equal(weekend[0].date, '2026-10-03');

  const artThisWeek = api.filterSampleEvents(events, {
    category: 'art-exhibitions',
    dateWindow: 'week',
    now,
  });
  assert.deepEqual(artThisWeek.map((item) => item.id), ['saturday']);
  assert.equal(api.filterSampleEvents(events, { dateWindow: 'week', now })[0].startTime, null);
});

test('fixture loader fails closed when sample data cannot be fetched', async () => {
  const api = requirePreview();
  await assert.rejects(
    api.loadSampleEvents(async () => ({ ok: false, status: 404 })),
    /sample events/i,
  );
});

test('event renderer shows source, category and unknown time without inventing a time', () => {
  const api = requirePreview();
  const list = new FakeElement('div');
  const status = new FakeElement('p');
  const now = new Date('2026-09-29T07:00:00.000Z');
  const visible = api.renderSampleEvents(new FakeDocument(), list, status, [
    event({ id: 'art-exhibitions', category: 'art-exhibitions', startTime: null }),
    event({ id: 'music', category: 'music' }),
  ], { category: 'art-exhibitions', dateWindow: 'all', now });

  assert.equal(visible.length, 1);
  assert.equal(status.textContent, '1 sample event');
  assert.equal(list.children.length, 1);
  assert.match(list.textContent, /Time not listed/);
  assert.match(list.textContent, /Art & exhibitions/);
  assert.match(list.textContent, /Date night/);
  const source = list.children[0].children[4];
  assert.equal(source.href, 'https://example.org/events/jazz');
  assert.equal(source.rel, 'noopener noreferrer');
});

test('month calendar starts weeks on Monday and includes dates from adjacent months', () => {
  const api = requirePreview();
  const cells = api.calendarMonthCells(new Date('2026-09-29T07:00:00.000Z'));

  assert.equal(cells.length, 35);
  assert.deepEqual(cells[0], { date: '2026-08-31', dayNumber: 31, inMonth: false });
  assert.deepEqual(cells[1], { date: '2026-09-01', dayNumber: 1, inMonth: true });
  assert.deepEqual(cells.at(-1), { date: '2026-10-04', dayNumber: 4, inMonth: false });
  assert.equal(api.calendarMonthInfo(new Date('2026-12-15T12:00:00.000Z'), 1).key, '2027-01');
});

test('calendar filters include multi-category events when any selected category matches', () => {
  const api = requirePreview();
  const events = [
    event({ id: 'mixed', category: 'music', categories: ['music', 'art-exhibitions'], daysFromToday: 4 }),
    event({ id: 'sports', category: 'sports', categories: ['sports'], daysFromToday: 4 }),
  ];
  const visible = api.filterCalendarEvents(events, {
    selectedCategories: ['art-exhibitions'],
    monthOffset: 0,
    now: new Date('2026-09-29T07:00:00.000Z'),
  });

  assert.deepEqual(visible.map((item) => item.id), ['mixed']);
  assert.equal(visible[0].date, '2026-10-03');
});

test('calendar displays three events and expands all remaining events on a dense day', () => {
  const api = requirePreview();
  const events = Array.from({ length: 15 }, (_, index) => event({
    id: `dense-${index + 1}`,
    title: `Example event ${index + 1}`,
    daysFromToday: 4,
    startTime: `19:${String(index).padStart(2, '0')}`,
    categories: ['music'],
  }));
  const grid = new FakeElement('div');
  const status = new FakeElement('p');
  const now = new Date('2026-09-29T07:00:00.000Z');

  const visible = api.renderCalendar(new FakeDocument(), grid, status, events, {
    now,
    monthOffset: 0,
    selectedCategories: ['music'],
  });

  const day = grid.children.find((cell) => cell.dataset.date === '2026-10-03');
  const more = findElement(day, 'details');
  assert.equal(visible.length, 15);
  assert.equal(status.textContent, '15 sample events');
  assert.ok(day, 'the calendar should render the event date');
  assert.equal(day.children[1].children.length, 3);
  assert.equal(more.children[0].textContent, '+12 more');
  assert.equal(more.children[1].children.length, 12);
});

test('calendar keeps source attribution visible on the three compact event rows', () => {
  const api = requirePreview();
  const grid = new FakeElement('ol');
  const status = new FakeElement('p');
  const css = readFileSync(new URL('../xmlui/sample-preview.css', `file://${__filename}`), 'utf8');
  api.renderCalendar(new FakeDocument(), grid, status, [event()], {
    now: new Date('2026-09-29T07:00:00.000Z'),
  });

  const day = grid.children.find((cell) => cell.dataset.date === '2026-10-03');
  assert.match(day.textContent, /Example source: Example local publisher/);
  assert.doesNotMatch(css, /\.calendar-day\s*>\s*\.calendar-day-events\s+\.calendar-event-source\s*,?\s*\n?\s*\.calendar-day\s*>\s*\.calendar-day-events\s+\.calendar-event-categories\s*\{\s*display:\s*none;/);
});

test('empty calendar dates display a clear no-events message', () => {
  const api = requirePreview();
  const grid = new FakeElement('ol');
  const status = new FakeElement('p');
  api.renderCalendar(new FakeDocument(), grid, status, [event()], {
    now: new Date('2026-09-29T07:00:00.000Z'),
  });

  const emptyDay = grid.children.find((cell) => cell.dataset.date === '2026-10-04');
  assert.match(emptyDay.className, /calendar-day-empty/);
  assert.match(emptyDay.textContent, /No events listed/);
});

test('calendar clearly reports when active filters match no sample events', () => {
  const api = requirePreview();
  const grid = new FakeElement('ol');
  const status = new FakeElement('p');
  api.renderCalendar(new FakeDocument(), grid, status, [event({ category: 'music', daysFromToday: 4 })], {
    now: new Date('2026-09-29T07:00:00.000Z'),
    selectedCategories: ['art-exhibitions'],
  });

  assert.equal(status.textContent, 'No sample events match these filters.');
});

test('sample fixture contains at least fifteen clearly fictional events on one date', () => {
  const events = JSON.parse(readFileSync(new URL('../xmlui/sample-events.json', `file://${__filename}`), 'utf8'));
  const counts = new Map();
  for (const item of events) counts.set(item.daysFromToday, (counts.get(item.daysFromToday) || 0) + 1);
  assert.ok(Math.max(...counts.values()) >= 15);
  assert.ok(events.every((item) => item.sourceUrl.startsWith('https://example.org/')));
});

function findElement(root, tagName) {
  return findElements(root, tagName)[0];
}

function findElements(root, tagName) {
  if (!root) return [];
  return [
    ...(root.tagName === tagName ? [root] : []),
    ...root.children.flatMap((child) => findElements(child, tagName)),
  ];
}
