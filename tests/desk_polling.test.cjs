// Dependency-free controller tests: fake DOM, timers and network, no browser writes.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../nbn/desk_assets/desk.js'), 'utf8');

function setup() {
  let selected = '', reject = false, calls = [], timers = new Map(), serial = 0;
  const el = () => ({textContent: '', disabled: false, attrs: {}, handlers: {},
    addEventListener(k, fn) { this.handlers[k] = fn; },
    setAttribute(k, v) { this.attrs[k] = v; },
    classList: {add() {}, remove() {}}});
  const content = {...el(), dataset: {observed: '1788680000'}, innerHTML: 'initial',
    contains: node => node === 'focused', querySelectorAll: () => [{id: 'detail'}]};
  const elements = {content, connection: el(), pause: el(), refresh: el(), detail: {open: false}};
  const document = {hidden: false, activeElement: null, body: {dataset: {view: 'runs'}},
    getElementById: id => elements[id], querySelector: () => ({defaultValue: '2026-09-06'}),
    handlers: {}, addEventListener(k, fn) { this.handlers[k] = fn; }};
  const ctx = {document, URL, AbortController, Date, Number, String,
    window: {location: {origin: 'https://example.test', search: '?k=test&run=saved-run'}, getSelection: () => selected},
    setTimeout(fn, delay) { const id = ++serial; timers.set(id, {fn, delay}); return id; },
    clearTimeout(id) { timers.delete(id); },
    async fetch(url, opts) { calls.push([url, opts]); if (reject) throw new Error('offline');
      return {ok: true, json: async () => ({html: 'updated', generated_at: 1788680020, worker: 'healthy'})}; }
  };
  vm.runInNewContext(source, ctx);
  return {ctx, elements, timers, calls, selection(v) { selected = v; }, fail(v) { reject = v; }};
}

(async () => {
  const s = setup();
  assert.equal([...s.timers.values()].filter(t => t.delay === 15000).length, 1);
  await s.elements.refresh.handlers.click();
  // Event callback intentionally returns void; settle its async continuation.
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.elements.content.innerHTML, 'updated');
  assert.equal(s.elements.detail.open, true);
  assert.equal(s.calls[0][0].searchParams.get('run'), 'saved-run');
  assert.equal(s.calls[0][0].searchParams.get('d'), '2026-09-06');
  assert.equal(s.calls[0][1].referrerPolicy, 'no-referrer');
  s.elements.pause.handlers.click();
  assert.equal(s.elements.pause.attrs['aria-pressed'], 'true');
  assert.equal([...s.timers.values()].filter(t => t.delay === 15000).length, 0);
  s.fail(true); s.elements.refresh.handlers.click();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.elements.content.innerHTML, 'updated');
  assert.match(s.elements.connection.textContent, /may be stale/);
  s.fail(false); s.elements.pause.handlers.click();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.elements.pause.attrs['aria-pressed'], 'false');
  s.ctx.document.hidden = true; s.ctx.document.handlers.visibilitychange();
  assert.equal([...s.timers.values()].filter(t => t.delay === 15000).length, 0);
  const count = s.calls.length;
  s.ctx.document.hidden = false; s.ctx.document.activeElement = 'focused';
  s.ctx.document.handlers.visibilitychange();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.calls.length, count);
  assert.match(s.elements.connection.textContent, /waiting while reading/);
  console.log('Desk polling: refresh, run/day preservation, disclosure state, pause/resume, hidden tab, error retention and reading guard passed.');
})().catch(err => { console.error(err); process.exitCode = 1; });
