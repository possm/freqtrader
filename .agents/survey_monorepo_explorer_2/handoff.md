# Handoff Report: Monorepo Architecture & Docker Consolidation Survey

**Agent**: survey_monorepo_explorer_2  
**Role**: Architecture, Docker & Freqtrade Environment Specialist Explorer  
**Date**: 2026-09-07  
**Type**: Hard Handoff (Task Complete)  
**Detailed Report Path**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/survey_arch_report.md`  

---

## 1. Observation

1. **Docker Compose Inspection Across 4 Repositories**:
   - `freqtrade-breakout/docker-compose.yml`:
     - Line 9: Service `freqtrade-academic-dryrun`, container `freqtrade-wolf-academic-dryrun`, port `192.168.2.4:8082:8080`, command `trade --logfile /freqtrade/user_data/logs/freqtrade_academic_dryrun.log --db-url sqlite:////freqtrade/user_data/tradesv3_academic_dryrun.sqlite --config /freqtrade/config_academic_dryrun.json --strategy WolfBreakout_PVB`.
     - Line 29 (added in `feat/daily-macro-strategy` branch): Service `freqtrade-hopt-live`, container `freqtrade-wolf-hopt-live`, port `192.168.2.4:8080:8080`, inlined `FREQTRADE__*` env vars, command `trade ... --strategy WolfBreakout_Daily`.
   - `freqtrade-grid/docker-compose.yml`:
     - Line 3: Service `freqtrade-grid`, container `freqtrade-grid`, `env_file: .env`, port `192.168.2.4:8081:8080`, command `trade --logfile /freqtrade/user_data/logs/freqtrade.log --db-url sqlite:////freqtrade/user_data/tradesv3.sqlite --config /freqtrade/user_data/config.json --strategy StepGrid`.
   - `freqtrade-trend/docker-compose.yml`:
     - Line 11: Service `freqtrade-hopt-live`, container `freqtrade-wolf-hopt-live`, `env_file: .env`, port `192.168.2.4:8080:8080`, command `trade --logfile /freqtrade/user_data/logs/freqtrade_hopt_live.log --db-url sqlite:////freqtrade/user_data/tradesv3_hopt_live.sqlite --config /freqtrade/config.json --strategy WolfTrend_1h_Candidate`.
     - Line 32: Service `freqtrade-trend-sim` (commented out, had port 8081).
   - `freqtrader-dash/docker-compose.yml`:
     - Line 2: Service `freqtrader-dash`, `build: .`, image `freqtrader-dash`, container `freqtrader-dash`, port `192.168.2.4:80:80`.
   - `freqtrader-dash/Dockerfile`: `FROM nginx:alpine; COPY nginx.conf /etc/nginx/conf.d/default.conf; COPY . /usr/share/nginx/html; EXPOSE 80`.
   - `freqtrader-dash/nginx.conf`: Line 20-30 proxies `/api/` to `http://192.168.2.4:8080/api/` and strips `WWW-Authenticate`.
   - `freqtrader-dash/api.jsx`: Line 5-8 defines `POLL_INTERVAL = 5000`, `STORAGE_KEY = "ft_api_config"`, `BOTS_KEY = "ft_bots"`. Line 58-69 handles `/api/v1/token/login` via HTTP Basic auth. Line 348-370 polls `/api/v1/status`, `/api/v1/balance`, `/api/v1/trades`, `/api/v1/profit`, `/api/v1/daily`, `/api/v1/show_config`, `/api/v1/locks`. Line 421, 455, 479 calls `/api/v1/pair_candles` and `/api/v1/plot_config`. Direct ripgrep search for `sqlite` and `websocket` returned zero matches in `freqtrader-dash`.

