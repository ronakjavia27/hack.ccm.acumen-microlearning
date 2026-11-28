// Accounts, Backups, Audit, Maintenance.
import { $, $$, esc, pill, toast } from '../ui.js';
import { get, put, post, del } from '../api.js';
import { load } from '../store.js';

/* ================= Accounts ================= */
export async function accounts(el) {
  el.innerHTML = `<div class="head"><div><h1>Accounts</h1><p id="asub"></p></div></div>
    <div class="card" style="margin-bottom:14px"><b>Default features for new users</b><div id="adefs" style="display:flex;flex-wrap:wrap;gap:8px;margin:10px 0"></div>
      <button class="btn sm primary" id="asave">Save defaults</button></div>
    <div class="toolbar"><input type="search" class="grow" id="aq" placeholder="Search email, name, workplace…"></div>
    <div id="alist" class="list"><div class="empty">Loading…</div></div>`;
  let users = [], defs = {};
  try { [users, defs] = await Promise.all([get('/accounts'), get('/accounts/defaults')]); }
  catch (e) { $('#alist', el).innerHTML = `<div class="empty">Load failed: ${esc(e.message)}</div>`; return; }
  const keys = Object.keys(defs).filter(k => k !== 'id');
  const label = (k) => k.replace(/_/g, ' ');
  $('#adefs', el).innerHTML = keys.map(k => `<label class="feat ${defs[k] ? 'on' : ''}"><input type="checkbox" data-def="${k}" ${defs[k] ? 'checked' : ''} hidden>${label(k)}</label>`).join('') || '<span class="muted small">No defaults configured.</span>';

  function draw() {
    const q = $('#aq', el).value.toLowerCase();
    const rows = users.filter(u => !q || [u.email, u.first_name, u.last_name, u.workplace].join(' ').toLowerCase().includes(q));
    $('#asub', el).textContent = `${rows.length} of ${users.length} users`;
    $('#alist', el).innerHTML = rows.length ? rows.map(u => {
      const feats = u.features || {};
      return `<div class="li" style="grid-template-columns:1fr;cursor:default" data-email="${esc(u.email)}">
        <div class="c-main"><div class="t">${esc(u.email)}</div><div class="s">${esc((u.first_name || '') + ' ' + (u.last_name || ''))} · ${esc(u.workplace || '—')} · ${esc(u.city || '—')} · joined ${u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</div></div>
        <div class="meta"><button class="feat ${u.is_admin ? 'on' : ''}" data-admin>${u.is_admin ? '⚡ Admin' : 'Set admin'}</button>
        ${keys.map(k => { const on = feats[k] === true || (feats[k] === undefined && defs[k]); return `<button class="feat ${on ? 'on' : ''}" data-flag="${k}">${label(k)}</button>`; }).join('')}
        <span class="spacer"></span><button class="btn sm bad" data-del>Delete</button></div></div>`;
    }).join('') : '<div class="empty">No users.</div>';
  }
  draw();
  $('#aq', el).oninput = draw;
  el.onclick = async (e) => {
    const t = e.target;
    if (t.id === 'asave') {
      const out = {}; $$('[data-def]', el).forEach(c => { out[c.dataset.def] = c.checked; });
      try { await put('/accounts/defaults', out); defs = out; toast('Defaults saved.'); } catch (err) { toast(err.message, true); }
      return;
    }
    const lab = t.closest('label.feat');
    if (lab && lab.querySelector('[data-def]')) { setTimeout(() => lab.classList.toggle('on', lab.querySelector('input').checked)); return; }
    const row = t.closest('[data-email]'); if (!row) return;
    const u = users.find(x => x.email === row.dataset.email); if (!u) return;
    try {
      if (t.hasAttribute('data-admin')) { await put('/accounts/' + encodeURIComponent(u.email), { is_admin: !u.is_admin }); u.is_admin = !u.is_admin; toast(u.is_admin ? 'Admin granted.' : 'Admin removed.'); }
      else if (t.dataset.flag) {
        const k = t.dataset.flag, cur = (u.features || {})[k] === true || ((u.features || {})[k] === undefined && defs[k]);
        const features = Object.assign({}, u.features, { [k]: !cur });
        await put('/accounts/' + encodeURIComponent(u.email), { features }); u.features = features; toast(`${k} ${!cur ? 'on' : 'off'}.`);
      } else if (t.hasAttribute('data-del')) {
        if (!confirm('Delete user ' + u.email + '?')) return;
        await del('/accounts/' + encodeURIComponent(u.email)); users = users.filter(x => x !== u); toast('Deleted.');
      } else return;
      draw();
    } catch (err) { toast(err.message, true); }
  };
}

