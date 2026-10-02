# freqtrader-dash

Lightweight web dashboard for one or more [Freqtrade](https://www.freqtrade.io/)
bots. Multi-bot login, live trades, performance metrics, per-pair signal
inspection.

## What it is

- **Vite React 18 app** — built with ES modules and a standard Node toolchain.
- **Reads from Freqtrade's REST API** (`/api/v1/...`) — credentials live in
  the browser's localStorage; the JWT in sessionStorage.
- **Navigation & Deep Linking** — Integrates seamlessly with browser history, allowing the use of Back/Forward buttons and deep-linking to specific tabs, charts, or trades (e.g., `/#chart?pair=BTC/USDT`).

## Files

| File | Purpose |
|------|---------|
| `index.html` | Entry point — loads the compiled Vite bundle |
| `app.jsx` | App shell — login screen, sidebar, top header, tab routing, polling |
| `api.jsx` | REST client + `useFreqtradeData()` hook |
| `views.jsx` | Page-level components (Overview, Trades, Performance, Locks, Signals) |
| `components.jsx` | Reusable UI (cards, buttons, charts, formatters) |
| `nginx.conf` | Nginx config (serves static assets with aggressive caching) |
| `Dockerfile` | Multi-stage build (`node:alpine` for build, `nginx:alpine` to serve) |
| `docker-compose.yml` | Single service binding to host port 80 |

## Pages

- **Dashboard** — open positions, P&L, equity curve, daily bars
- **Signals** — per-pair view of which entry conditions are currently met,
  per strategy. Add new entries to `STRATEGY_SIGNALS` in `views.jsx`.
- **Trades** — sortable trade history with filters
- **Performance** — strategy stats, best/worst, win rate, Sharpe
- **Pair locks** — currently blocked pairs from protections

## Deploy

Code edits must be explicitly deployed to the VPS and rebuilt:

```bash
docker compose build freqtrader-dash
docker compose up -d freqtrader-dash
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