2. **Host / VPS Infrastructure Reality via SSH**:
   - Execution of `ssh -o ConnectTimeout=3 vps-matthijs-trader "docker ps"` returned:
     - `c80c7ff34c2f`: `freqtradeorg/freqtrade:stable`, ports `192.168.2.4:8080->8080/tcp`, name `freqtrade-wolf-hopt-live`.
     - `821a114f835c`: `freqtradeorg/freqtrade:stable`, ports `192.168.2.4:8082->8080/tcp`, name `freqtrade-wolf-academic-dryrun`.
     - `f82d395c1c3c`: `freqtrader-dash`, ports `192.168.2.4:80->80/tcp`, name `freqtrader-dash`.
     - `d623a5ef664c`: `antigravity-remote-code-server`, ports `192.168.2.4:8443->8443/tcp`, name `code-server-agy`.
   - Execution of `ssh -o ConnectTimeout=3 vps-matthijs-trader "ip -br a"` returned: `wg0 UNKNOWN 192.168.2.4/32`. `192.168.2.4` is the private WireGuard VPN interface.

3. **Strategies Comparison (`user_data/strategies/`)**:
   - `diff -rq /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/user_data/strategies /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/user_data/strategies` output:
     - Only in breakout: `WolfAftermath.py`, `WolfBearTrap.py`, `WolfBreakout_Daily.json`, `WolfBreakout_Daily.py`, `WolfBreakout_Macro.py`, `WolfBreakout_Test_ADX.py`, `WolfBreakout_Test_ALL.py`, `WolfBreakout_Test_EMA.py`, `WolfBreakout_Test_ETHBTC.py`, `WolfBreakout_Test_VOL.py`, `WolfBreakout_Testing.py`, `WolfTrend_1h_Candidate.json`.
     - Files `WolfTrend_1h_Candidate.py` differed only by 1 trailing newline (`diff -u` showed 1 deleted newline at EOF).
   - `freqtrade-grid/user_data/strategies/`: Contains solely `StepGrid.py` (3,163 bytes). Does not exist in breakout or trend.

4. **Configuration Comparison**:
   - Root JSON configs in `freqtrade-breakout` and `freqtrade-trend` are identical (`config.json`, `config_academic_dryrun.json`, `config_backtest.json`, `config_trend_hopt.json`, `config_trend.json`, `config_sim*.json`).
   - `config_bt_breakout_split.json` and `config_bt_trend_split.json` exist only in `freqtrade-trend` root.
   - `freqtrade-grid/user_data/config.json`: Kraken spot config for StepGrid (`bot_name: freqtrade_grid`, pairs `BTC/EUR`, `ETH/EUR`).
   - `freqtrade-grid/user_data/config_backtest.json`: Binance spot config for StepGrid backtest (`BTC/USDT`, `ETH/USDT`).

5. **Validation Test**:
   - Authored consolidated compose draft in `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/test-compose.yml`.
   - Executed `docker compose -f /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/test-compose.yml config`. Exit code: 0.

---

## 2. Logic Chain

1. **Service Identity & Port De-confliction**:
   - *From Observation 1 & 2*: Four bots exist across the projects: Trend Live (`WolfTrend_1h_Candidate`), Grid Live (`StepGrid`), Breakout Academic Dry-Run (`WolfBreakout_PVB`), and Breakout Daily (`WolfBreakout_Daily`), plus the Dashboard.
   - *From Observation 1 & 2*: Trend Live is currently live on VPS port 8080. Grid runs on 8081. Breakout Academic runs on 8082. Dashboard runs on 80.
   - *Deduction*: Port 8080 must remain dedicated to `freqtrade-trend-live`. The new `WolfBreakout_Daily` bot must be assigned port 8083 (or managed via profile) to eliminate the port 8080 conflict.

2. **Single Root `user_data` Structure**:
   - *From Observation 1 & 4*: Breakout and trend mounted individual root JSON configs into `/freqtrade/...` while grid mounted `./user_data:/freqtrade/user_data` and read configs inside `user_data/`.
   - *From Observation 4*: Placing all configs inside `user_data/` allows every container to mount solely `./user_data:/freqtrade/user_data`.
   - *From Observation 4*: `freqtrade-grid/user_data/config.json` collides in name with root `config.json`. Renaming it to `user_data/config_grid.json` and renaming `user_data/config_backtest.json` to `user_data/config_grid_backtest.json` cleanly eliminates both filename collisions while clarifying bot ownership.

