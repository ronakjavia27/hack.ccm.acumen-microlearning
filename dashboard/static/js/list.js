// Generic responsive list: table-like on desktop, cards on mobile.
import { $, $$, esc, debounce, toast } from './ui.js';
import { load, markDirty } from './store.js';
import { post } from './api.js';

const PAGE = 50;

/**
 * cfg = {
 *   kind, title, sub, grid:'1fr 180px 110px',             // desktop column template (after checkbox)
 *   headers:['Title','System','Status'],
 *   main(row)->html, meta(row)->html, extras(row)->[html...],
 *   search(row)->string, filters:[{key,label,get(row)->string,values?}],
 *   bulk:[{label,cls,fn(ids)->Promise}], open(row), actions?: html (toolbar extras)
 * }
 */
export function mountList(el, cfg) {
  const st = { q: '', f: {}, page: 0, sel: new Set(), rows: [] };
  el.innerHTML = `
    <div class="head"><div><h1>${esc(cfg.title)}</h1><p id="lsub">${esc(cfg.sub || '')}</p></div><div class="spacer"></div>${cfg.actions || ''}</div>
    <div class="toolbar">
      <input type="search" class="grow" id="lq" placeholder="Search…" autocomplete="off">
      <button class="btn filters-toggle" id="lft">Filters</button>
      <div class="filters" id="lfilters"></div>
      <span class="muted small" id="lcount"></span>
    </div>
    <div class="list" id="llist"></div>
    <div class="pager" id="lpager"></div>
    <div id="lbulk"></div>`;

  const hasChk = !!(cfg.bulk && cfg.bulk.length);
  const gridCols = (hasChk ? '28px ' : '') + cfg.grid;

  function filtered() {
    const q = st.q.toLowerCase();
    return st.rows.filter(r => {
      for (const f of cfg.filters || []) { const v = st.f[f.key]; if (v && f.get(r) !== v) return false; }
      return !q || cfg.search(r).toLowerCase().includes(q);
    });
  }

  function renderFilters() {
    $('#lfilters', el).innerHTML = (cfg.filters || []).map(f => {
      const vals = f.values || [...new Set(st.rows.map(f.get).filter(Boolean))].sort();
      return `<select data-f="${f.key}" aria-label="${esc(f.label)}"><option value="">${esc(f.label)}</option>${vals.map(v => `<option ${st.f[f.key] === v ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>`;
    }).join('');
  }

  function render() {
    const rows = filtered();
    const pages = Math.max(1, Math.ceil(rows.length / PAGE));
    if (st.page >= pages) st.page = pages - 1;
    const slice = rows.slice(st.page * PAGE, st.page * PAGE + PAGE);
    $('#lcount', el).textContent = `${rows.length} of ${st.rows.length}`;
    const head = `<div class="li head-row${hasChk ? ' has-chk' : ''}" style="grid-template-columns:${gridCols}">${hasChk ? '<span class="chk"><input type="checkbox" id="lall" aria-label="Select all"></span>' : ''}${cfg.headers.map(h => `<span>${esc(h)}</span>`).join('')}</div>`;
    const body = slice.map(r => {
      const id = esc(r.id);
      const ex = (cfg.extras ? cfg.extras(r) : []).map(x => `<div class="c-extra">${x}</div>`).join('');
      return `<div class="li${hasChk ? ' has-chk' : ''}" data-id="${id}" style="grid-template-columns:${gridCols}">
        ${hasChk ? `<span class="chk"><input type="checkbox" data-sel="${id}" ${st.sel.has(String(r.id)) ? 'checked' : ''} aria-label="Select"></span>` : ''}
        <div class="c-main">${cfg.main(r)}</div><div class="c-meta meta">${cfg.meta(r)}</div>${ex}</div>`;
    }).join('');
    $('#llist', el).innerHTML = rows.length ? head + body : '<div class="empty">Nothing matches these filters.</div>';
    $('#lpager', el).innerHTML = pages > 1
      ? `<button class="btn sm" data-pg="-1" ${st.page === 0 ? 'disabled' : ''}>‹ Prev</button><span>${st.page + 1} / ${pages}</span><button class="btn sm" data-pg="1" ${st.page >= pages - 1 ? 'disabled' : ''}>Next ›</button>` : '';
    renderBulk();
  }

  function renderBulk() {
    if (!hasChk) return;
    const n = st.sel.size;
    $('#lbulk', el).innerHTML = n ? `<div class="bulkbar"><b>${n} selected</b><span class="spacer"></span>
      ${cfg.bulk.map((b, i) => `<button class="btn sm ${b.cls || ''}" data-bulk="${i}">${esc(b.label)}</button>`).join('')}
      <button class="btn sm ghost" data-bulk="clear" style="color:inherit">Clear</button></div>` : '';
  }

  el.addEventListener('input', debounce(e => { if (e.target.id === 'lq') { st.q = e.target.value; st.page = 0; render(); } }, 150));
  el.addEventListener('change', e => {
    const t = e.target;
    if (t.dataset.f) { st.f[t.dataset.f] = t.value; st.page = 0; render(); }
    else if (t.dataset.sel) { t.checked ? st.sel.add(t.dataset.sel) : st.sel.delete(t.dataset.sel); renderBulk(); }
    else if (t.id === 'lall') { filtered().slice(st.page * PAGE, st.page * PAGE + PAGE).forEach(r => t.checked ? st.sel.add(String(r.id)) : st.sel.delete(String(r.id))); render(); }
  });
  el.addEventListener('click', async e => {
    const t = e.target;
    if (t.id === 'lft') { $('#lfilters', el).classList.toggle('open'); return; }
    if (t.dataset.pg) { st.page += Number(t.dataset.pg); render(); window.scrollTo({ top: 0 }); return; }
    if (t.dataset.bulk) {
      if (t.dataset.bulk === 'clear') { st.sel.clear(); render(); return; }
      const b = cfg.bulk[Number(t.dataset.bulk)];
      try { await b.fn([...st.sel]); st.sel.clear(); await reload(true); } catch (err) { toast(err.message, true); }
      return;
    }
    if (t.closest('.chk')) return;
    const li = t.closest('.li[data-id]');
    if (li) { const row = st.rows.find(r => String(r.id) === li.dataset.id); if (row) cfg.open(row, reload); }
  });

  async function reload(force) {
    try {
      st.rows = await load(cfg.kind, !!force);
      renderFilters();
      render();
    } catch (e) { $('#llist', el).innerHTML = `<div class="empty">Load failed: ${esc(e.message)}</div>`; }
  }
  $('#llist', el).innerHTML = '<div class="empty">Loading…</div>';
  reload(false);
  return { reload };
}

export async function bulkStatus(kind, ids, status) {
  const r = await post(`/${kind}/bulk-status`, { ids, status });
  markDirty(kind, 'bulk-status', r.affected_paths);
  toast(`${ids.length} set to "${status}"`);
}
export async function bulkDelete(kind, ids, label) {
  if (!confirm(`Delete ${ids.length} ${label || kind}? This cannot be undone.`)) throw new Error('Cancelled');
  const r = await post(`/${kind}/bulk-delete`, { ids });
  markDirty(kind, 'bulk-delete', r.affected_paths);
  toast(`${r.deleted} deleted` + (r.pearls_deleted ? ` (+${r.pearls_deleted} pearls)` : ''));
}
