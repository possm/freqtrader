# Survey Explorer 2: VPS Infrastructure & Environment Report

- **Author**: Survey Explorer 2 (VPS Infrastructure Explorer)
- **Target Audience**: Project Orchestrator, Data Scientist, Risk Manager, Implementer
- **Date**: 2026-09-04
- **Working Directory**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2`
- **Output Artifact**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2/handoff.md`

---

## 1. Observation

### 1.1 VPS Host Specifications & Network State
- **SSH Connectivity**: Connection verified via `ssh vps-matthijs-trader`.
- **System Information** (from `uname -a` and `whoami`):
  - Hostname / OS: `Linux trader 6.8.0-136-generic #136-Ubuntu SMP PREEMPT_DYNAMIC Wed Jul 1 21:53:05 UTC 2026 x86_64`
  - User: `root`, Home: `/root`
- **Hardware Resources** (from `nproc`, `free -h`, `df -h /`):
  - CPU Cores: `2` vCPUs
  - Memory: `3.8 GiB` total, `1.5 GiB` used, `2.3 GiB` available; Swap: `1.5 GiB` (195 MiB used)
  - Disk Space: `58 GiB` total, `18 GiB` used, `40 GiB` available (31% utilization)
- **Open TCP Ports** (from `ss -tulpn` on `192.168.2.4`):
  - Port `80`: `freqtrader-dash` (Nginx reverse proxy + React dashboard)
  - Port `8080`: `freqtrade-wolf-hopt-live` (Active production bot)
  - Port `8443`: `code-server-agy` (Remote IDE)
  - Ports `8081` and `8082`: Currently UNBOUND and fully available.

### 1.2 Docker & Container Ecosystem
- **Running Containers** (from `docker ps -a`):
  1. `freqtrade-wolf-hopt-live` (`freqtradeorg/freqtrade:stable`):
     - Created: ~5 hours ago, Status: `Up 5 hours`.
     - Bound Ports: `192.168.2.4:8080->8080/tcp`.
     - Compose service name: `freqtrade-hopt-live`.
     - Runtime Environment: Python 3.14, Freqtrade 2026.4, CCXT 4.5.50.
     - Live command:
       ```bash
       trade --logfile /freqtrade/user_data/logs/freqtrade_hopt_live.log \
             --db-url sqlite:////freqtrade/user_data/tradesv3_hopt_live.sqlite \
             --config /freqtrade/config.json \
             --strategy WolfTrend_1h_Candidate
       ```
     - Heartbeat logs (`docker logs --tail=40 freqtrade-wolf-hopt-live`):
       ```text
       2026-09-04 15:23:24,579 - freqtrade.worker - INFO - Bot heartbeat. PID=1, version='2026.4', state='RUNNING'
       2026-09-04 15:24:24,585 - freqtrade.worker - INFO - Bot heartbeat. PID=1, version='2026.4', state='RUNNING'
       ```
     - **CRITICAL NOTE**: This container is in **LIVE TRADING** (`"dry_run": false`) managing real funds on Kraken. It must not be stopped or modified during dry-run deployment.
  2. `freqtrader-dash` (`freqtrader-dash` image):
     - Status: `Up 19 hours`, Port `192.168.2.4:80->80/tcp`.
     - Configuration (`~/freqtrader-dash/nginx.conf`): Proxies `/api/` to `http://192.168.2.4:8080/api/`.
  3. `code-server-agy` (`antigravity-remote-code-server`):
     - Status: `Up 7 days`, Port `192.168.2.4:8443->8443/tcp`.

- **Docker Compose Configuration (`~/freqtrade-wolf/docker-compose.yml`)**:
  - Contains definitions for:
    - `freqtrade-hopt-live`: Active live service on port 8080, mapped to `config_trend_hopt.json`.
    - `freqtrade-trend-sim` (commented out): Service on port 8081, mapped to `config_trend.json`.
    - `freqtrade-qe-sim` (commented out): Service on port 8082, mapped to `config_kraken_dryrun.json`.

### 1.3 Historical Candle Data Inventory (`~/freqtrade-wolf/user_data/data/`)
Two separate exchange directories exist under `~/freqtrade-wolf/user_data/data/`:

1. **Kraken Data (`user_data/data/kraken/`)**:
   - Total files: 93 `.feather` files (OHLCV candles and `-trades.feather` trade files).
   - Pairs present (18 EUR pairs + 8 micro-caps):
     - `AAVE/EUR`, `ADA/EUR`, `ARB/EUR`, `BTC/EUR`, `ETH/EUR`, `FET/EUR`, `HBAR/EUR`, `INJ/EUR`, `KAS/EUR`, `LINK/EUR`, `NEAR/EUR`, `OP/EUR`, `POL/EUR`, `RENDER/EUR`, `SOL/EUR`, `STX/EUR`, `SUI/EUR`, `TIA/EUR`.
     - Micro-caps (1m, 5m only): `APT`, `ATOM`, `AVAX`, `DOGE`, `DOT`, `LTC`, `UNI`, `XRP`.
   - Timeframes: `15m`, `1h`, `4h` (and tick `trades.feather` for slippage audit).
   - Date Coverage:
     - 1h candles: ~2026-03-14 to 2026-05-15 (~800 - 2,100 candles per pair).
     - 4h candles: For `BTC/EUR`, `ETH/EUR`, `LINK/EUR`, `ADA/EUR`, data extends from 2026-04-01 to 2026-08-30 (908 candles). Other pairs end around 2026-05-15.
   - Note: Kraken data history is relatively short (~2 to 5 months) due to Kraken API candle rate limits.

2. **Binance Data (`user_data/data/binance/`)**:
   - Total files: 90 pair/timeframe combinations in `.feather` format.
   - Pairs present (USDT pairs mirroring Kraken whitelist):
     - `AAVE/USDT`, `ADA/USDT`, `ALGO/USDT`, `APT/USDT`, `ARB/USDT`, `ATOM/USDT`, `AVAX/USDT`, `AXS/USDT`, `BCH/USDT`, `BTC/USDT`, `DOGE/USDT`, `DOT/USDT`, `EGLD/USDT`, `ETH/USDT`, `FET/USDT`, `FIL/USDT`, `HBAR/USDT`, `ICP/USDT`, `INJ/USDT`, `LINK/USDT`, `LTC/USDT`, `MANA/USDT`, `NEAR/USDT`, `OP/USDT`, `POL/USDT`, `RENDER/USDT`, `SAND/USDT`, `SEI/USDT`, `SHIB/USDT`, `SOL/USDT`, `STX/USDT`, `SUI/USDT`, `THETA/USDT`, `TIA/USDT`, `TRX/USDT`, `VET/USDT`, `XLM/USDT`, `XRP/USDT`, `XTZ/USDT`.
   - Timeframes: `5m`, `15m`, `1h`, `4h`.
   - Date Coverage:
     - 1h candles: `2021-01-01 00:00:00` to `2026-05-22 06:00:00` (47,201 candles per pair, ~5.4 years).
     - 4h candles: `2021-01-01 00:00:00` to `2026-09-03 08:00:00` (12,429 candles per pair, updated yesterday!).
     - 5m / 15m candles: `2021-01-01` to `2026-05-22`.
   - Script automation: `user_data/scripts/download_data.sh` downloads Binance multi-year data for all Kraken-mirrored pairs plus KAS from Kraken.

### 1.4 Configuration Files & Fee Structure Analysis
- **Configurations on VPS**:
  - `config_trend_hopt.json`: Production live config. `"dry_run": false`, `"stake_amount": 125`, `"stake_currency": "EUR"`, `"max_open_trades": 8`, 15 Kraken pairs, Home Assistant webhook configured.
  - `config_kraken_dryrun.json`: Production-ready dry-run config. `"dry_run": true`, `"dry_run_wallet": 1500`, `"stake_amount": 75`, `"stake_currency": "EUR"`, `"max_open_trades": 10`, 18 Kraken EUR pairs.
  - `user_data/config_binance.json`: Backtest/Hyperopt configuration against Binance USDT data. `"stake_currency": "USDT"`, `"max_open_trades": 8`, 8 trend pairs (`SOL`, `NEAR`, `FET`, `HBAR`, `ADA`, `BTC`, `ETH`, `LINK`).
  - `.env`: Contains `FREQTRADE__EXCHANGE__KEY`, `FREQTRADE__EXCHANGE__SECRET`, and API server JWT/ws tokens.

