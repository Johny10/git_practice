#!/usr/bin/env node
/**
 * Eurostar Snap availability check.
 *
 * Loads the Snap search page for a given date in a real browser, records every
 * JSON response the page fetches, and dumps the rendered result area. Snap is a
 * client-rendered SPA whose markup changes without notice, so this script does
 * not try to be the final judge of availability: it gathers evidence
 * (API payloads + visible text + a screenshot) and reports a best-effort
 * verdict alongside it. The caller decides what to do with an "unknown".
 *
 * Usage:
 *   node check.js --date 2026-09-13 [--origin 8727100] [--destination 7015400]
 *                 [--adults 1] [--out ./run] [--timeout 60000]
 *
 * Exit codes: 0 = check completed (see verdict in JSON), 1 = check failed.
 */

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

function parseArgs(argv) {
  const opts = {
    date: null,
    origin: '8727100',
    destination: '7015400',
    adults: '1',
    out: null,
    timeout: 60000,
    locale: 'uk-en',
    url: null, // override the built URL; used by the test fixture
  };
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith('--')) continue;
    const eq = arg.indexOf('=');
    const key = (eq === -1 ? arg.slice(2) : arg.slice(2, eq)).replace(/-/g, '');
    const value = eq === -1 ? argv[++i] : arg.slice(eq + 1);
    if (key in opts) opts[key] = key === 'timeout' ? Number(value) : value;
  }
  if (!opts.date || !/^\d{4}-\d{2}-\d{2}$/.test(opts.date)) {
    throw new Error('--date is required, in YYYY-MM-DD form');
  }
  if (!opts.out) opts.out = path.join(process.cwd(), 'runs', opts.date);
  return opts;
}

function searchUrl(o) {
  if (o.url) return o.url;
  const params = new URLSearchParams({
    adult: o.adults,
    origin: o.origin,
    destination: o.destination,
    outbound: o.date,
  });
  return `https://snap.eurostar.com/${o.locale}/search?${params}`;
}

// Words Snap uses when a date has nothing on offer. Matched against the
// page's visible text, lowercased.
const SOLD_OUT_MARKERS = [
  'no trains available',
  'no available',
  'sold out',
  'fully booked',
  'nothing available',
  'no snap tickets',
  'try another date',
  'no results',
];

// A departure slot looks like "07:06" / "7:06am" next to a price.
const SLOT_RE = /\b([01]?\d|2[0-3])[:.][0-5]\d\s*(am|pm)?\b/gi;
const PRICE_RE = /(?:£|€)\s?\d+(?:[.,]\d{2})?/g;

async function run(opts) {
  fs.mkdirSync(opts.out, { recursive: true });
  const url = searchUrl(opts);
  const apiHits = [];

  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH || undefined,
  });
  const context = await browser.newContext({
    locale: 'en-GB',
    timezoneId: 'Europe/London',
    viewport: { width: 1280, height: 1600 },
  });
  const page = await context.newPage();

  page.on('response', async (response) => {
    const req = response.request();
    if (req.resourceType() !== 'xhr' && req.resourceType() !== 'fetch') return;
    const ct = (response.headers()['content-type'] || '');
    if (!ct.includes('json')) return;
    try {
      const body = await response.text();
      apiHits.push({
        url: response.url(),
        method: req.method(),
        status: response.status(),
        // Cap each payload so one chatty endpoint cannot swamp the report.
        body: body.length > 200000 ? body.slice(0, 200000) + '…[truncated]' : body,
      });
    } catch {
      /* body already consumed or the request was aborted; not worth failing over */
    }
  });

  const result = {
    checkedAt: new Date().toISOString(),
    date: opts.date,
    origin: opts.origin,
    destination: opts.destination,
    adults: Number(opts.adults),
    url,
    verdict: 'unknown',
    slots: [],
    prices: [],
    soldOutMarkers: [],
    error: null,
    artifacts: {},
  };

  try {
    const response = await page.goto(url, {
      waitUntil: 'domcontentloaded',
      timeout: opts.timeout,
    });
    result.httpStatus = response ? response.status() : null;

    // The results list arrives over XHR after first paint. networkidle is the
    // honest signal that the SPA has finished; fall back to a fixed settle if
    // the page keeps a socket or poller open.
    await page
      .waitForLoadState('networkidle', { timeout: opts.timeout })
      .catch(() => page.waitForTimeout(8000));

    const text = await page.evaluate(() => document.body.innerText || '');
    const lower = text.toLowerCase();

    result.soldOutMarkers = SOLD_OUT_MARKERS.filter((m) => lower.includes(m));
    result.slots = [...new Set((text.match(SLOT_RE) || []).map((s) => s.trim()))];
    result.prices = [...new Set(text.match(PRICE_RE) || [])];

    // A slot plus a price and no sold-out banner is the only combination we
    // are willing to call available on our own; everything else stays unknown
    // so the caller inspects the evidence rather than trusting a guess.
    if (result.soldOutMarkers.length > 0 && result.prices.length === 0) {
      result.verdict = 'unavailable';
    } else if (result.slots.length > 0 && result.prices.length > 0) {
      result.verdict = 'available';
    } else {
      result.verdict = 'unknown';
    }

    const textPath = path.join(opts.out, 'page.txt');
    const shotPath = path.join(opts.out, 'page.png');
    const htmlPath = path.join(opts.out, 'page.html');
    fs.writeFileSync(textPath, text);
    fs.writeFileSync(htmlPath, await page.content());
    await page.screenshot({ path: shotPath, fullPage: true });
    result.artifacts = { text: textPath, html: htmlPath, screenshot: shotPath };
    result.pageText = text.length > 20000 ? text.slice(0, 20000) + '…[truncated]' : text;
  } catch (err) {
    result.verdict = 'error';
    result.error = String(err && err.message ? err.message : err);
  } finally {
    await browser.close().catch(() => {});
  }

  result.apiHits = apiHits;
  const jsonPath = path.join(opts.out, 'result.json');
  fs.writeFileSync(jsonPath, JSON.stringify(result, null, 2));
  result.artifacts.json = jsonPath;
  return result;
}

Promise.resolve()
  .then(() => run(parseArgs(process.argv)))
  .then((result) => {
    const brief = { ...result };
    delete brief.apiHits;
    delete brief.pageText;
    console.log(JSON.stringify(brief, null, 2));
    console.log(`\nFull evidence (API payloads, page text): ${result.artifacts.json}`);
    process.exit(result.verdict === 'error' ? 1 : 0);
  })
  .catch((err) => {
    console.error(String(err && err.stack ? err.stack : err));
    process.exit(1);
  });
