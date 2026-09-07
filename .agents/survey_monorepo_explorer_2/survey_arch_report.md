# Monorepo Architectural Survey & Consolidation Design Report

**Author**: survey_monorepo_explorer_2 (Architecture, Docker & Freqtrade Environment Specialist)  
**Date**: 2026-09-07  
**Target Monorepo**: `~/IdeaProjects/freqtrade-monorepo`  
**Source Repositories**:
1. `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout`
2. `/Users/matthijsdrenth/IdeaProjects/freqtrade-grid`
3. `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend`
4. `/Users/matthijsdrenth/IdeaProjects/freqtrader-dash`

---

## 1. Executive Summary

This survey provides a complete architectural blueprint for consolidating four separate Freqtrade and dashboard repositories into a unified monorepo. 

Key findings:
1. **Docker Services**: Currently, four distinct services operate across the repositories:
   - **Trend Live Bot** (`WolfTrend_1h_Candidate` on Kraken Spot, port 8080)
   - **Grid Live Bot** (`StepGrid` on Kraken Spot, port 8081)
   - **Breakout Academic Dry-Run Bot** (`WolfBreakout_PVB` on Kraken Spot, port 8082)
   - **Breakout Daily Bot** (`WolfBreakout_Daily` newly developed macro breakout bot, port 8083)
   - **Dashboard** (`freqtrader-dash` Nginx + React 18, port 80)
2. **Dashboard Communication**: `freqtrader-dash` is an in-browser React application served via Nginx. It communicates **strictly via HTTP REST API polling** (`/api/v1/...` every 5 seconds) using JWT Bearer authentication. It **does not** touch SQLite databases directly and **does not** use WebSockets. Nginx proxies `/api/` to port 8080 by default; other bots (8081, 8082, 8083) are polled directly by the browser via CORS.
3. **Strategy Unification**: The 173 strategies in `freqtrade-breakout` are a strict superset of `freqtrade-trend` (171 strategies, identical code modulo 1 newline). Adding `StepGrid.py` from `freqtrade-grid` creates a unified library of **174 strategies with zero code collisions**.
4. **Configuration Unification**: In breakout/trend, primary configs were stored at repository root and bind-mounted individually. In grid, configs were inside `user_data/`. Placing all configurations into a single shared `user_data/` eliminates individual file bind-mounts. Renaming `freqtrade-grid/user_data/config.json` to `user_data/config_grid.json` resolves the only configuration naming collision.
5. **Database & Log Isolation**: In `freqtrade-grid`, the SQLite database defaulted to `tradesv3.sqlite`, which collided with the legacy `tradesv3.sqlite` from the Wolf bots. In the consolidated architecture, every bot is given an isolated database URL (`tradesv3_hopt_live.sqlite`, `tradesv3_grid.sqlite`, `tradesv3_academic_dryrun.sqlite`, `tradesv3_breakout_daily.sqlite`) and isolated log file.
6. **Verification**: A consolidated `docker-compose.yml` was generated and validated using `docker compose config`, passing with exit code 0.

---

## 2. Inventory & Analysis of Docker Setups

### 2.1 Host & VPS Networking Reality
All existing compose files bind ports to `192.168.2.4:<port>:<container_port>`.
- Live inspection via SSH (`vps-matthijs-trader`) confirmed that `192.168.2.4` is the `wg0` WireGuard VPN interface on the host VPS (`5.181.134.210`).
- Binding to `192.168.2.4` is an intentional security design: services are strictly accessible within the private WireGuard mesh and never exposed to the public internet.
- On the VPS, live verification (`docker ps`) showed:
  - `freqtrade-wolf-hopt-live` running on `192.168.2.4:8080->8080`
  - `freqtrade-wolf-academic-dryrun` running on `192.168.2.4:8082->8080`
  - `freqtrader-dash` running on `192.168.2.4:80->80`
  - `code-server-agy` running on `192.168.2.4:8443->8443`

### 2.2 Repository Docker Details

