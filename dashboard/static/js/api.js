const BASE = '/console/api';

export async function api(method, path, body, timeoutMs = 60000) {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);
  const opts = { method, headers: { 'Content-Type': 'application/json' }, signal: ac.signal, credentials: 'same-origin' };
  if (body !== undefined) opts.body = JSON.stringify(body);
  try {
    const r = await fetch(BASE + path, opts);
    if (r.status === 401) { location.href = '/console'; throw new Error('Token required'); }
    if (!r.ok) {
      let msg = await r.text();
      try { const j = JSON.parse(msg); msg = j.detail || msg; } catch (_) {}
      throw new Error(typeof msg === 'string' ? msg.slice(0, 240) : JSON.stringify(msg).slice(0, 240));
    }
    return await r.json();
  } finally { clearTimeout(timer); }
}
export const get = (p) => api('GET', p);
export const put = (p, b) => api('PUT', p, b);
export const post = (p, b, t) => api('POST', p, b, t);
export const del = (p) => api('DELETE', p);
// ids can contain "/" (flashcards: "System/Subtopic") — path routes accept that as-is.
export const enc = (id) => String(id).split('/').map(encodeURIComponent).join('/');
