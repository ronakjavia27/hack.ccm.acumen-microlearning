// Summaries, Pearls, Theory, Flashcards — list + edit sheet.
import { $, $$, esc, trunc, pill, toast, openSheet, closeSheet, selectOptions, toolbar, contentEditor, collectContent } from '../ui.js';
import { get, put, post, del, enc } from '../api.js';
import { store, load, loadSubtopics, subtopicsFor, markDirty, pushAll, SYSTEMS, PEARL_TYPES } from '../store.js';
import { mountList, bulkStatus, bulkDelete } from '../list.js';

const statusOf = (r) => r.show_on_web === 'Yes' ? 'published' : r.show_on_web === 'No' ? 'hidden' : (r.validation_status || r.visibility || 'published');
const seg = (opts, cur) => `<div class="seg" data-seg>${opts.map(o => `<button type="button" data-v="${o}" class="${o === cur ? 'on' : ''}">${o}</button>`).join('')}</div>`;
const segVal = (root) => { const b = $('[data-seg] .on', root); return b ? b.dataset.v : null; };
document.addEventListener('click', e => {
  const b = e.target.closest('[data-seg] button');
  if (b) { $$('button', b.parentElement).forEach(x => x.classList.toggle('on', x === b)); }
});
const val = (root, id) => { const el = $('#' + id, root); return el ? el.value : undefined; };

function footer(extra = '') {
  return `<button class="btn" data-act="save">Save</button><button class="btn primary" data-act="savepush">Save &amp; push</button>${extra}<span class="spacer"></span><button class="btn bad" data-act="delete">Delete</button>`;
}

/** Wire sheet footer buttons: collect() -> fields, then save/push/delete. */
function wire(kind, id, collect, after, delMsg) {
  const foot = $('#sheetFoot');
  foot.onclick = async (e) => {
    const act = e.target.dataset.act;
    if (!act) return;
    try {
      if (act === 'delete') {
        if (!confirm(`Delete ${delMsg}? This cannot be undone.`)) return;
        const r = await del(`/${kind}/${enc(id)}`);
        if (!r.deleted) { toast('Delete failed — nothing changed.', true); return; }
        markDirty(kind, id, r.affected_paths);
        toast('Deleted.');
        closeSheet(); await after(true); return;
      }
      const fields = collect();
      let r = { updated: false };
      if (fields && Object.keys(fields).length) {
        r = await put(`/${kind}/${enc(id)}`, fields);
        if (r.updated) { markDirty(kind, id, r.affected_paths); toast('Saved.'); } else toast('No changes.');
      }
      if (kind === 'summaries' && (r.system_changed || r.subtopic_changed)) await cascade(id, r);
      if (act === 'savepush') await pushAll();
      closeSheet(); await after(true);
    } catch (err) { toast(err.message, true); }
  };
}

async function cascade(id, r) {
  try {
    const prev = await post(`/summaries/${enc(id)}/cascade-preview`, {});
    const n = prev.total_pearls || 0;
    if (!n) return;
    const o = r.old || {}, nw = r.new || {};
    if (confirm(`${n} linked pearl(s) share this paper.\nReclassify ${o.system || '?'}/${o.subtopic || '?'} → ${nw.system || '?'}/${nw.subtopic || '?'}?`)) {
      const row = (store.cache.summaries || []).find(s => String(s.id) === String(id)) || {};
      const res = await post('/update-pearls-bulk', { file_name: row.file_name, system: nw.system, subtopic: nw.subtopic });
      markDirty('pearls', 'cascade', res.affected_paths);
      toast('Pearls reclassified.');
    }
  } catch (_) { /* no cascade possible */ }
}

function wireSystemSubtopic(root) {
  const s = $('#f_system', root), t = $('#f_subtopic', root);
  if (s && t) s.addEventListener('change', () => { t.innerHTML = selectOptions(subtopicsFor(s.value), '', '—'); });
}