#### Repository: `freqtrade-breakout`
- **File**: `docker-compose.yml`
- **Services**:
  1. `freqtrade-academic-dryrun`:
     - Container: `freqtrade-wolf-academic-dryrun`
     - Image: `freqtradeorg/freqtrade:stable`
     - Restart: `unless-stopped`
     - Ports: `"192.168.2.4:8082:8080"`
     - Volumes: `./user_data:/freqtrade/user_data`, `./config_academic_dryrun.json:/freqtrade/config_academic_dryrun.json`
     - Command: `trade --logfile /freqtrade/user_data/logs/freqtrade_academic_dryrun.log --db-url sqlite:////freqtrade/user_data/tradesv3_academic_dryrun.sqlite --config /freqtrade/config_academic_dryrun.json --strategy WolfBreakout_PVB`
  2. `freqtrade-hopt-live` (modified locally in branch `feat/daily-macro-strategy`):
     - Container: `freqtrade-wolf-hopt-live`
     - Image: `freqtradeorg/freqtrade:stable`
     - Restart: `unless-stopped`
     - Ports: `"192.168.2.4:8080:8080"`
     - Volumes: `./user_data:/freqtrade/user_data`, `./config_trend_hopt.json:/freqtrade/config.json`
     - Environment: Inlined exchange credentials and api_server JWT tokens.
     - Command: `trade --logfile /freqtrade/user_data/logs/freqtrade_hopt_live.log --db-url sqlite:////freqtrade/user_data/tradesv3_hopt_live.sqlite --config /freqtrade/config.json --strategy WolfBreakout_Daily`

#### Repository: `freqtrade-grid`
- **File**: `docker-compose.yml`
- **Services**:
  1. `freqtrade-grid`:
     - Container: `freqtrade-grid`
     - Image: `freqtradeorg/freqtrade:stable`
     - Restart: `unless-stopped`
     - Env File: `.env`
     - DNS: `8.8.8.8`, `1.1.1.1`
     - Ports: `"192.168.2.4:8081:8080"`
     - Volumes: `./user_data:/freqtrade/user_data`
     - Command: `trade --logfile /freqtrade/user_data/logs/freqtrade.log --db-url sqlite:////freqtrade/user_data/tradesv3.sqlite --config /freqtrade/user_data/config.json --strategy StepGrid`

#### Repository: `freqtrade-trend`
- **File**: `docker-compose.yml`
- **Services**:
  1. `freqtrade-hopt-live`:
     - Container: `freqtrade-wolf-hopt-live`
     - Image: `freqtradeorg/freqtrade:stable`
     - Restart: `unless-stopped`
     - Env File: `.env`
     - Ports: `"192.168.2.4:8080:8080"`
     - Volumes: `./user_data:/freqtrade/user_data`, `./config_trend_hopt.json:/freqtrade/config.json`
     - Command: `trade --logfile /freqtrade/user_data/logs/freqtrade_hopt_live.log --db-url sqlite:////freqtrade/user_data/tradesv3_hopt_live.sqlite --config /freqtrade/config.json --strategy WolfTrend_1h_Candidate`
  2. `freqtrade-trend-sim` (commented out):
     - Container: `freqtrade-wolf-trend-sim`
     - Ports: `"192.168.2.4:8081:8080"` (historical port collision with grid!)
     - Command: `trade ... --strategy WolfTrend_EMA`

#### Repository: `freqtrader-dash`
- **File**: `docker-compose.yml`, `Dockerfile`, `nginx.conf`
- **Services**:
  1. `freqtrader-dash`:
     - Container: `freqtrader-dash`
     - Build: `.`
     - Base Image: `nginx:alpine`
     - Restart: `unless-stopped`
     - Ports: `"192.168.2.4:80:80"`

---

## 3. Dashboard Communication Architecture

`freqtrader-dash` is built as an in-browser React application without any Node.js runtime or backend server.