- **Exchange Fee Verification (CCXT queries inside container)**:
  - **Kraken Spot**:
    - Taker fee: `0.0026` (0.26%) on standard low-tier; entry-tier (<$10k) worst-case is `0.0040` (0.40%).
    - Maker fee: `0.0016` (0.16%).
    - When backtesting with Kraken exchange config without `--fee`, Freqtrade logs:
      `Using fee 0.4000% - worst case fee from exchange (lowest tier)`.
  - **Binance Spot**:
    - Taker fee: `0.0010` (0.10%).
    - Maker fee: `0.0010` (0.10%).
  - **CRITICAL FEE OBSERVATION**: If Hyperopt or Backtesting is executed against Binance data (`config_binance.json`) without an explicit fee flag, Freqtrade uses Binance's low 0.10% fee. To satisfy Requirement R2 (explicitly factoring in Kraken fees), **`--fee 0.0026` (or `--fee 0.0040`) MUST be passed to all hyperopt/backtest commands**.

### 1.5 Hyperopt & Backtest Workflows on VPS
- **How Hyperopt is run on VPS**:
  - Hyperopt is executed as a one-off container using `docker compose run --rm`:
    ```bash
    docker compose run --rm freqtrade-hopt-live hyperopt \
      --hyperopt-loss SharpeHyperOptLoss \
      --spaces stoploss roi trailing \
      --strategy <StrategyName> \
      --config /freqtrade/user_data/config_binance.json \
      --timerange "20210101-" \
      -e 150 \
      --fee 0.0026 \
      -j 2
    ```
  - Reference scripts in `~/freqtrade-wolf/user_data/scripts/`:
    - `run_hyperopt_candidate.sh`
    - `run_hyperopt_early.sh`
    - `run_comparison_backtest.sh`
  - Results are saved to `~/freqtrade-wolf/user_data/hyperopt_results/` (e.g., `strategy_WTE_btc200_2026-09-03_14-45-02.fthypt`).
  - Available system capacity: 2 vCPUs and 3.8 GiB RAM. Job workers should be set to `-j 2` to prevent memory thrashing.

---

## 2. Logic Chain

1. **Safety Separation between Live Trading & Dry-Run Deployment**:
   - *Observation*: Container `freqtrade-wolf-hopt-live` is active on port 8080 (`dry_run: false`) trading live capital.
   - *Logic Step 1*: Under no circumstances should port 8080 or `config_trend_hopt.json` be touched or stopped.
   - *Logic Step 2*: Ports 8081 and 8082 are currently unbound. Port 8082 is already designated in `docker-compose.yml` for dry-run simulation (`freqtrade-qe-sim`).
   - *Inference*: A dedicated service named `freqtrade-academic-dryrun` should be defined on port `8082` using port mapping `192.168.2.4:8082:8080`, mapped to its own dry-run configuration (`config_academic_dryrun.json`), with dedicated database `tradesv3_academic_dryrun.sqlite` and logfile `freqtrade_academic_dryrun.log`.

2. **Data Selection & Multi-Year Optimization Strategy (Requirement R2)**:
   - *Observation*: Kraken data in `user_data/data/kraken/` only covers ~2–5 months (spring/summer 2026), whereas Binance data in `user_data/data/binance/` spans 5.4 years (2021–2026 across 4h/1h).
   - *Logic Step 3*: Optimizing a strategy exclusively on 2 months of Kraken data risks severe overfitting to a short market regime.
   - *Logic Step 4*: Binance data offers complete multi-cycle stress testing (2021 bull, 2022 bear, 2023 chop, 2024 bull, 2025–2026).
   - *Inference*: The Data Scientist should run multi-year Hyperopt and Backtesting using `config_binance.json` with `--timerange 20210101-` (or `20240101-`), while enforcing `--fee 0.0026` (Kraken fee) to guarantee the >10% profit hurdle is met under realistic Kraken transaction friction.

3. **Timeframe Compatibility with Kraken Spot API**:
   - *Observation*: Kraken exchange does not support 2h candles (as documented in commit `2c19b77` and `WolfTrend_1h_Candidate.py`). Kraken natively supports 15m, 1h, 4h, 1d.
   - *Inference*: The strategy to be deployed in dry-run on Kraken must use `timeframe = '1h'` (or `15m` / `4h`). 2h timeframes are rejected.

4. **Synchronization Protocol Compliance (`GEMINI.md`)**:
   - *Observation*: `GEMINI.md` dictates the exact sync command:
     ```bash
     rsync -avz --exclude '.git' --exclude 'user_data/data' --exclude 'user_data/logs' \
       --exclude 'user_data/hyperopt_results' --exclude 'user_data/backtest_results' \
       --exclude '*.sqlite*' ./ vps-matthijs-trader:~/freqtrade-wolf/
     ```
   - *Inference*: Any local code changes (new strategy `.py`, `docker-compose.yml`, config) must be committed locally on a feature branch, and once authorized, synced to the VPS using this exact rsync command.

