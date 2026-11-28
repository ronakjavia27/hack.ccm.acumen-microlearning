import { $, $$, esc, debounce, theme, closeSheet, toast } from './ui.js';
import { get } from './api.js';
import { store, load, pushAll, renderPush } from './store.js';
import { overview } from './views/overview.js';
import { summaries, pearls, theory, flashcards } from './views/content.js';
import { mcqs } from './views/mcqs.js';
import { accounts, backups, audit, maintenance } from './views/system.js';

const VIEWS = {
  overview: { label: 'Overview', ic: '◉', group: 'Home', fn: (el) => overview(el, go) },
  mcqs: { label: 'MCQ Review', ic: '✓', group: 'Content', fn: mcqs, badge: true },
  summaries: { label: 'Summaries', ic: '❒', group: 'Content', fn: summaries },
  pearls: { label: 'Pearls', ic: '◆', group: 'Content', fn: pearls },
  flashcards: { label: 'Flashcards', ic: '▤', group: 'Content', fn: flashcards },
  theory: { label: 'Theory', ic: '☰', group: 'Content', fn: theory },
  accounts: { label: 'Accounts', ic: '☺', group: 'System', fn: accounts },
  backups: { label: 'Backups', ic: '⇩', group: 'System', fn: backups },
  audit: { label: 'Audit log', ic: '≡', group: 'System', fn: audit },
  maintenance: { label: 'Maintenance', ic: '⚙', group: 'System', fn: maintenance },
};
const TABS = [['overview', 'Home'], ['mcqs', 'Review'], ['content', 'Content'], ['more', 'More']];
const CONTENT = ['summaries', 'pearls', 'flashcards', 'theory'];

export function go(name) { location.hash = '#/' + name; }

function renderRail() {
  let html = '', group = '';
  for (const [k, v] of Object.entries(VIEWS)) {
    if (v.group !== group) { group = v.group; html += `<h4>${group}</h4>`; }
    html += `<button class="nav" data-nav="${k}"><span class="ic">${v.ic}</span>${v.label}${v.badge ? '<span class="count">·</span>' : ''}</button>`;
  }
  $('#rail').innerHTML = html;
  $('#tabbar').innerHTML = TABS.map(([k, l]) => `<button data-tab="${k}"><span class="ic">${{ overview: '◉', mcqs: '✓', content: '❒', more: '⋯' }[k]}</span>${l}</button>`).join('');
}

function menuSheet(title, keys) {
  // Mobile sub-menu: reuses the view area instead of a sheet so back/forward works.
  const el = $('#view');
  el.innerHTML = `<div class="head"><div><h1>${esc(title)}</h1></div></div><div class="list">${keys.map(k => `<div class="li" data-go="${k}" style="grid-template-columns:28px 1fr"><span>${VIEWS[k].ic}</span><div class="t">${VIEWS[k].label}</div></div>`).join('')}</div>
    <div class="toolbar" style="margin-top:14px"><button class="btn" id="mtheme">Toggle theme</button><button class="btn" id="mpush">Push saved changes</button></div>`;
  el.onclick = (e) => { const g = e.target.closest('[data-go]'); if (g) go(g.dataset.go); if (e.target.id === 'mtheme') theme(); if (e.target.id === 'mpush') pushAll(); };
}

async function route() {
  closeSheet();
  const name = (location.hash.replace(/^#\//, '') || 'overview').split('?')[0];
  const el = $('#view');
  el.onclick = null;
  $$('#rail .nav').forEach(b => b.classList.toggle('active', b.dataset.nav === name));
  const tab = name === 'overview' ? 'overview' : name === 'mcqs' ? 'mcqs' : CONTENT.includes(name) || name === 'content' ? 'content' : 'more';
  $$('#tabbar button').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  window.scrollTo({ top: 0 });
  if (name === 'content') return menuSheet('Content', CONTENT);
  if (name === 'more') return menuSheet('More', ['accounts', 'backups', 'audit', 'maintenance']);
  const v = VIEWS[name] || VIEWS.overview;
  el.innerHTML = '';
  try { await v.fn(el); } catch (e) { el.innerHTML = `<div class="empty">Failed to load: ${esc(e.message)}</div>`; }
}

/* ---- global search across loaded + fetched kinds ---- */
async function search(q) {
  const box = $('#gresults');
  q = q.trim().toLowerCase();
  if (q.length < 2) { box.classList.add('hide'); return; }
  const [s, p, f, m] = await Promise.all(['summaries', 'pearls', 'flashcards', 'mcqs'].map(k => load(k).catch(() => [])));
  const hits = [];
  s.forEach(r => { if ([r.title, r.authors, r.doi].join(' ').toLowerCase().includes(q)) hits.push(['summaries', r.title, r.system]); });
  p.forEach(r => { if ([r.pearl, r.topic].join(' ').toLowerCase().includes(q)) hits.push(['pearls', r.pearl.slice(0, 90), r.system]); });
  f.forEach(r => { if ([r.title, r.specialty].join(' ').toLowerCase().includes(q)) hits.push(['flashcards', r.title, r.specialty]); });
  m.forEach(r => { if (r.stem.toLowerCase().includes(q)) hits.push(['mcqs', r.stem.slice(0, 90), r.system]); });
  box.innerHTML = hits.length ? hits.slice(0, 30).map(h => `<button data-go="${h[0]}"><b>${esc(h[1])}</b><div class="small muted">${h[0]} · ${esc(h[2] || '')}</div></button>`).join('') : '<button disabled>No matches</button>';
  box.classList.remove('hide');
}

document.addEventListener('click', (e) => {
  const nav = e.target.closest('[data-nav]'); if (nav) go(nav.dataset.nav);
  const tab = e.target.closest('[data-tab]'); if (tab) go(tab.dataset.tab);
  const g = e.target.closest('#gresults [data-go]'); if (g) { $('#gresults').classList.add('hide'); $('#gsearch').value = ''; go(g.dataset.go); }
  if (!e.target.closest('.search')) $('#gresults').classList.add('hide');
  if (e.target.closest('#themeBtn')) theme();
  if (e.target.closest('#pushBtn')) pushAll();
});
$('#gsearch').addEventListener('input', debounce(e => search(e.target.value), 200));
window.addEventListener('hashchange', route);

renderRail();
renderPush();
route();
get('/mcqs/stats').then(s => { const b = $('[data-nav="mcqs"] .count'); if (b) { b.textContent = s.by_status.draft; b.classList.toggle('alert', s.by_status.draft > 0); } }).catch(() => {});
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/console/sw.js', { scope: '/console/' }).catch(() => {});