### 3.1 Communication Flow
```
+-------------------------------------------------------------+
|                 Browser (Client Machine)                    |
|  - React 18 + Babel-standalone                              |
|  - Manages active bot in localStorage (ft_bots)             |
|  - Manages JWT access tokens in sessionStorage (ft_token)   |
|  - Polls /api/v1/* endpoints every 5000ms                   |
+------------------------------+------------------------------+
                               |
        +----------------------+----------------------+
        | HTTP (default)                              | HTTP (multi-bot)
        v                                             v
+-----------------------+                    +-----------------------+
|  nginx (port 80)      |                    |  Direct Bot Port      |
|  proxy_pass:          |                    |  (:8081, :8082, :8083)|
|  http://192.168.2.4:  |                    |  Freqtrade REST API   |
|  8080/api/            |                    |  (CORS validated)     |
+-----------+-----------+                    +-----------+-----------+
            |                                            |
            +--------------------+-----------------------+
                                 |
                                 v
                     +-----------------------+
                     |  Freqtrade Bots       |
                     |  (Container port 8080)|
                     |  - REST API Server    |
                     |  - Whitelist, Trades  |
                     |  - Plot config        |
                     +-----------------------+
```

### 3.2 Key Technical Mechanisms
1. **REST Endpoints Polled**:
   - `/api/v1/ping`
   - `/api/v1/status` (open trades, profit, rates)
   - `/api/v1/balance` (wallet balances)
   - `/api/v1/trades?limit=500` (closed trade history)
   - `/api/v1/profit` (aggregate P&L statistics)
   - `/api/v1/daily?timescale=30` (daily P&L bars)
   - `/api/v1/show_config` (bot configuration, run mode, strategy)
   - `/api/v1/locks` (protection locks)
   - `/api/v1/pair_candles` & `/api/v1/plot_config` (indicator signals)
2. **Authentication**:
   - Initial login via HTTP Basic Auth: `POST /api/v1/token/login` with `Authorization: Basic <base64>`
   - Responses yield `access_token` and `refresh_token`.
   - Subsequent calls use Bearer auth: `Authorization: Bearer <token>`.
   - Automatic token renewal occurs via `POST /api/v1/token/refresh`.
3. **CORS Handling**:
   - When connecting through port 80, Nginx proxies `/api/` to port 8080 and strips the `WWW-Authenticate: Basic` header so the browser does not show its native prompt.
   - For multi-bot connections (ports 8081, 8082, 8083), the browser fetches directly from `http://192.168.2.4:<port>/api/v1/...`.
   - Freqtrade bot configs must include `CORS_origins` allowing `http://192.168.2.4` and `http://192.168.2.4:80`.
4. **Database & WebSocket Confirmation**:
   - **Zero** SQLite database interaction in dashboard code.
   - **Zero** WebSocket connection code in dashboard client (pure 5s polling loop).

---

## 4. `user_data` Structure & Inventory

### 4.1 Strategies Inventory (`user_data/strategies/`)
- **Total unique strategies**: 174
- **`freqtrade-grid`**: 1 strategy (`StepGrid.py`).
- **`freqtrade-trend`**: 171 strategies (Wolf family: `WolfTrend_*`, `WolfMR_*`, `WolfBounce_*`, `WolfCustomSwing_*`, `WolfQuantEdge_*`, etc.).
- **`freqtrade-breakout`**: 173 strategies (contains all 171 trend strategies + 2 new strategies: `WolfAftermath.py`, `WolfBearTrap.py`, and test variants).
- **Strategy Parameter JSON files**:
  - `WolfBreakout_Daily.json`
  - `WolfBreakout_PVB.json`
  - `WolfMeanReversion_Hyper.json`
  - `WolfTrend_1h_Candidate.json`
  - `WolfTrend_EMA_hopt.json`
- **Resolution**: Merging `user_data/strategies/` is completely collision-free. Taking the superset from `freqtrade-breakout` and adding `StepGrid.py` yields all 174 strategies.

### 4.2 Configuration Files Inventory
Configurations across the repositories are categorized as:
1. **Primary Active Bot Configs**:
   - `config_trend_hopt.json`: Trend Live Bot (Kraken EUR, 12 pairs, tight stoploss, exit webhook)
   - `config_academic_dryrun.json`: Academic Breakout Bot (Kraken EUR, 18 pairs, Parkinson Volatility)
   - `config.json` (in `freqtrade-grid/user_data/`): Grid Live Bot (Kraken EUR, BTC/EUR + ETH/EUR, StepGrid)
   - `config_breakout_daily.json`: Daily Macro Breakout Bot (`WolfBreakout_Daily`)