/* ================= Summaries ================= */
export function summaries(el) {
  loadSubtopics();
  mountList(el, {
    kind: 'summaries', title: 'Summaries', sub: 'Paper summaries shown on the portal',
    grid: '1fr 230px 170px 100px', headers: ['Title', 'System · status', 'Subtopic', 'Added'],
    main: r => `<div class="t">${esc(r.title)}</div><div class="s">${esc(trunc(r.authors, 70))}</div>`,
    meta: r => `<span class="tag">${esc(r.system || '—')}</span>${pill(statusOf(r))}`,
    extras: r => [`<span class="s">${esc(r.subtopic || '')}</span>`, `<span class="s">${esc((r.date_added || '').split(' ')[0])}</span>`],
    search: r => [r.title, r.authors, r.doi, r.file_name, r.id].join(' '),
    filters: [{ key: 'system', label: 'All systems', get: r => r.system }, { key: 'status', label: 'All statuses', get: statusOf, values: ['published', 'hidden'] }],
    bulk: [
      { label: 'Show', fn: ids => bulkStatus('summaries', ids, 'published') },
      { label: 'Hide', fn: ids => bulkStatus('summaries', ids, 'hidden') },
      { label: 'Delete', cls: 'bad', fn: ids => bulkDelete('summaries', ids, 'summaries and their linked pearls') },
    ],
    open: (r, reload) => openSummary(r, reload),
  });
}
async function openSummary(r, reload) {
  const sub = r.subtopic;
  const sh = openSheet({ title: r.title, body: '<p class="muted">Loading…</p>' });
  let content = {};
  try { content = await get(`/summaries/${enc(r.id)}/content`); } catch (_) {}
  const hasC = content && Object.keys(content).length;
  sh.body.innerHTML = `${seg(['published', 'hidden'], statusOf(r))}
    <label class="f"><span>Title</span><input type="text" id="f_title" value="${esc(r.title)}"></label>
    <div class="row2"><label class="f"><span>Authors</span><input type="text" id="f_authors" value="${esc(r.authors || '')}"></label>
    <label class="f"><span>Journal</span><input type="text" id="f_journal" value="${esc(r.journal || '')}"></label></div>
    <div class="row2"><label class="f"><span>System</span><select id="f_system">${selectOptions(SYSTEMS, r.system)}</select></label>
    <label class="f"><span>Subtopic</span><select id="f_subtopic">${selectOptions(subtopicsFor(r.system), sub, '—')}</select></label></div>
    <div class="row2"><label class="f"><span>DOI</span><input type="text" id="f_doi" value="${esc(r.doi || '')}"></label>
    <label class="f"><span>Type</span><select id="f_type">${selectOptions(['Trial', 'Review', 'Guideline', 'Meta-analysis', 'Observational', 'Other'], r.type)}</select></label></div>
    <p class="small muted">File: <code>${esc(r.file_name || '')}</code></p>
    ${hasC ? `<div class="section-title">Content sections</div><div class="ce" id="ceRoot">${contentEditor(content)}</div>` : '<p class="muted small">No content file found for this summary.</p>'}`;
  sh.foot.innerHTML = footer();
  wireSystemSubtopic(sh.body);
  wire('summaries', r.id, () => {
    const f = {};
    for (const k of ['title', 'authors', 'journal', 'system', 'subtopic', 'doi', 'type']) { const v = val(sh.body, 'f_' + k); if (v !== undefined && v !== '') f[k] = v; }
    f.show_on_web = segVal(sh.body) === 'published' ? 'Yes' : 'No';
    if (hasC) { const edited = collectContent($('#ceRoot', sh.body), content); if (JSON.stringify(edited) !== JSON.stringify(content)) f._content_edits = edited; }
    return f;
  }, reload, 'this summary and ALL its linked pearls');
}

/* ================= Pearls ================= */
export function pearls(el) {
  loadSubtopics();
  mountList(el, {
    kind: 'pearls', title: 'Pearls', sub: 'Clinical pearls extracted from papers',
    grid: '1fr 230px 110px', headers: ['Pearl', 'System · status', 'Type'],
    main: r => `<div class="t" style="font-weight:600">${esc(trunc(r.pearl, 170))}</div><div class="s">${esc(trunc(r.source_paper, 80))}</div>`,
    meta: r => `<span class="tag">${esc(r.system || '—')}</span>${pill(statusOf(r))}`,
    extras: r => [`<span class="s">${esc(r.type || '')}</span>`],
    search: r => [r.pearl, r.doi, r.topic, r.subtopic, r.id, r.source_paper].join(' '),
    filters: [{ key: 'system', label: 'All systems', get: r => r.system }, { key: 'type', label: 'All types', get: r => r.type },
      { key: 'status', label: 'All statuses', get: statusOf, values: ['published', 'hidden', 'removed'] }],
    bulk: [
      { label: 'Show', fn: ids => bulkStatus('pearls', ids, 'published') },
      { label: 'Hide', fn: ids => bulkStatus('pearls', ids, 'hidden') },
      { label: 'Delete', cls: 'bad', fn: ids => bulkDelete('pearls', ids, 'pearls') },
    ],
    open: (r, reload) => {
      const sh = openSheet({ title: 'Pearl #' + r.id, body: `${seg(['published', 'hidden', 'removed'], statusOf(r))}
        <label class="f"><span>Pearl</span>${toolbar('f_pearl')}<textarea id="f_pearl" rows="6">${esc(r.pearl)}</textarea></label>
        <div class="row2"><label class="f"><span>System</span><select id="f_system">${selectOptions(SYSTEMS, r.system)}</select></label>
        <label class="f"><span>Type</span><select id="f_type">${selectOptions(PEARL_TYPES, r.type)}</select></label></div>
        <label class="f"><span>Subtopic</span><select id="f_subtopic">${selectOptions(subtopicsFor(r.system), r.subtopic, '—')}</select></label>
        <label class="f"><span>Remarks</span><textarea id="f_remarks" rows="3">${esc(r.remarks || '')}</textarea></label>
        <p class="small muted">Source: <em>${esc(r.source_paper || '')}</em> · DOI <code>${esc(r.doi || '—')}</code></p>`, footer: footer() });
      wireSystemSubtopic(sh.body);
      wire('pearls', r.id, () => {
        const f = {};
        for (const k of ['pearl', 'system', 'type', 'subtopic', 'remarks']) { const v = val(sh.body, 'f_' + k); if (v !== undefined && v !== '') f[k] = v; }
        f.visibility = segVal(sh.body);
        return f;
      }, reload, 'this pearl');
    },
  });
}

