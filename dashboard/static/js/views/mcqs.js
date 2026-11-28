// MCQ review studio: one-at-a-time triage queue + browse list.
import { $, $$, esc, pill, toast, openSheet, closeSheet, selectOptions } from '../ui.js';
import { get, put, post, del, enc } from '../api.js';
import { store, load, markDirty, SYSTEMS, pushAll } from '../store.js';

const DIFFS = ['easy', 'medium', 'hard'];

export function mcqs(el) {
  const st = { rows: [], queue: [], i: 0, status: 'draft', system: '', difficulty: '', q: '', mode: 'review', stats: null, history: [] };

  el.innerHTML = `
    <div class="head"><div><h1>MCQ Review</h1><p id="msub">Approve, edit or reject generated questions</p></div><div class="spacer"></div>
      <button class="btn" id="mgen">Generate more</button></div>
    <div class="seg" id="mmode"><button data-m="review" class="on">Review queue</button><button data-m="browse">Browse all</button></div>
    <div class="toolbar">
      <select id="mstatus"><option value="draft">Drafts</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="">All statuses</option></select>
      <button class="btn filters-toggle" id="mft">Filters</button>
      <div class="filters" id="mfilters">
        <select id="msystem"><option value="">All systems</option></select>
        <select id="mdiff"><option value="">Any difficulty</option>${DIFFS.map(d => `<option>${d}</option>`).join('')}</select>
        <input type="search" id="mq" placeholder="Search stem / tag…" class="grow">
      </div>
    </div>
    <div id="mbody"></div>`;

  async function refresh(force) {
    try {
      st.rows = await load('mcqs', !!force);
      const systems = [...new Set(st.rows.map(r => r.system).filter(Boolean))].sort();
      $('#msystem', el).innerHTML = '<option value="">All systems</option>' + systems.map(s => `<option ${s === st.system ? 'selected' : ''}>${esc(s)}</option>`).join('');
      applyFilters(true);
    } catch (e) { $('#mbody', el).innerHTML = `<div class="empty">Load failed: ${esc(e.message)}</div>`; }
  }

  function applyFilters(resetPos) {
    const q = st.q.toLowerCase();
    st.queue = st.rows.filter(r => (!st.status || r.status === st.status) && (!st.system || r.system === st.system) &&
      (!st.difficulty || r.difficulty === st.difficulty) && (!q || (r.stem + ' ' + r.tags.join(' ') + ' ' + r.subtopic).toLowerCase().includes(q)));
    if (resetPos) st.i = 0;
    if (st.i >= st.queue.length) st.i = Math.max(0, st.queue.length - 1);
    draw();
  }

  function counts() {
    const c = { draft: 0, approved: 0, rejected: 0 };
    st.rows.forEach(r => { c[r.status] = (c[r.status] || 0) + 1; });
    return c;
  }

  function draw() {
    const c = counts();
    $('#msub', el).textContent = `${c.draft} to review · ${c.approved} approved · ${c.rejected} rejected`;
    const nb = document.querySelector('[data-nav="mcqs"] .count'); if (nb) { nb.textContent = c.draft; nb.classList.toggle('alert', c.draft > 0); }
    st.mode === 'review' ? drawReview() : drawBrowse();
  }

  /* ---------- review queue ---------- */
  function qHtml(q) {
    return `<div class="meta"><span class="tag">${esc(q.system)}</span><span class="small muted">${esc(q.subtopic)}</span>${pill(q.status)}${pill(q.difficulty, 'info')}</div>
      <div class="stem">${esc(q.stem)}</div>
      ${q.options.map(o => `<div class="opt ${o.key === q.answer ? 'correct' : ''}"><span class="k">${esc(o.key)}</span><span>${esc(o.text)}</span></div>`).join('')}
      <div class="expl"><b>Explanation.</b> ${esc(q.explanation)}</div>
      <div class="small muted" style="margin-top:10px">${q.source_kind ? `Source: ${esc(q.source_kind)} — ${esc(q.source_title || q.source_ref)}` : ''}${q.tags.length ? ' · ' + q.tags.map(esc).join(', ') : ''}</div>`;
  }

  function drawReview() {
    const body = $('#mbody', el);
    if (!st.queue.length) { body.innerHTML = `<div class="empty">🎉 Nothing in this queue.<br><span class="small">Change the status filter, or generate more questions.</span></div>`; return; }
    const q = st.queue[st.i];
    body.innerHTML = `<div class="review">
      <div class="small muted">${st.i + 1} of ${st.queue.length} <span class="kbd-hint"><span class="kbd">A</span> approve <span class="kbd">R</span> reject <span class="kbd">E</span> edit <span class="kbd">←</span><span class="kbd">→</span> navigate</span></div>
      <div class="progress"><i style="width:${((st.i + 1) / st.queue.length) * 100}%"></i></div>
      <div class="qcard" id="qcard">${qHtml(q)}</div>
      <div class="review-actions"><button class="btn bad" data-a="rejected">✕ Reject</button><button class="btn" data-a="edit">✎ Edit</button><button class="btn ok" data-a="approved">✓ Approve</button></div>
      <div class="toolbar" style="margin-top:12px;justify-content:space-between">
        <button class="btn sm" data-a="prev" ${st.i === 0 ? 'disabled' : ''}>‹ Prev</button>
        <button class="btn sm" data-a="undo" ${st.history.length ? '' : 'disabled'}>↶ Undo</button>
        <button class="btn sm" data-a="approveSub">Approve all in “${esc(q.subtopic)}”</button>
        <button class="btn sm" data-a="next" ${st.i >= st.queue.length - 1 ? 'disabled' : ''}>Skip ›</button></div></div>`;
    attachSwipe($('#qcard', el));
  }

  function attachSwipe(card) {
    let x0 = null, y0 = 0;
    card.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    card.addEventListener('touchmove', e => {
      if (x0 == null) return;
      const dx = e.touches[0].clientX - x0;
      if (Math.abs(dx) > 10 && Math.abs(e.touches[0].clientY - y0) < 40) { card.style.transform = `translateX(${dx}px) rotate(${dx / 40}deg)`; card.style.opacity = String(1 - Math.min(.5, Math.abs(dx) / 400)); }
    }, { passive: true });
    card.addEventListener('touchend', e => {
      if (x0 == null) return;
      const dx = e.changedTouches[0].clientX - x0; x0 = null;
      card.style.transform = ''; card.style.opacity = '';
      if (dx > 110) setStatus('approved'); else if (dx < -110) setStatus('rejected');
    });
  }

  async function setStatus(status, q = st.queue[st.i]) {
    if (!q) return;
    const prev = q.status;
    try {
      const r = await put('/mcqs/' + enc(q.id), { status });
      q.status = status;
      markDirty('mcqs', q.id, r.affected_paths);
      st.history.push({ id: q.id, prev });
      if (st.history.length > 30) st.history.shift();
      // leaving the current filter -> drop from queue and keep position
      if (st.status && st.status !== status) st.queue.splice(st.i, 1); else st.i = Math.min(st.i + 1, st.queue.length - 1);
      if (st.i >= st.queue.length) st.i = Math.max(0, st.queue.length - 1);
      draw();
    } catch (e) { toast(e.message, true); }
  }

  async function undo() {
    const h = st.history.pop();
    if (!h) return;
    try {
      const r = await put('/mcqs/' + enc(h.id), { status: h.prev });
      const row = st.rows.find(x => x.id === h.id); if (row) row.status = h.prev;
      markDirty('mcqs', h.id, r.affected_paths);
      applyFilters(false);
      const idx = st.queue.findIndex(x => x.id === h.id); if (idx >= 0) st.i = idx;
      draw(); toast('Undone.');
    } catch (e) { toast(e.message, true); }
  }

  async function approveSub() {
    const q = st.queue[st.i]; if (!q) return;
    const ids = st.queue.filter(x => x.system === q.system && x.subtopic === q.subtopic && x.status === 'draft').map(x => x.id);
    if (!confirm(`Approve ${ids.length} draft question(s) in ${q.system} / ${q.subtopic}?`)) return;
    try {
      const r = await post('/mcqs/bulk-status', { ids, status: 'approved' });
      markDirty('mcqs', 'bulk', r.affected_paths);
      toast(`${r.touched} approved.`);
      await refresh(true);
    } catch (e) { toast(e.message, true); }
  }

  /* ---------- edit sheet ---------- */
  function openEdit(q) {
    const opts = q.options.map(o => o.text);
    while (opts.length < 5) opts.push('');
    const sh = openSheet({
      title: 'Edit question',
      body: `<label class="f"><span>Stem</span><textarea id="e_stem" rows="5">${esc(q.stem)}</textarea></label>
        <div class="section-title" style="margin-top:0">Options — tap the radio for the correct answer (leave 5th blank for 4 options)</div>
        ${opts.map((t, i) => `<div style="display:flex;gap:10px;align-items:center;margin-bottom:8px"><input type="radio" name="e_ans" value="${'ABCDE'[i]}" ${q.answer === 'ABCDE'[i] ? 'checked' : ''} style="width:22px;height:22px;flex:none" aria-label="Correct answer ${'ABCDE'[i]}"><b style="width:18px">${'ABCDE'[i]}</b><input type="text" data-opt value="${esc(t)}"></div>`).join('')}
        <label class="f"><span>Explanation</span><textarea id="e_expl" rows="5">${esc(q.explanation)}</textarea></label>
        <div class="row2"><label class="f"><span>Difficulty</span><select id="e_diff">${selectOptions(DIFFS, q.difficulty)}</select></label>
        <label class="f"><span>Tags (comma separated)</span><input type="text" id="e_tags" value="${esc(q.tags.join(', '))}"></label></div>
        <div class="small muted">${esc(q.system)} / ${esc(q.subtopic)} · ${esc(q.source_title || q.source_ref)}</div>`,
      footer: `<button class="btn primary" data-act="save">Save</button><button class="btn ok" data-act="saveapprove">Save &amp; approve</button><span class="spacer"></span><button class="btn bad" data-act="delete">Delete</button>`,
    });
    sh.foot.onclick = async (e) => {
      const act = e.target.dataset.act; if (!act) return;
      try {
        if (act === 'delete') {
          if (!confirm('Delete this question permanently?')) return;
          const r = await del('/mcqs/' + enc(q.id)); markDirty('mcqs', q.id, r.affected_paths);
          closeSheet(); await refresh(true); return;
        }
        const sel = $('input[name=e_ans]:checked', sh.body);
        const selIdx = sel ? 'ABCDE'.indexOf(sel.value) : -1;
        const keep = []; let answer = '';
        $$('[data-opt]', sh.body).forEach((inp, i) => { const t = inp.value.trim(); if (!t) return; if (i === selIdx) answer = 'ABCDE'[keep.length]; keep.push(t); });
        if (!answer) { toast('Pick a non-empty correct option.', true); return; }
        const body = { stem: $('#e_stem', sh.body).value, options: keep, answer, explanation: $('#e_expl', sh.body).value, difficulty: $('#e_diff', sh.body).value, tags: $('#e_tags', sh.body).value };
        if (act === 'saveapprove') body.status = 'approved';
        const r = await put('/mcqs/' + enc(q.id), body);
        if (r.updated) markDirty('mcqs', q.id, r.affected_paths);
        toast(r.updated ? 'Saved.' : 'No changes.');
        closeSheet(); await refresh(true);
      } catch (err) { toast(err.message, true); }
    };
  }

  /* ---------- browse ---------- */
  function drawBrowse() {
    const body = $('#mbody', el);
    if (!st.queue.length) { body.innerHTML = '<div class="empty">No questions match.</div>'; return; }
    const rows = st.queue.slice(0, 200);
    body.innerHTML = `<div class="list">${rows.map(q => `<div class="li" data-id="${esc(q.id)}" style="grid-template-columns:1fr 200px">
        <div class="c-main"><div class="t" style="font-weight:600">${esc(q.stem.length > 160 ? q.stem.slice(0, 160) + '…' : q.stem)}</div><div class="s">${esc(q.subtopic)}</div></div>
        <div class="c-meta meta"><span class="tag">${esc(q.system)}</span>${pill(q.status)}${pill(q.difficulty, 'info')}</div></div>`).join('')}</div>
      ${st.queue.length > 200 ? `<div class="pager">Showing 200 of ${st.queue.length} — narrow the filters.</div>` : ''}`;
  }

  /* ---------- generate ---------- */
  function openGenerate() {
    const sh = openSheet({
      title: 'Generate MCQs',
      body: `<p class="muted small">Runs <code>mcq_generator.py</code> on new/changed sources. Questions arrive as drafts for review.</p>
        <label class="f"><span>Source</span><select id="g_src"><option value="all">Theory + guidelines</option><option value="theory">Theory only</option><option value="guidelines">Guidelines only</option></select></label>
        <label class="f"><span>System (optional)</span><select id="g_spec">${selectOptions(SYSTEMS, '', 'All systems')}</select></label>
        <div class="row2"><label class="f"><span>Max sources</span><input type="number" id="g_max" value="3" min="1" max="50"></label>
        <label class="f"><span>Questions / source</span><input type="number" id="g_per" value="8" min="1" max="20"></label></div>
        <label class="f"><span><input type="checkbox" id="g_gem"> Use Gemini instead of OpenRouter</span></label>
        <pre class="log hide" id="g_log"></pre>`,
      footer: `<button class="btn primary" id="g_go">Start</button>`,
    });
    $('#g_go', sh.foot).onclick = async (e) => {
      e.target.disabled = true;
      try {
        const job = await post('/mcqs/generate', { source: $('#g_src', sh.body).value, spec: $('#g_spec', sh.body).value, max: +$('#g_max', sh.body).value, per_source: +$('#g_per', sh.body).value, gemini: $('#g_gem', sh.body).checked });
        const log = $('#g_log', sh.body); log.classList.remove('hide'); log.textContent = 'Running… (can take several minutes)\n' + job.cmd;
        const t = setInterval(async () => {
          try {
            const s = await get('/mcqs/generate/' + job.job_id);
            if (s.status !== 'running') { clearInterval(t); log.textContent = `[${s.status}]\n` + s.log; e.target.disabled = false; toast('Generation ' + s.status, s.status !== 'done'); refresh(true); }
          } catch (_) { clearInterval(t); e.target.disabled = false; }
        }, 3000);
      } catch (err) { toast(err.message, true); e.target.disabled = false; }
    };
  }

  /* ---------- events ---------- */
  el.addEventListener('click', e => {
    const t = e.target;
    if (t.id === 'mgen') return openGenerate();
    if (t.id === 'mft') return $('#mfilters', el).classList.toggle('open');
    if (t.dataset.m) { st.mode = t.dataset.m; $$('#mmode button', el).forEach(b => b.classList.toggle('on', b === t)); draw(); return; }
    const a = t.closest('[data-a]')?.dataset.a;
    if (a === 'approved' || a === 'rejected') setStatus(a);
    else if (a === 'edit') openEdit(st.queue[st.i]);
    else if (a === 'prev') { st.i = Math.max(0, st.i - 1); draw(); }
    else if (a === 'next') { st.i = Math.min(st.queue.length - 1, st.i + 1); draw(); }
    else if (a === 'undo') undo();
    else if (a === 'approveSub') approveSub();
    const li = t.closest('.li[data-id]');
    if (li && st.mode === 'browse') { const q = st.rows.find(r => r.id === li.dataset.id); if (q) openEdit(q); }
  });
  el.addEventListener('change', e => {
    if (e.target.id === 'mstatus') st.status = e.target.value;
    else if (e.target.id === 'msystem') st.system = e.target.value;
    else if (e.target.id === 'mdiff') st.difficulty = e.target.value;
    else return;
    applyFilters(true);
  });
  el.addEventListener('input', e => { if (e.target.id === 'mq') { st.q = e.target.value; applyFilters(true); } });

  const keyHandler = (e) => {
    if (!el.isConnected) { document.removeEventListener('keydown', keyHandler); return; }
    if (st.mode !== 'review' || /input|textarea|select/i.test(e.target.tagName) || $('#sheet.show')) return;
    const k = e.key.toLowerCase();
    if (k === 'a') setStatus('approved'); else if (k === 'r') setStatus('rejected');
    else if (k === 'e') st.queue[st.i] && openEdit(st.queue[st.i]);
    else if (k === 'arrowright') { st.i = Math.min(st.queue.length - 1, st.i + 1); draw(); }
    else if (k === 'arrowleft') { st.i = Math.max(0, st.i - 1); draw(); }
    else if (k === 'z') undo();
  };
  document.addEventListener('keydown', keyHandler);

  $('#mbody', el).innerHTML = '<div class="empty">Loading…</div>';
  refresh(false);
}
