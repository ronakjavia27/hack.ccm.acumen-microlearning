const puppeteer = require('puppeteer');
const fs = require('fs');

const SITE_URL = process.argv[2] || 'https://hack-ccm-acumen-microlearning.vercel.app';
const GUARD_JS_PATTERNS = ['guard', 'security', 'protect', 'block']; // add your guard file names here

// =====================================================================
// TEST SUITE
// =====================================================================
const results = { pass: 0, fail: 0, tests: [] };

function test(name, passed, detail = '') {
  results.tests.push({ name, passed, detail });
  if (passed) results.pass++; else results.fail++;
  console.log(`${passed ? '  PASS' : '  FAIL'} ${name}${detail ? ' — ' + detail : ''}`);
}

(async () => {
  console.log(`\n=== Guardrail Red-Team Test ===`);
  console.log(`Target: ${SITE_URL}\n`);

  // ------------------------------------------------------------------
  // TEST 1: Direct HTTP access (curl equivalent) — can you get content without JS?
  // ------------------------------------------------------------------
  console.log('\n--- 1. HTTP-level tests ---');
  try {
    const resp = await fetch(SITE_URL);
    const html = await resp.text();
    const hasContent = html.includes('hack.CCM') || html.includes('Knowledge Portal');
    test('Content loads without JS', hasContent, `Page title found: ${hasContent}`);
    test('Status 200', resp.status === 200, `HTTP ${resp.status}`);

    // Check if raw content is in HTML (not JS-rendered)
    const rawTextSize = html.length;
    test('Content size > 10KB', rawTextSize > 10000, `${(rawTextSize/1024).toFixed(1)}KB`);
  } catch (e) {
    test('HTTP fetch', false, e.message);
  }

  // ------------------------------------------------------------------
  // TEST 2: Puppeteer — headless extraction
  // ------------------------------------------------------------------
  console.log('\n--- 2. Headless browser tests ---');
  let browser;
  try {
    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.goto(SITE_URL, { waitUntil: 'networkidle0', timeout: 30000 });

    // 2a. Text extraction
    const bodyText = await page.evaluate(() => document.body.innerText);
    const textLen = bodyText.trim().length;
    test('Extract page text', textLen > 100, `${textLen} chars extracted`);

    // 2b. Screenshot
    await page.screenshot({ path: 'bypass_screenshot.png', fullPage: true });
    const ssExists = fs.existsSync('bypass_screenshot.png');
    const ssSize = ssExists ? fs.statSync('bypass_screenshot.png').size : 0;
    test('Screenshot bypass', ssSize > 5000, `${(ssSize/1024).toFixed(1)}KB`);

    // 2c. PDF generation
    await page.pdf({ path: 'bypass_print.pdf', format: 'A4' });
    const pdfExists = fs.existsSync('bypass_print.pdf');
    const pdfSize = pdfExists ? fs.statSync('bypass_print.pdf').size : 0;
    test('Print-to-PDF bypass', pdfSize > 5000, `${(pdfSize/1024).toFixed(1)}KB`);

    // 2d. Copy content via JS
    const selections = await page.evaluate(() => {
      const el = document.createElement('div');
      el.textContent = 'test-selection-' + Date.now();
      document.body.appendChild(el);
      const range = document.createRange();
      range.selectNode(el);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      const copied = sel.toString();
      sel.removeAllRanges();
      el.remove();
      return copied;
    });
    test('Text selection works', selections.includes('test-selection'));

    // 2e. Check if guard JS code ran
    const guardRan = await page.evaluate(() => {
      // Check for common guardrail signatures
      const body = document.body;
      return {
        contextMenuBlocked: body.oncontextmenu !== null || document.body.getAttribute('oncontextmenu') !== null,
        noSelectCSS: getComputedStyle(document.body).userSelect === 'none',
        hasGuardScript: !!document.querySelector('script[src*="guard"], script[src*="security"]')
      };
    });
    test('Right-click guard present', guardRan.contextMenuBlocked, `oncontextmenu: ${guardRan.contextMenuBlocked}`);
    test('user-select:none CSS guard', guardRan.noSelectCSS);
    test('Dedicated guard script loaded', guardRan.hasGuardScript);

    await browser.close();
  } catch (e) {
    test('Puppeteer setup', false, e.message);
    if (browser) await browser.close();
  }

  // ------------------------------------------------------------------
  // TEST 3: Request Interception (blocking guard JS)
  // ------------------------------------------------------------------
  console.log('\n--- 3. Guard script interception ---');
  try {
    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();

    // Block any JS files matching guard patterns
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      if (req.resourceType() === 'script') {
        const url = req.url();
        const isGuard = GUARD_JS_PATTERNS.some(p => url.toLowerCase().includes(p));
        if (isGuard) {
          req.respond({ body: '', contentType: 'application/javascript' });
          return;
        }
      }
      req.continue();
    });

    await page.goto(SITE_URL, { waitUntil: 'networkidle0', timeout: 30000 });
    const textAfterBlock = await page.evaluate(() => document.body.innerText);
    const blockedLen = textAfterBlock.trim().length;
    test('Content still accessible after blocking guard scripts', blockedLen > 100, `${blockedLen} chars`);

    // Also test PDF extraction with intercepted guards
    let pdfBlocked = false;
    try {
      await page.pdf({ path: 'bypass_intercepted.pdf', format: 'A4' });
      pdfBlocked = fs.existsSync('bypass_intercepted.pdf') && fs.statSync('bypass_intercepted.pdf').size > 5000;
    } catch { pdfBlocked = false; }
    test('Guard-blocked PDF extraction', pdfBlocked);

    await browser.close();
  } catch (e) {
    test('Interception test', false, e.message);
    if (browser) await browser.close();
  }

  // ------------------------------------------------------------------
  // TEST 4: DevTools detection check
  // ------------------------------------------------------------------
  console.log('\n--- 4. DevTools detection ---');
  try {
    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.goto(SITE_URL, { waitUntil: 'networkidle0', timeout: 30000 });

    const dtChecks = await page.evaluate(() => {
      const checks = {};
      // Check for debugger traps
      const scriptText = document.querySelector('script:last-of-type')?.textContent || '';
      checks.hasDebuggerStatement = scriptText.includes('debugger');
      checks.hasDevtoolsDetect = scriptText.includes('devtools') || scriptText.includes('DevTools');
      // Check Firebug
      checks.fireguard = !!(window.Firebug || (window.console && console.firebug));
      // Check element-id trick
      const scripts = Array.from(document.scripts).map(s => s.textContent).join(' ');
      checks.hasElementIdDetect = scripts.includes('Object.defineProperty') || scripts.includes('__defineGetter__');
      return checks;
    });
    test('debugger trap present', dtChecks.hasDebuggerStatement);
    test('DevTools detection code present', dtChecks.hasDevtoolsDetect);
    test('Element ID detection trick used', dtChecks.hasElementIdDetect);

    await browser.close();
  } catch (e) {
    test('DevTools detection test', false, e.message);
    if (browser) await browser.close();
  }

  // ------------------------------------------------------------------
  // TEST 5: Real user interaction simulation (right-click, F12, Ctrl+P)
  // ------------------------------------------------------------------
  console.log('\n--- 5. User interaction simulation ---');
  try {
    browser = await puppeteer.launch({
      headless: false,  // must be visible to test keyboard events properly
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.goto(SITE_URL, { waitUntil: 'networkidle0', timeout: 30000 });

    // 5a. Simulate right-click
    let contextmenuFired = false;
    await page.evaluate(() => {
      document.addEventListener('contextmenu', () => { window.__ctxfired = true; });
    });
    await page.mouse.click(100, 100, { button: 'right' });
    contextmenuFired = await page.evaluate(() => !!window.__ctxfired);
    test('Right-click event fires', contextmenuFired, 'contextmenu listener was called');

    // 5b. Simulate F12 key
    let f12Fired = false;
    await page.evaluate(() => {
      document.addEventListener('keydown', (e) => {
        if (e.key === 'F12') window.__f12fired = true;
      });
    });
    await page.keyboard.press('F12');
    f12Fired = await page.evaluate(() => !!window.__f12fired);
    test('F12 key event fires', f12Fired, 'keydown listener caught F12');

    // 5c. Simulate Ctrl+Shift+I
    let csiFired = false;
    await page.evaluate(() => {
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'i')) window.__csifired = true;
      });
    });
    await page.keyboard.down('Control');
    await page.keyboard.down('Shift');
    await page.keyboard.press('i');
    await page.keyboard.up('Shift');
    await page.keyboard.up('Control');
    csiFired = await page.evaluate(() => !!window.__csifired);
    test('Ctrl+Shift+I event fires', csiFired, 'keydown listener caught Ctrl+Shift+I');

    // 5d. Simulate Ctrl+P (print)
    let printFired = false;
    await page.evaluate(() => {
      document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 'P')) window.__printfired = true;
      });
    });
    await page.keyboard.down('Control');
    await page.keyboard.press('p');
    await page.keyboard.up('Control');
    printFired = await page.evaluate(() => !!window.__printfired);
    test('Ctrl+P print event fires', printFired, 'keydown listener caught Ctrl+P');

    await browser.close();
  } catch (e) {
    test('User interaction simulation', false, e.message);
    if (browser) await browser.close();
  }

  // ------------------------------------------------------------------
  // SUMMARY
  // ------------------------------------------------------------------
  console.log(`\n${'='.repeat(50)}`);
  console.log(`RESULTS: ${results.pass} passed, ${results.fail} failed, ${results.tests.length} total`);
  console.log(`${'='.repeat(50)}`);

  // Save report
  const report = {
    timestamp: new Date().toISOString(),
    target: SITE_URL,
    summary: { pass: results.pass, fail: results.fail, total: results.tests.length },
    tests: results.tests
  };
  fs.writeFileSync('guardrail-test-report.json', JSON.stringify(report, null, 2));
  console.log(`\nReport saved: guardrail-test-report.json`);

  // Cleanup
  ['bypass_screenshot.png', 'bypass_print.pdf', 'bypass_intercepted.pdf'].forEach(f => {
    if (fs.existsSync(f)) fs.unlinkSync(f);
  });

  process.exit(results.fail > 0 ? 1 : 0);
})();