/* ================= Theory ================= */
export function theory(el) {
  mountList(el, {
    kind: 'theory', title: 'Theory', sub: 'Validated theory documents',
    grid: '1fr 260px', headers: ['Title', 'Specialty · status'],
    main: r => `<div class="t">${esc(r.title)}</div><div class="s">${r.sections_count || 0} sections · ${r.subtopic_count || 0} subtopics</div>`,
    meta: r => `<span class="tag">${esc(r.specialty || '—')}</span>${pill(statusOf(r))}`,
    search: r => [r.title, r.id, r.specialty].join(' '),
    filters: [{ key: 'specialty', label: 'All specialties', get: r => r.specialty }],
    open: (r, reload) => {
      const raw = r._raw || {};
      const cur = r.validation_status || 'needs_review';
      const sh = openSheet({ title: r.title, body: `${seg(['needs_review', 'reviewed', 'approved'], cur)}
        <label class="f"><span>Title</span><input type="text" id="f_title" value="${esc(r.title)}"></label>
        <label class="f"><span>Specialty</span><input type="text" id="f_specialty" value="${esc(r.specialty || '')}"></label>
        <div class="section-title">Content fields</div><div id="ceRoot">${contentEditor(raw)}</div>`, footer: footer() });
      wire('theory', r.id, () => {
        const edits = collectContent($('#ceRoot', sh.body), raw);
        edits.validation = Object.assign({}, edits.validation, { status: segVal(sh.body) });
        const f = { _raw: edits };
        const t = val(sh.body, 'f_title'); if (t) f.title = t;
        return f;
      }, reload, 'this theory document');
    },
  });
}

/* ================= Flashcards (decks + card reader) ================= */
export function flashcards(el) {
  const ctl = mountList(el, {
    kind: 'flashcards', title: 'Flashcards', sub: 'Unified store — decks by system / subtopic',
    grid: '1fr 260px', headers: ['Deck', 'Specialty · status'],
    main: r => `<div class="t">${esc(r.title)}</div><div class="s">${r.card_count || 0} cards · ${r.preserved_count || 0} preserved · ${r.discarded_count || 0} discarded · ${r.pending_count || 0} pending</div>`,
    meta: r => `<span class="tag">${esc(r.specialty || '—')}</span>${pill(r.status || 'pending')}`,
    search: r => [r.title, r.id, r.specialty].join(' '),
    filters: [{ key: 'specialty', label: 'All specialties', get: r => r.specialty }, { key: 'status', label: 'All statuses', get: r => r.status, values: ['pending', 'preserved', 'discarded'] }],
    open: (r, reload) => openDeck(r, reload),
  });
}

