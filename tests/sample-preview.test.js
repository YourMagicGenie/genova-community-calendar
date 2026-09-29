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
}

test('sample preview route only matches Genova sample mode', () => {
  const api = requirePreview();
  assert.equal(api.matchesSampleRoute('https://calendar.example/?city=genova&preview=sample'), true);
  assert.equal(api.matchesSampleRoute('https://calendar.example/?city=asheville&preview=sample'), false);
  assert.equal(api.matchesSampleRoute('https://calendar.example/?city=genova'), false);
});

test('site entry sends only the Genova sample route to the isolated preview page', () => {
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

  assert.equal(destination('?city=genova&preview=sample'), 'xmlui/genova-sample-preview.html?city=genova&preview=sample#events');
  assert.equal(destination('?city=asheville'), 'xmlui/index.html?city=asheville#events');
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
});

test('time filters use Europe/Rome calendar dates and retain unknown times as unknown', () => {
  const api = requirePreview();
  const now = new Date('2026-09-29T07:00:00.000Z');
  const events = [
    event({ id: 'weekday', daysFromToday: 1, startTime: null }),
    event({ id: 'saturday', daysFromToday: 4, category: 'art' }),
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
    category: 'art',
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
    event({ id: 'art', category: 'art', startTime: null }),
    event({ id: 'music', category: 'music' }),
  ], { category: 'art', dateWindow: 'all', now });

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
