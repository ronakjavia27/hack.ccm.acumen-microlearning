// Browser test for the sign-in page. Prints one JSON document so two builds can be diffed:
//   node tests/e2e/landing.js http://127.0.0.1:8101 8101 > old.json
//   node tests/e2e/landing.js http://127.0.0.1:8102 8102 > new.json && diff old.json new.json
// The server must NOT be in local-dev mode (start it with VERCEL=0 and OAUTH_CLIENT_ID=test-client).
// The Google section only shows on hackccm.vercel.app, so that hostname is mapped to 127.0.0.1.
const { chromium } = require('playwright');

const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const PORT = process.argv[3] || new URL(BASE).port;
const PROD_HOST = 'hackccm.vercel.app';

(async () => {
  const browser = await chromium.launch({ args: [`--host-resolver-rules=MAP ${PROD_HOST} 127.0.0.1`] });
  const out = {};
  const attach = (page, bucket) => {
    page.on('pageerror', (e) => bucket.push(String(e.message).slice(0, 160)));
  };

  // ---- plain host: forms, tabs, disclaimer, bad login, real signup
  {
    const errors = [];
    const page = await browser.newPage();
    attach(page, errors);
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    const vis = (sel) => page.evaluate((s) => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none'; }, sel);
    out.title = await page.title();
    out.initial = { login: await vis('#loginForm'), signup: await vis('#signupForm'), googleSection: await vis('#googleSection') };

    await page.click('#tabSignup');
    out.afterSignupTab = { login: await vis('#loginForm'), signup: await vis('#signupForm'), activeTab: await page.$eval('.tab.active', (e) => e.id) };
    await page.click('#tabLogin');
    out.afterLoginTab = { login: await vis('#loginForm'), signup: await vis('#signupForm'), activeTab: await page.$eval('.tab.active', (e) => e.id) };

    await page.click('#loginPwToggle');
    out.pwToggled = { type: await page.$eval('#loginPassword', (e) => e.type), label: await page.$eval('#loginPwToggle', (e) => e.textContent) };
    await page.click('#loginPwToggle');
    out.pwToggledBack = { type: await page.$eval('#loginPassword', (e) => e.type), label: await page.$eval('#loginPwToggle', (e) => e.textContent) };

    await page.click('#landingDisclaimerLink');
    out.disclaimer = await page.evaluate(() => {
      const t = document.getElementById('landingDisclaimerText');
      return { overlay: getComputedStyle(document.getElementById('landingDisclaimerOverlay')).display, textLen: t.innerText.length,
               head: t.innerText.slice(0, 70), strongs: t.querySelectorAll('strong').length, paragraphs: t.querySelectorAll('p').length };
    });
    await page.click('#landingDisclaimerClose');
    out.disclaimerClosed = await page.$eval('#landingDisclaimerOverlay', (e) => getComputedStyle(e).display);

    await page.fill('#loginEmail', 'nobody@example.com');
    await page.fill('#loginPassword', 'wrong-password');
    await page.click('#loginForm button[type=submit]');
    await page.waitForFunction(() => document.getElementById('loginError').textContent.length > 0);
    out.badLoginError = await page.$eval('#loginError', (e) => e.textContent);

    await page.click('#tabSignup');
    await page.fill('#signupEmail', `e2e-${PORT}-${Date.now()}@example.com`);
    await page.fill('#signupPassword', 'longenough1');
    await page.fill('#signupFirstName', 'E2E');
    await page.click('#signupForm button[type=submit]');
    await page.waitForFunction(() => document.title.includes('Knowledge Portal'), null, { timeout: 15000 });
    out.afterSignup = { title: await page.title(), cookies: (await page.context().cookies()).map((c) => c.name) };
    out.landingErrors = errors;
    await page.close();
  }

  // ---- production host: Google section (GSI is blocked in the sandbox, so the redirect-link fallback renders)
  {
    const errors = [];
    const page = await browser.newPage();
    attach(page, errors);
    await page.goto(`http://${PROD_HOST}:${PORT}/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    out.google = await page.evaluate(() => {
      const sec = document.getElementById('googleSection');
      const a = document.querySelector('#googleButtonWrapper a');
      return { sectionVisible: !!sec && getComputedStyle(sec).display !== 'none', hasFallbackLink: !!a,
               href: a ? a.getAttribute('href') : null, clientId: typeof CLIENT_ID !== 'undefined' ? CLIENT_ID : null,
               isProduction: typeof IS_PRODUCTION !== 'undefined' ? IS_PRODUCTION : null };
    });
    // redirect-flow landing: ?hackccm_sess=... is stored as a cookie, the URL is cleaned and the page reloads
    await page.goto(`http://${PROD_HOST}:${PORT}/?hackccm_sess=abc123`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    out.sessParam = await page.evaluate(() => ({ search: location.search, cookie: document.cookie }));
    out.googleErrors = errors;
    await page.close();
  }
  console.log(JSON.stringify(out, null, 1));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