2. **Backtest & Simulation Configs**:
   - `config_backtest.json`: Kraken 18-pair backtest configuration
   - `config_grid_backtest.json` (migrated from `freqtrade-grid/user_data/config_backtest.json`): Binance USDT grid backtest
   - `config_bt_trend_split.json`, `config_bt_breakout_split.json`: Trend/Breakout validation split configs
   - `config_sim2204039.json`, `config_sim_no_sl.json`, `config_sim_tight.json`, `config_trend.json`
3. **Binance & Research Configs** (already located in `user_data/`):
   - `config_binance.json`, `config_binance_15m.json`, `config_binance_1h.json`, `config_binance_4h.json`, `config_binance_clean.json`, `config_binance_fixed.json`, `config_binance_4h_10p_trend.json`, `config_binance_4h_17p.json`
   - `config_4h_all.json`, `config_4h_best.json`, `config_4h_clean.json`, `config_4h_no_aave.json`, `config_4h_top5.json`, `config_4h_winners.json`
   - `config_download.json`, `config_futures_ls.json`, `config_runner.json`, `config_train_top8.json`, `config_train_top10.json`, `config_wave.json`

### 4.3 Databases Inventory
- Active Live Trend Database: `tradesv3_hopt_live.sqlite`
- Active Dry-Run Academic Database: `tradesv3_academic_dryrun.sqlite`
- Grid Database: `tradesv3_grid.sqlite` (renamed from `tradesv3.sqlite` to avoid collisions)
- Daily Breakout Database: `tradesv3_breakout_daily.sqlite`
- Historical research databases: `tradesv3_mr.sqlite`, `tradesv3_qe.sqlite`, `tradesv3_trend.sqlite`, `tradesv3_trend_hopt.sqlite`

---

## 5. Conflict Resolution Matrix

| Conflict Category | Conflicting Items | Nature of Conflict | Resolution in Consolidated Monorepo |
|-------------------|-------------------|-------------------|--------------------------------------|
| **Config Filename** | `freqtrade-grid/user_data/config.json` vs root `config.json` | Both use `config.json` | Rename grid config to `user_data/config_grid.json`. Keep root `config.json` as `user_data/config.json` (or `config_swing.json`). |
| **Config Filename** | `freqtrade-grid/user_data/config_backtest.json` vs root `config_backtest.json` | Same filename, different contents (Binance pairs vs Kraken pairs) | Rename grid backtest config to `user_data/config_grid_backtest.json`. Keep Kraken backtest config as `user_data/config_backtest.json`. |
| **Port Binding** | `freqtrade-trend` (8080) vs `freqtrade-breakout` (8080) | Both configured `freqtrade-hopt-live` on 8080 | Trend live remains on `8080`. Daily breakout bot assigned to dedicated port `8083`. |
| **Port Binding** | `freqtrade-grid` (8081) vs `freqtrade-trend-sim` (8081) | Port 8081 overlap | `freqtrade-trend-sim` was commented out. Grid bot retains `8081`. Any future sim bot uses `8084+`. |
| **Database File** | `freqtrade-grid/user_data/tradesv3.sqlite` vs Wolf `tradesv3.sqlite` | Same filename | Configure grid bot `--db-url` to `sqlite:////freqtrade/user_data/tradesv3_grid.sqlite`. |
| **Log File** | `freqtrade-grid` (`freqtrade.log`) vs default logs | Generic log name overwrites | Configure grid bot `--logfile` to `/freqtrade/user_data/logs/freqtrade_grid.log`. |
| **Config Location** | Root JSON configs vs `user_data/` | Inconsistent volume mounts across repos | Relocate all JSON configs into `user_data/`. All bot containers mount ONLY `./user_data:/freqtrade/user_data`. |
| **Environment Vars** | Inlined credentials in compose vs duplicate `.env` files | Security exposure and drift | Consolidate into a single root `.env` referenced via `env_file: .env` for each bot service. |

---

## 6. Target Consolidated Monorepo Architecture