---

## 3. Caveats

1. **Live Production Isolation**: The production bot `freqtrade-wolf-hopt-live` is actively trading live funds. Any container restart command must target only the specific dry-run service (e.g. `docker compose up -d freqtrade-academic-dryrun`), never a blanket `docker compose down` or `docker compose restart`.
2. **VPS Resource Constraints**: The VPS has 2 vCPUs and 3.8 GiB RAM. Simultaneous execution of heavy hyperopt (e.g. 500+ epochs with all spaces) will cause high CPU load; `-j 2` or `-j 1` should be used, and epoch counts should be kept reasonable (100–250 epochs).
3. **Kaspa (KAS) Pair**: `KAS/USDT` does not exist on Binance spot. If KAS is included in the pairlist for backtests, it must use Kraken data (`KAS/EUR`) or be excluded from the Binance backtesting pairlist.
4. **Uncommitted Local Config**: In the local git repository, `config_trend_hopt.json` has an unstaged change (removal of `"timeframe": "4h"`). This should be preserved or cleaned when branching.

---

## 4. Conclusion

1. **VPS Infrastructure Readiness**:
   - SSH access is passwordless and fully operational (`vps-matthijs-trader`).
   - Docker and Docker Compose v2 are properly configured with image `freqtradeorg/freqtrade:stable`.
   - Dedicated port `8082` is vacant and ready for the dry-run container.
2. **Data & Hyperopt Strategy**:
   - Dataset: Use `user_data/data/binance/` for 5.4-year backtesting and parameter tuning across 1h / 4h candles.
   - Fee Parameter: Mandatory use of `--fee 0.0026` (or `--fee 0.0040`) on all `freqtrade hyperopt` and `freqtrade backtesting` commands.
   - Hyperopt Command: Execute via `docker compose run --rm freqtrade-hopt-live hyperopt ... -j 2`.
3. **Dry-Run Deployment Architecture**:
   - Service name: `freqtrade-academic-dryrun` (or uncomment `freqtrade-qe-sim`).
   - Port: `192.168.2.4:8082:8080`.
   - Config file: `config_academic_dryrun.json` with `"dry_run": true`, `"dry_run_wallet": 1500`, `"stake_currency": "EUR"`, `"stake_amount": 75`.
   - SQLite DB: `/freqtrade/user_data/tradesv3_academic_dryrun.sqlite`.
   - Logfile: `/freqtrade/user_data/logs/freqtrade_academic_dryrun.log`.

---

## 5. Verification Method

To independently verify all findings in this report:

1. **Verify VPS Hardware & Free Ports**:
   ```bash
   ssh vps-matthijs-trader "nproc && free -h && ss -tulpn | grep 808"
   ```
   *Expected*: 2 CPUs, ~2.3 GiB available memory, port 8080 listening (live bot), ports 8081 and 8082 unlisted (free).

2. **Verify Live Bot Heartbeat**:
   ```bash
   ssh vps-matthijs-trader "docker logs --tail=5 freqtrade-wolf-hopt-live"
   ```
   *Expected*: Heartbeat lines showing `state='RUNNING'`.

3. **Verify Data Inventory & Date Spans**:
   ```bash
   ssh vps-matthijs-trader "docker compose -f ~/freqtrade-wolf/docker-compose.yml run --rm freqtrade-hopt-live list-data --exchange binance"
   ssh vps-matthijs-trader "docker compose -f ~/freqtrade-wolf/docker-compose.yml run --rm freqtrade-hopt-live list-data --exchange kraken"
   ```
   *Expected*: 90 pair/timeframe combinations for Binance, 74 for Kraken.

4. **Verify Fee Resolution via CCXT**:
   ```bash
   ssh vps-matthijs-trader "docker compose -f ~/freqtrade-wolf/docker-compose.yml run --rm --entrypoint python3 freqtrade-hopt-live -c 'import ccxt; print(\"Kraken:\", ccxt.kraken().fees[\"trading\"][\"taker\"]); print(\"Binance:\", ccxt.binance().fees[\"trading\"][\"taker\"])'"
   ```
   *Expected*: Kraken taker `0.0026`, Binance taker `0.001`.
