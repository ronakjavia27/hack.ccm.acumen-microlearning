import { get, post } from './api.js';
import { toast, $ } from './ui.js';

export const SYSTEMS = ['Cardiology', 'Endocrinology', 'Gastroenterology', 'General', 'Hematology', 'Hepatology',
  'Infectious Diseases', 'Multisystem', 'Nephrology', 'Neurology', 'Nutrition', 'Obstetrics And Gynecology',
  'Other', 'Pulmonology', 'Sepsis', 'Surgery', 'Trauma'];
export const PEARL_TYPES = ['Guideline', 'Meta-analysis', 'Review', 'Trial', 'Observational', 'Other'];

export const store = {
  cache: {},          // kind -> rows
  loaded: {},         // kind -> bool
  subtopics: {},
  dirty: new Map(),   // "kind:id" -> [paths]  (saved to disk, not yet pushed to git)
};

export async function load(kind, force = false) {
  if (store.loaded[kind] && !force) return store.cache[kind];
  store.cache[kind] = await get('/' + kind);
  store.loaded[kind] = true;
  return store.cache[kind];
}
export async function loadSubtopics() {
  if (!Object.keys(store.subtopics).length) store.subtopics = await get('/subtopics').catch(() => ({}));
  return store.subtopics;
}
export const subtopicsFor = (system) => store.subtopics[system] || [];

export function markDirty(kind, id, paths) {
  const key = kind + ':' + id;
  store.dirty.set(key, paths && paths.length ? paths : (store.dirty.get(key) || []));
  renderPush();
}
export function renderPush() {
  const b = $('#pushBtn');
  if (b) b.dataset.n = String(store.dirty.size);
}

export async function pushAll() {
  const paths = [...new Set([...store.dirty.values()].flat())];
  if (!store.dirty.size) { toast('Nothing to push.'); return; }
  if (!paths.length) { toast('Edits have no file paths to push.', true); return; }
  try {
    const { job_id } = await post('/push-all', { all_paths: paths });
    toast('Pushing…');
    const t = setInterval(async () => {
      try {
        const s = await get('/push/' + job_id);
        if (s.status === 'done') { clearInterval(t); store.dirty.clear(); renderPush(); toast('Pushed ' + (s.commit_sha || '').slice(0, 8)); }
        else if (s.status === 'failed') { clearInterval(t); toast('Push failed: ' + s.message, true); }
      } catch (_) { clearInterval(t); }
    }, 1500);
  } catch (e) { toast(e.message, true); }
}
