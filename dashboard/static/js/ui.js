export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];
export const esc = (s) => (s == null ? '' : String(s)).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const trunc = (s, n) => { s = s || ''; return s.length > n ? s.slice(0, n) + '…' : s; };
export const debounce = (fn, ms = 200) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
export const pill = (s, cls) => `<span class="pill ${esc(cls || s)}">${esc(s)}</span>`;

export function toast(msg, bad) {
  const el = document.createElement('div');
  el.className = 'toast' + (bad ? ' bad' : '');
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), bad ? 5200 : 2800);
}

export function theme() {
  const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = t;
  localStorage.setItem('hc2-theme', t);
}

/* ---- sheet: right drawer on desktop, bottom sheet on mobile ---- */
let onClose = null;
export function openSheet({ title, body, footer = '', onclose }) {
  $('#sheetTitle').textContent = title || '';
  $('#sheetBody').innerHTML = body;
  $('#sheetFoot').innerHTML = footer;
  $('#sheetFoot').classList.toggle('hide', !footer);
  $('#sheetBody').scrollTop = 0;
  $('#sheet').classList.add('show');
  $('#scrim').classList.add('show');
  onClose = onclose || null;
  return { body: $('#sheetBody'), foot: $('#sheetFoot') };
}
export function closeSheet() {
  $('#sheet').classList.remove('show');
  $('#scrim').classList.remove('show');
  if (onClose) { const f = onClose; onClose = null; f(); }
}
export const sheetOpen = () => $('#sheet').classList.contains('show');
document.addEventListener('click', e => { if (e.target.id === 'scrim' || e.target.closest('#sheetClose')) closeSheet(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && sheetOpen()) closeSheet(); });

/* ---- fields ---- */
export function selectOptions(list, current, blank) {
  const opts = (blank != null ? [`<option value="">${esc(blank)}</option>`] : []);
  if (current && !list.includes(current)) list = [...list, current];
  return opts.concat(list.map(v => `<option ${v === current ? 'selected' : ''}>${esc(v)}</option>`)).join('');
}

/* ---- markdown-ish toolbar for textareas ---- */
export function toolbar(taId) {
  return `<div class="toolbar" style="margin:0 0 6px">
    <button type="button" class="btn sm" data-fmt="b" data-ta="${taId}"><b>B</b></button>
    <button type="button" class="btn sm" data-fmt="i" data-ta="${taId}"><i>I</i></button>
    <button type="button" class="btn sm" data-fmt="h" data-ta="${taId}">H</button>
    <button type="button" class="btn sm" data-fmt="ul" data-ta="${taId}">•</button></div>`;
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-fmt]');
  if (!b) return;
  const ta = document.getElementById(b.dataset.ta);
  if (!ta) return;
  const s = ta.selectionStart, en = ta.selectionEnd, v = ta.value, f = b.dataset.fmt;
  const wrap = (a, z) => { ta.value = v.slice(0, s) + a + v.slice(s, en) + z + v.slice(en); ta.selectionStart = s + a.length; ta.selectionEnd = en + a.length; };
  if (f === 'b') wrap('**', '**');
  else if (f === 'i') wrap('*', '*');
  else if (f === 'h') wrap('## ', '');
  else if (f === 'ul') {
    const ls = v.lastIndexOf('\n', s - 1) + 1, le = v.indexOf('\n', en), e2 = le === -1 ? v.length : le;
    ta.value = v.slice(0, ls) + v.slice(ls, e2).split('\n').map(l => l.trim() ? '- ' + l.replace(/^[-*]\s*/, '') : l).join('\n') + v.slice(e2);
  }
  ta.focus();
});

/* ---- generic JSON content editor (port of the old path-based editor) ---- */
let cid = 0;
export function contentEditor(obj) {
  return Object.keys(obj).map(key => {
    const val = obj[key];
    const label = esc(key) + (Array.isArray(val) ? ` (${val.length})` : '');
    return `<details class="ce"><summary>${label}</summary><div>${ceValue(val, [key])}</div></details>`;
  }).join('');
}
function ceValue(val, path) {
  const p = esc(JSON.stringify(path));
  const id = 'ce' + (cid++);
  if (Array.isArray(val)) {
    if (!val.length) return '<p class="muted small">(empty)</p>';
    if (typeof val[0] === 'string')
      return `${toolbar(id)}<textarea id="${id}" data-path='${p}' data-lines rows="${Math.max(3, Math.min(14, val.length + 1))}">${esc(val.join('\n'))}</textarea>`;
    if (typeof val[0] === 'object')
      return val.map((it, i) => `<div class="ce-sub">${Object.entries(it || {}).map(([k, v]) => `<label>${esc(k)}</label>${ceValue(v, [...path, i, k])}`).join('')}</div>`).join('');
  }
  if (typeof val === 'string')
    return `${toolbar(id)}<textarea id="${id}" data-path='${p}' rows="${Math.max(2, Math.min(12, val.split('\n').length + 1))}">${esc(val)}</textarea>`;
  if (typeof val === 'number') return `<input type="number" id="${id}" data-path='${p}' value="${esc(val)}">`;
  return '';
}
export function collectContent(root, original) {
  const out = JSON.parse(JSON.stringify(original));
  $$('[data-path]', root).forEach(el => {
    const path = JSON.parse(el.dataset.path);
    let t = out;
    for (let i = 0; i < path.length - 1; i++) t = t[path[i]];
    const k = path[path.length - 1];
    if (el.hasAttribute('data-lines')) t[k] = el.value.split('\n').map(s => s.trim()).filter(Boolean);
    else if (el.type === 'number') t[k] = parseFloat(el.value);
    else t[k] = el.value;
  });
  return out;
}