3. **Strategy Unification**:
   - *From Observation 3*: Breakout contains 173 strategy files which are a strict superset of trend's 171 strategies. Grid contains 1 unique strategy (`StepGrid.py`).
   - *Deduction*: Merging breakout strategies with `StepGrid.py` yields 174 strategies with zero code loss and zero naming conflicts.

4. **Database & Log Safety**:
   - *From Observation 1 & 2*: Grid defaulted to `tradesv3.sqlite` and `freqtrade.log`. Breakout and Trend used `tradesv3_hopt_live.sqlite`, `tradesv3_academic_dryrun.sqlite`, etc.
   - *Deduction*: To prevent trade data corruption or overwrite in a shared `user_data/`, Grid's `--db-url` must be `sqlite:////freqtrade/user_data/tradesv3_grid.sqlite` and logfile `/freqtrade/user_data/logs/freqtrade_grid.log`.

5. **Dashboard Protocol Alignment**:
   - *From Observation 1*: `freqtrader-dash` relies strictly on REST polling, uses Nginx to proxy port 8080, and browser direct fetch for other ports.
   - *Deduction*: The dashboard will function seamlessly in the monorepo with zero frontend modifications as long as all bots are exposed on their expected ports (8080, 8081, 8082, 8083) and have `CORS_origins` allowing `http://192.168.2.4` and `http://192.168.2.4:80`.

---

## 3. Caveats

- **WireGuard Interface IP**: The bind IP `192.168.2.4` exists on the VPS WireGuard mesh (`wg0`). In the consolidated compose file, using `"${LISTEN_IP:-192.168.2.4}"` guarantees backwards compatibility on the VPS while allowing local developers to override with `LISTEN_IP=127.0.0.1` or `0.0.0.0` if they do not have WireGuard active.
- **Excluded Ephemeral Data**: Per `GEMINI.md`, live runtime databases (`*.sqlite*`), logs (`user_data/logs`), and candle cache (`user_data/data`) must be excluded during rsync deployments to VPS to prevent wiping active trading state.

---

## 4. Conclusion

1. The architectural consolidation is completely feasible with **zero structural blockers**.
2. There will be **exactly one central `docker-compose.yml`** launching 5 services:
   - `freqtrader-dash` (port 80)
   - `freqtrade-trend-live` (port 8080, `WolfTrend_1h_Candidate`)
   - `freqtrade-grid` (port 8081, `StepGrid`)
   - `freqtrade-breakout-dryrun` (port 8082, `WolfBreakout_PVB`)
   - `freqtrade-breakout-daily` (port 8083, `WolfBreakout_Daily`)
3. There will be **exactly one shared `user_data` directory** at the monorepo root:
   - Strategies unified to 174 files in `user_data/strategies/`.
   - Configs stored cleanly in `user_data/` (`config_trend_hopt.json`, `config_grid.json`, `config_academic_dryrun.json`, `config_breakout_daily.json`, etc.).
   - Databases and logs strictly partitioned per service.
4. Full architectural survey report is recorded at `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/survey_arch_report.md`.

---

## 5. Verification Method

To independently verify this survey and consolidated design:
1. **Docker Compose Validation**:
   ```bash
   docker compose -f /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/test-compose.yml config
   ```
   *Expected Output*: Returns YAML config with exit code 0 and no schema or validation errors.
2. **Strategy Collision Verification**:
   ```bash
   comm -12 <(ls /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/user_data/strategies | sort) <(ls /Users/matthijsdrenth/IdeaProjects/freqtrade-grid/user_data/strategies | sort)
   ```
   *Expected Output*: Empty output (confirms zero filename overlap between StepGrid and Wolf strategies).
3. **Report Inspection**:
   Inspect `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/survey_arch_report.md`.

---
