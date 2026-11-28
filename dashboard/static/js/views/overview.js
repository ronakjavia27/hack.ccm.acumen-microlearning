import { $, esc, pill } from '../ui.js';
import { get } from '../api.js';
import { store, load, pushAll } from '../store.js';

export async function overview(el, go) {
  el.innerHTML = `<div class="head"><div><h1>Overview</h1><p id="osub">Loading…</p></div><div class="spacer"></div></div>
    <div class="grid" id="ostats"></div>
    <div class="section-title">Needs attention</div><div class="grid" id="otodo"></div>
    <div class="section-title">Recent activity</div><div class="list" id="oact"><div class="empty">Loading…</div></div>`;
  const safe = (p) => p.catch(() => null);
  const [s, p, t, f, m, a] = await Promise.all([safe(load('summaries')), safe(load('pearls')), safe(load('theory')), safe(load('flashcards')),
    safe(get('/mcqs/stats')), safe(get('/audit?n=8'))]);
  const n = (x) => (x ? x.length : '—');
  const cards = (f || []).reduce((acc, d) => acc + (d.card_count || 0), 0);
  const pub = (s || []).filter(x => x.show_on_web === 'Yes').length;
  $('#osub', el).textContent = `${n(s)} summaries · ${n(p)} pearls · ${cards} flashcards · ${m ? m.total : '—'} MCQs`;
  const tile = (label, v, view, cls = '') => `<button class="stat ${cls}" data-go="${view}"><b>${v}</b><span>${label}</span></button>`;
  $('#ostats', el).innerHTML = [
    tile('Summaries', n(s), 'summaries'), tile('Published', pub, 'summaries', 'ok'), tile('Pearls', n(p), 'pearls'),
    tile('Theory docs', n(t), 'theory'), tile('Flashcard decks', n(f), 'flashcards'), tile('Flashcards', cards, 'flashcards'),
    tile('MCQs approved', m ? m.by_status.approved : '—', 'mcqs', 'ok'),
  ].join('');
  const draft = m ? m.by_status.draft : 0;
  const pendingCards = (f || []).reduce((acc, d) => acc + (d.pending_count || 0), 0);
  const failed = (s || []).filter(x => x.md_generated !== 'Yes' || (x.parsing_notes && x.parsing_notes !== 'Success')).length;
  $('#otodo', el).innerHTML = [
    tile('MCQ drafts to review', draft, 'mcqs', draft ? 'warn' : ''),
    tile('Flashcards pending', pendingCards, 'flashcards', pendingCards ? 'warn' : ''),
    tile('Summaries needing attention', failed, 'maintenance', failed ? 'bad' : ''),
    `<button class="stat ${store.dirty.size ? 'warn' : ''}" data-push="1"><b>${store.dirty.size}</b><span>Saved edits not pushed${store.dirty.size ? ' — tap to push' : ''}</span></button>`,
  ].join('');
  $('#oact', el).innerHTML = a && a.length ? a.map(e => `<div class="li" style="grid-template-columns:150px 1fr"><span class="s">${esc(e.ts)}</span><span><b>${esc(e.kind)}</b> ${esc(e.action)} <span class="s">${esc(String(e.id).slice(0, 40))}</span></span></div>`).join('') : '<div class="empty">No recent edits.</div>';
  el.onclick = (e) => {
    const g = e.target.closest('[data-go]'); if (g) go(g.dataset.go);
    if (e.target.closest('[data-push]')) pushAll();
  };
}