/* ================= Backups ================= */
export async function backups(el) {
  el.innerHTML = `<div class="head"><div><h1>Backups</h1><p>Manual — you trigger every backup and restore</p></div></div>
    <div class="card" style="margin-bottom:14px"><b>Create backup</b><div class="toolbar" style="margin:10px 0 0"><input type="text" id="blabel" class="grow" placeholder="label (optional)"><button class="btn primary" id="bgo">Backup now</button></div></div>
    <div class="card" style="margin-bottom:14px"><b>Restore</b><div class="toolbar" style="margin:10px 0 0"><select id="bsel" class="grow"><option value="">Select backup</option></select><input type="text" id="btarget" class="grow" placeholder="target path"></div>
      <label class="small muted"><input type="checkbox" id="bforce"> allow overwrite (--force)</label> <button class="btn" id="brestore" style="margin-left:8px">Restore</button></div>
    <div class="list" id="blist"><div class="empty">Loading…</div></div>`;
  async function list() {
    try {
      const l = await get('/backup');
      $('#bsel', el).innerHTML = '<option value="">Select backup</option>' + l.map(b => `<option value="${esc(b.name)}">${esc(b.name)} (${esc(b.timestamp)})</option>`).join('');
      $('#blist', el).innerHTML = l.length ? l.map(b => `<div class="li" style="grid-template-columns:1fr auto;cursor:default"><div class="c-main"><div class="t mono">${esc(b.name)}</div><div class="s">${esc(b.timestamp)} · ${esc(b.label)} · ${b.file_count} files · ${b.size_kb} KB · HEAD ${esc(b.git_head || '')}</div></div><div class="meta">${b.dirty ? pill('dirty', 'hidden') : ''}<button class="btn sm" data-verify="${esc(b.name)}">Verify</button></div></div>`).join('') : '<div class="empty">No backups yet.</div>';
    } catch (e) { toast(e.message, true); }
  }
  list();
  el.onclick = async (e) => {
    const t = e.target;
    try {
      if (t.id === 'bgo') { const r = await post('/backup', { label: $('#blabel', el).value || 'dashboard' }, 300000); toast('Backup created.'); list(); }
      else if (t.id === 'brestore') {
        const name = $('#bsel', el).value, target = $('#btarget', el).value;
        if (!name || !target) { toast('Select a backup and a target path.', true); return; }
        const r = await post('/backup/restore', { from: name, to: target, force: $('#bforce', el).checked }, 300000); toast('Restored to ' + r.restored_to);
      } else if (t.dataset.verify) { const r = await get('/backup/verify/' + encodeURIComponent(t.dataset.verify)); toast(r.ok === false ? 'Verify failed: ' + (r.error || '') : 'Backup verified.', r.ok === false); }
    } catch (err) { toast(err.message, true); }
  };
}

/* ================= Audit ================= */
export async function audit(el) {
  el.innerHTML = `<div class="head"><div><h1>Audit log</h1><p>Last 200 console edits</p></div></div><div class="list" id="alog"><div class="empty">Loading…</div></div>`;
  try {
    const rows = await get('/audit?n=200');
    $('#alog', el).innerHTML = rows.length ? rows.map(e => `<div class="li" style="grid-template-columns:1fr auto;cursor:default"><div class="c-main"><div class="t"><span class="tag">${esc(e.kind)}</span> ${esc(e.action)}</div><div class="s mono">${esc(String(e.id).slice(0, 80))}${e.fields && e.fields.length ? ' · ' + esc(e.fields.join(', ')) : ''}${e.note ? ' · ' + esc(e.note) : ''}</div></div><div class="meta"><span class="s">${esc(e.ts)}</span></div></div>`).join('') : '<div class="empty">Empty.</div>';
  } catch (e) { $('#alog', el).innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}

/* ================= Maintenance ================= */
export function maintenance(el) {
  el.innerHTML = `<div class="head"><div><h1>Maintenance</h1><p>Orphan detection and health checks</p></div></div>
    <div class="card" style="margin-bottom:14px"><b>Orphaned pearls</b><p class="muted small">Pearls whose file_name matches no summary in the ledger.</p><button class="btn" id="mo">Scan orphans</button><div id="mores" style="margin-top:10px"></div></div>
    <div class="card"><b>Summaries needing attention</b><p class="muted small">md_generated ≠ Yes, or parsing_notes ≠ Success.</p><button class="btn" id="mf">Scan failed</button><div id="mfres" style="margin-top:10px"></div></div>`;
  el.onclick = async (e) => {
    try {
      if (e.target.id === 'mo') {
        const [s, p] = await Promise.all([load('summaries'), load('pearls')]);
        const files = new Set(s.map(x => x.file_name || ''));
        const orph = p.filter(x => { const fn = x.file_name || ''; return !files.has(fn) && !files.has(fn.replace(/\.json$/, '.pdf')); });
        const names = [...new Set(orph.map(o => o.file_name))];
        $('#mores', el).innerHTML = names.length ? `<p>${orph.length} orphaned pearls from ${names.length} missing files:</p><pre class="log">${names.slice(0, 60).map(esc).join('\n')}</pre>` : '<p style="color:var(--ok)">No orphans found.</p>';
      } else if (e.target.id === 'mf') {
        const s = await load('summaries');
        const bad = s.filter(x => x.md_generated !== 'Yes' || (x.parsing_notes && x.parsing_notes !== 'Success'));
        $('#mfres', el).innerHTML = bad.length ? `<p>${bad.length} need attention:</p><pre class="log">${bad.map(x => `#${x.id} ${esc(x.title)} — ${esc(x.parsing_notes || 'md_generated: ' + x.md_generated)}`).join('\n')}</pre>` : '<p style="color:var(--ok)">All summaries healthy.</p>';
      }
    } catch (err) { toast(err.message, true); }
  };
}