### 6.1 Directory Tree
```
freqtrade-monorepo/
├── .agents/                      # Preserved AI agent memory and governance metadata
├── .env                          # Central secrets (EXCHANGE_KEY, JWT tokens, etc.)
├── .env.example                  # Template secrets file
├── .gitignore                    # Standard gitignore (ignoring .env, data, logs, sqlite)
├── GEMINI.md                     # Consolidated VPS deployment & workflow instructions
├── README.md                     # Monorepo architecture, bots overview, and operations guide
├── docker-compose.yml            # Single central docker-compose running all bots + dashboard
├── freqtrader-dash/              # Dashboard application
│   ├── Dockerfile                # nginx:alpine container build
│   ├── nginx.conf                # Nginx proxy configuration
│   ├── index.html                # App entry point
│   ├── app.jsx                   # Shell, bot picker, auth
│   ├── api.jsx                   # REST API client & polling hook
│   ├── views.jsx                 # UI pages (Dashboard, Signals, Trades, Performance)
│   ├── components.jsx            # UI component library
│   └── package.json
├── tests/                        # Centralized test suite
│   ├── __init__.py
│   ├── test_adversarial_hvrspb.py
│   ├── test_adversarial_pvb.py
│   ├── test_boundary_sensitivity.py
│   ├── test_lookahead_and_execution_hvrspb.py
│   ├── test_wolfbreakout_hvrspb.py
│   └── test_wolfbreakout_pvb.py
├── reports/                      # Architectural and quant research reports
└── user_data/                    # Exactly ONE shared Freqtrade user_data directory
    ├── config.json               # Baseline custom swing config
    ├── config_trend_hopt.json    # Trend Live Bot configuration (Port 8080)
    ├── config_grid.json          # Grid Live Bot configuration (Port 8081)
    ├── config_academic_dryrun.json # Academic Breakout Bot configuration (Port 8082)
    ├── config_breakout_daily.json # Daily Macro Breakout Bot configuration (Port 8083)
    ├── config_backtest.json      # Kraken backtest config
    ├── config_grid_backtest.json # Binance grid backtest config
    ├── config_binance_*.json     # Binance research configs
    ├── config_4h_*.json          # 4h time-frame research configs
    ├── strategies/               # All 174 unified Python strategies + parameter JSONs
    │   ├── StepGrid.py           # Grid strategy
    │   ├── WolfTrend_1h_Candidate.py # Trend live strategy
    │   ├── WolfBreakout_PVB.py   # Breakout academic strategy
    │   ├── WolfBreakout_Daily.py # Breakout daily macro strategy
    │   └── ... (all 170 other Wolf strategies)
    ├── data/                     # Market historical data (kraken/, binance/)
    ├── logs/                     # Bot execution logs
    └── backtest_results/         # Backtest outputs and metadata
```

### 6.2 Consolidated `docker-compose.yml` Specification
This specification has been validated and tested:

```yaml
services:
  # ─────────────────────────────────────────────────────────────────────────────
  # Dashboard (Port 80) — Web UI for multi-bot monitoring
  # ─────────────────────────────────────────────────────────────────────────────
  freqtrader-dash:
    build:
      context: ./freqtrader-dash
      dockerfile: Dockerfile
    image: freqtrader-dash
    container_name: freqtrader-dash
    restart: unless-stopped
    ports:
      - "${LISTEN_IP:-192.168.2.4}:80:80"
    networks:
      - freqtrade-net

  # ─────────────────────────────────────────────────────────────────────────────
  # 8080 — LIVE: WolfTrend_1h_Candidate (Trend Following Bot on Kraken Spot)
  # ─────────────────────────────────────────────────────────────────────────────
  freqtrade-trend-live:
    image: freqtradeorg/freqtrade:stable
    restart: unless-stopped
    container_name: freqtrade-wolf-hopt-live
    env_file:
      - .env
    volumes:
      - "./user_data:/freqtrade/user_data"
    ports:
      - "${LISTEN_IP:-192.168.2.4}:8080:8080"
    command: >
      trade
      --logfile /freqtrade/user_data/logs/freqtrade_hopt_live.log
      --db-url sqlite:////freqtrade/user_data/tradesv3_hopt_live.sqlite
      --config /freqtrade/user_data/config_trend_hopt.json
      --strategy WolfTrend_1h_Candidate
    networks:
      - freqtrade-net

  # ─────────────────────────────────────────────────────────────────────────────
  # 8081 — LIVE: StepGrid (Grid Trading Bot on Kraken Spot)
  # ─────────────────────────────────────────────────────────────────────────────
  freqtrade-grid:
    image: freqtradeorg/freqtrade:stable
    restart: unless-stopped
    container_name: freqtrade-grid
    env_file:
      - .env
    dns:
      - 8.8.8.8
      - 1.1.1.1
    volumes:
      - "./user_data:/freqtrade/user_data"
    ports:
      - "${LISTEN_IP:-192.168.2.4}:8081:8080"
    command: >
      trade
      --logfile /freqtrade/user_data/logs/freqtrade_grid.log
      --db-url sqlite:////freqtrade/user_data/tradesv3_grid.sqlite
      --config /freqtrade/user_data/config_grid.json
      --strategy StepGrid
    networks:
      - freqtrade-net

  # ─────────────────────────────────────────────────────────────────────────────
  # 8082 — DRY-RUN: WolfBreakout_PVB (Academic Parkinson Volatility Breakout)
  # ─────────────────────────────────────────────────────────────────────────────
  freqtrade-breakout-dryrun:
    image: freqtradeorg/freqtrade:stable
    restart: unless-stopped
    container_name: freqtrade-wolf-academic-dryrun
    env_file:
      - .env
    volumes:
      - "./user_data:/freqtrade/user_data"
    ports:
      - "${LISTEN_IP:-192.168.2.4}:8082:8080"
    command: >
      trade
      --logfile /freqtrade/user_data/logs/freqtrade_academic_dryrun.log
      --db-url sqlite:////freqtrade/user_data/tradesv3_academic_dryrun.sqlite
      --config /freqtrade/user_data/config_academic_dryrun.json
      --strategy WolfBreakout_PVB
    networks:
      - freqtrade-net

  # ─────────────────────────────────────────────────────────────────────────────
  # 8083 — LIVE / DRY-RUN: WolfBreakout_Daily (Daily Macro Breakout Bot)
  # ─────────────────────────────────────────────────────────────────────────────
  freqtrade-breakout-daily:
    image: freqtradeorg/freqtrade:stable
    restart: unless-stopped
    container_name: freqtrade-wolf-breakout-daily
    env_file:
      - .env
    volumes:
      - "./user_data:/freqtrade/user_data"
    ports:
      - "${LISTEN_IP:-192.168.2.4}:8083:8080"
    command: >
      trade
      --logfile /freqtrade/user_data/logs/freqtrade_breakout_daily.log
      --db-url sqlite:////freqtrade/user_data/tradesv3_breakout_daily.sqlite
      --config /freqtrade/user_data/config_breakout_daily.json
      --strategy WolfBreakout_Daily
    networks:
      - freqtrade-net

networks:
  freqtrade-net:
    driver: bridge
```

---

## 7. Migration & Consolidation Instructions for Implementers

When executing Milestone 2 (Consolidation):

1. **Strategy Migration**:
   - Copy all files from `freqtrade-breakout/user_data/strategies/` to `user_data/strategies/`.
   - Copy `StepGrid.py` from `freqtrade-grid/user_data/strategies/StepGrid.py` to `user_data/strategies/StepGrid.py`.
2. **Config Migration & Renaming**:
   - Move root configs (`config_trend_hopt.json`, `config_academic_dryrun.json`, `config_backtest.json`, `config.json`, `config_*.json`) into `user_data/`.
   - Copy `config_bt_trend_split.json` and `config_bt_breakout_split.json` from `freqtrade-trend` into `user_data/`.
   - Copy `freqtrade-grid/user_data/config.json` to `user_data/config_grid.json`.
   - Copy `freqtrade-grid/user_data/config_backtest.json` to `user_data/config_grid_backtest.json`.
   - Ensure all `CORS_origins` in configs include `"http://192.168.2.4"` and `"http://192.168.2.4:80"`.
3. **Environment & Secrets**:
   - Create root `.env` merging API keys and secrets from the existing `.env` files.
   - Create `.env.example` with dummy values.
4. **Dashboard Setup**:
   - Place dashboard files in `freqtrader-dash/` at root.
   - Retain `Dockerfile` and `nginx.conf`.
5. **Validation Command**:
   - Run `docker compose config` from monorepo root. It must output the valid configuration with zero errors.

---
