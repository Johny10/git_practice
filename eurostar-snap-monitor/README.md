# Eurostar Snap availability monitor

Checks whether Eurostar Snap has anything on offer for a given date on the
London St Pancras (`8727100`) → Paris Gare du Nord (`7015400`) route, and
gathers enough evidence for a caller to act on the answer.

## Why it reports evidence rather than just a boolean

Snap is a client-rendered SPA with no public API and no stability guarantee on
its markup. A scraper that only returned `true`/`false` would silently start
lying the first time Eurostar renamed a CSS class. So `check.js` drives a real
browser and returns three independent signals:

- **`apiHits`** — every JSON response the page itself fetched. This is the
  most durable signal; it is the data Snap's own UI renders from.
- **`slots` / `prices` / `soldOutMarkers`** — parsed from the rendered text.
- **`page.png` / `page.html` / `page.txt`** — a full snapshot, so a human (or
  the scheduled job) can look at what the page actually said.

`verdict` is a best-effort summary of those, and is deliberately conservative:

| verdict | meaning |
| --- | --- |
| `available` | departure times **and** prices rendered, no sold-out banner |
| `unavailable` | a sold-out banner and no prices |
| `unknown` | neither pattern matched — inspect the evidence, don't assume |
| `error` | navigation or load failed |

Treat `unknown` as "go look", never as "nothing available".

## Usage

```sh
npm install
node check.js --date 2026-09-13
```

Options: `--date` (required, `YYYY-MM-DD`), `--origin`, `--destination`,
`--adults`, `--out`, `--timeout`, `--url` (override the built URL; used by the
test fixture).

Exit code is 0 whenever the check completed — read `verdict` for the outcome —
and 1 only when the check itself failed.

Note that no `outslot` filter is applied, so **all** departure times for the
date are reported, not just the 07:06 slot from the original search link.

## Network requirement

`snap.eurostar.com` must be reachable. In a Claude Code remote environment it
must be on the environment's egress allowlist, or the run fails with a 403
`CONNECT tunnel failed` from the egress proxy and `verdict: "error"`.