async function openDeck(row, reload) {
  const sh = openSheet({ title: row.title, body: '<p class="muted">Loading…</p>' });
  let deck;
  try { deck = await get('/flashcards/' + enc(row.id)); } catch (e) { sh.body.innerHTML = `<p style="color:var(--bad)">${esc(e.message)}</p>`; return; }
  let idx = 0, editing = false, changed = false;
  const cards = deck.cards || [];

  function draw() {
    if (!cards.length) { sh.body.innerHTML = '<div class="empty">This deck has no cards.</div>'; return; }
    const c = cards[idx];
    const pres = cards.filter(x => x.status === 'preserved').length, disc = cards.filter(x => x.status === 'discarded').length;
    sh.body.innerHTML = `
      <div class="meta" style="margin-bottom:8px"><span class="tag">${esc(deck.specialty || '')}</span>${pill(c.status || 'pending')}<span class="muted small">${idx + 1} / ${cards.length} · ${pres} kept · ${disc} dropped</span></div>
      <div class="progress"><i style="width:${((idx + 1) / cards.length) * 100}%"></i></div>
      <div class="muted small" style="margin-bottom:6px">${esc(c.subtopic || '')}</div>
      ${c.front ? `<div class="fc-face fc-q">${esc(c.front)}</div>` : ''}
      <div class="fc-face">${esc(c.back || c.content || '')}</div>
      <div class="row2" style="margin-bottom:10px"><button class="btn ok" data-a="preserve">Preserve</button><button class="btn bad" data-a="discard">Discard</button></div>
      <div class="row2" style="margin-bottom:10px"><button class="btn" data-a="prev" ${idx === 0 ? 'disabled' : ''}>‹ Prev</button><button class="btn" data-a="next" ${idx >= cards.length - 1 ? 'disabled' : ''}>Next ›</button></div>
      <button class="btn" data-a="edit" style="width:100%">Edit with AI…</button>
      <div id="fcEdit" class="${editing ? '' : 'hide'}" style="margin-top:10px"><textarea id="fcEditInput" rows="3" placeholder="Describe the change (e.g. add the dose, shorten the question)…"></textarea>
        <div class="row2" style="margin-top:8px"><button class="btn primary" data-a="submit">Regenerate card</button><button class="btn" data-a="cancel">Cancel</button></div></div>
      <hr style="border:0;border-top:1px solid var(--line);margin:18px 0">
      <label class="f"><span>Deck title (subtopic)</span><input type="text" id="f_title" value="${esc(deck.title)}"></label>
      <label class="f"><span>Specialty (reclassify moves all cards)</span><select id="f_specialty">${selectOptions(SYSTEMS, deck.specialty)}</select></label>`;
  }
  draw();

  async function cardAction(action) {
    const c = cards[idx];
    try {
      const r = await put('/flashcards/' + enc(deck.id), { action, card_id: c.id });
      c.status = action === 'preserve' ? 'preserved' : 'discarded';
      if (r.affected_paths) markDirty('flashcards', deck.id, r.affected_paths);
      changed = true;
      if (idx < cards.length - 1) idx++;
      draw();
    } catch (e) { toast(e.message, true); }
  }

  sh.body.onclick = async (e) => {
    const a = e.target.dataset.a;
    if (!a) return;
    if (a === 'preserve' || a === 'discard') return cardAction(a);
    if (a === 'prev') { idx = Math.max(0, idx - 1); editing = false; draw(); }
    else if (a === 'next') { idx = Math.min(cards.length - 1, idx + 1); editing = false; draw(); }
    else if (a === 'edit') { editing = true; draw(); $('#fcEditInput', sh.body).focus(); }
    else if (a === 'cancel') { editing = false; draw(); }
    else if (a === 'submit') {
      const comment = $('#fcEditInput', sh.body).value.trim();
      if (!comment) { toast('Describe the change first.', true); return; }
      e.target.disabled = true; e.target.textContent = 'Working…';
      try {
        const r = await post(`/flashcards/${enc(deck.id)}/regenerate-card`, { card_id: cards[idx].id, edit_comment: comment }, 120000);
        if (r.updated && r.card) {
          Object.assign(cards[idx], { subtopic: r.card.subtopic, front: r.card.front || '', back: r.card.back || '' });
          if (r.affected_paths) markDirty('flashcards', deck.id, r.affected_paths);
          changed = true; editing = false; toast('Card updated.'); draw();
        } else { toast('No revision returned.', true); e.target.disabled = false; e.target.textContent = 'Regenerate card'; }
      } catch (err) { toast(err.message, true); e.target.disabled = false; e.target.textContent = 'Regenerate card'; }
    }
  };
  sh.foot.innerHTML = `<button class="btn" data-act="save">Save title / specialty</button><button class="btn primary" data-act="savepush">Save &amp; push</button><span class="spacer"></span><button class="btn bad" data-act="delete">Delete deck</button>`;
  wire('flashcards', deck.id, () => {
    const f = {}, t = val(sh.body, 'f_title'), s = val(sh.body, 'f_specialty');
    if (t && t !== deck.title) f.title = t;
    if (s && s !== deck.specialty) f.specialty = s;
    return f;
  }, async () => { await load('flashcards', true); reload && reload(true); }, 'this deck and all its cards (authored markdown is kept)');
  // Reflect card-level changes in the list when the sheet is dismissed.
  document.getElementById('scrim').addEventListener('click', () => { if (changed) reload && reload(true); }, { once: true });
}
