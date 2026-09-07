# freqtrader-dash

Lightweight web dashboard for one or more [Freqtrade](https://www.freqtrade.io/)
bots. Multi-bot login, live trades, performance metrics, per-pair signal
inspection.

## What it is

- **In-browser React 18 app** — no build step. JSX is compiled live in the
  browser by Babel standalone. Just static files served by nginx.
- **Reads from Freqtrade's REST API** (`/api/v1/...`) — credentials live in
  the browser's localStorage; the JWT in sessionStorage.
- Designed to be light enough to deploy as a single nginx container, no
  Node toolchain or build pipeline required.

## Files

| File | Purpose |
|------|---------|
| `index.html` | Entry point — loads React, Babel, and the four JSX files |
| `app.jsx` | App shell — login screen, sidebar, top header, tab routing, polling |
| `api.jsx` | REST client + `useFreqtradeData()` hook |
| `views.jsx` | Page-level components (Overview, Trades, Performance, Locks, Signals) |
| `components.jsx` | Reusable UI (cards, buttons, charts, formatters) |
| `nginx.conf` | Nginx config (just serves the static files) |
| `Dockerfile` | `nginx:alpine` + COPY |
| `docker-compose.yml` | Single service binding to host port 80 |

## Pages

- **Dashboard** — open positions, P&L, equity curve, daily bars
- **Signals** — per-pair view of which entry conditions are currently met,
  per strategy. Add new entries to `STRATEGY_SIGNALS` in `views.jsx`.
- **Trades** — sortable trade history with filters
- **Performance** — strategy stats, best/worst, win rate, Sharpe
- **Pair locks** — currently blocked pairs from protections

## Deploy

```bash
docker compose up -d --build
```

Then navigate to `http://<host>/` and add your Freqtrade bot(s) on the login
screen (URL + freqtrade API username/password). Each bot is stored in
localStorage; switch between them via the dropdown in the top bar.

## Multi-bot

If you have multiple Freqtrade bots (e.g. one per strategy on different ports),
add each one separately. The dashboard remembers them. The Signals page
auto-detects which strategy the active bot is running and shows the right columns
(from `STRATEGY_SIGNALS` in `views.jsx`).

## Adding signals for a new strategy

In `views.jsx`, add an entry to `STRATEGY_SIGNALS` keyed by the strategy class
name. Each signal needs `getValue` and `isFired` callbacks that read columns
from the analyzed dataframe (whatever `populate_indicators` puts in there).
See existing entries for `WolfTrend_EMA`, `WolfMR_4h_btc`, etc.

## Why no build step?

This started as a personal tool. In-browser Babel keeps the deploy story tiny:
edit a `.jsx` file, rsync, restart container. No npm, no bundlers, no source
maps to worry about. If/when complexity outgrows this, Vite would be the next
step.
