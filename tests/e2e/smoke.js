// Browser smoke test for the portal. Prints one JSON document so two builds can be diffed:
//   node tests/e2e/smoke.js http://127.0.0.1:8101 > old.json
//   node tests/e2e/smoke.js http://127.0.0.1:8102 > new.json && diff old.json new.json
// The server must run in local-dev mode (VERCEL unset) so it auto-logs in as admin.
const { chromium } = require('playwright');

const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const VIEWS = ['home', 'papers', 'guidelines', 'pearls', 'trials', 'trials-esbicm', 'trials-condensed', 'bookmarks', 'theory'];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
  page.on('pageerror', (e) => pageErrors.push(String(e.message).slice(0, 200)));
  page.on('requestfailed', (r) => failedRequests.push(new URL(r.url()).host + new URL(r.url()).pathname.slice(0, 60)));

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  // The home view shows a random "pearl of the day", so its text length is not comparable between runs.
  const fingerprint = () => page.evaluate(() => ({
    nodes: document.querySelectorAll('*').length,
    textLen: (document.querySelector('.view.active') || {}).id === 'view-home' ? null : document.body.innerText.length,
    activeView: (document.querySelector('.view.active') || {}).id || null,
    searchResultKids: (document.getElementById('searchResults') || { children: [] }).children.length,
  }));

  const result = { base: 'normalized', initial: await fingerprint(), views: {} };
  for (const v of VIEWS) {
    const ok = await page.evaluate((name) => {
      try { if (typeof showView !== 'function') return 'no showView'; showView(name); return 'ok'; } catch (e) { return 'threw: ' + e.message; }
    }, v);
    await page.waitForTimeout(400);
    result.views[v] = { call: ok, ...(await fingerprint()) };
  }

  await page.evaluate(() => { try { showView('home'); } catch (e) {} });
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(300);
  const input = await page.$('#globalSearchInput');
  if (input) { await input.type('sepsis'); await page.waitForTimeout(1200); }
  result.search = { hasInput: !!input, ...(await fingerprint()) };

  // Every user-defined global (functions + const/let are not on window, but functions and var are):
  result.globals = await page.evaluate(() => {
    const fresh = document.createElement('iframe'); document.body.appendChild(fresh);
    const builtin = new Set(Object.getOwnPropertyNames(fresh.contentWindow));
    fresh.remove();
    return Object.getOwnPropertyNames(window).filter((k) => !builtin.has(k)).sort();
  });
  result.dataSizes = await page.evaluate(() => {
    const names = ['baseDataset', 'allPearls', 'TRIAL_INDEX', 'CONDENSED_INDEX', 'allFlashcardDecks', 'THEORY_NOTES', 'RELATED_CATALOG', 'RELATED_INDEX', 'SUBTOPIC_MAP', 'SPECS', 'TYPES', 'USER_FEATURES'];
    const out = {};
    for (const n of names) { try { const v = eval(n); out[n] = Array.isArray(v) ? v.length : Object.keys(v).length; } catch (e) { out[n] = 'missing'; } }
    out.USER_IS_ADMIN = (() => { try { return eval('USER_IS_ADMIN'); } catch (e) { return 'missing'; } })();
    out.showDisclaimer = (() => { try { return eval('showDisclaimer'); } catch (e) { return 'missing'; } })();
    return out;
  });
  result.consoleErrors = consoleErrors;
  result.pageErrors = pageErrors;
  result.failedRequests = [...new Set(failedRequests)].sort();
  console.log(JSON.stringify(result, null, 1));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
