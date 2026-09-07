# Survey Explorer 1: Codebase & Repository Survey Report

## 1. Observation

### 1.1 Local Git Status & Branching
- **Current Branch**: `feature/early-entry-2h-strategy` (up to date with `origin/feature/early-entry-2h-strategy`).
- **All Local & Remote Branches**:
  - Local: `feature/early-entry-2h-strategy`, `feature/initial-import`, `main`.
  - Remote: `origin/HEAD -> origin/feature/initial-import`, `origin/feature/early-entry-2h-strategy`, `origin/feature/initial-import`, `origin/main`.
  - Remote URL: `https://github.com/possm/freqtrader-trend.git`.
- **Working Tree State**:
  - Modified uncommitted file: `config_trend_hopt.json` (diff: removal of `"timeframe": "4h"`).
  - Untracked files/folders: `.agents/`, `rename_tf.py`, `user_data/backtest_results/`, `user_data/data/`, `user_data/hyperopt_results/`, `user_data/logs/`, helper scripts in `user_data/scripts/`, and 9 untracked strategies in `user_data/strategies/`.
- **Recent Git Log**:
  - `aeab992 chore: Add GEMINI.md deployment workflow rules`
  - `2c19b77 fix: Switch to 1h candidate because Kraken does not support 2h candles`
  - `0700401 feat: Promote WolfTrend_2h_Candidate to live bot`
  - `199a159 Initial commit of freqtrade-wolf config`

### 1.2 Repository Structure & File Layout
- **Root Directory (`/Users/matthijsdrenth/IdeaProjects/freqtrade-trend`)**:
  - Config files: `config.json`, `config_backtest.json`, `config_kraken_dryrun.json`, `config_mr.json`, `config_trend.json`, `config_trend_hopt.json`, `config_sim*.json`.
  - Infrastructure: `docker-compose.yml`, `.env` (contains API keys, JWT secret, exchange credentials), `.gitignore`, `GEMINI.md`.
  - Subdirectories: `user_data/` (primary location for data, strategies, logs, scripts, backtests), `strategies/` (empty), `hyperopts/` (empty), `freqaimodels/`, `notebooks/`, `plot/`.
- **Strategies Directory (`user_data/strategies/`)**:
  - Contains 250 files representing multiple strategy archetypes:
    - **Trend Following**: `WolfTrend_1h_Candidate.py` (currently live in production), `WolfTrend_EMA_hopt_tuned.py`, `WolfTrend_Donchian*.py`, `WolfTrend_emacross*.py`.
    - **Regime-Gated Volatility Breakout**: `WolfQuantEdge.py` (Keltner Upper Band + ATR expansion + Kaufman Efficiency Ratio regime gate + rising 4h BTC EMA50 gate + chandelier ATR trailing stoploss).
    - **Mean Reversion**: `WolfMR_4h_btc*.py`, `WolfMeanReversion*.py`, `WolfMR_1h*.py`, `WolfMR_15m*.py`.
    - **Slippage & Microstructure Model**: `kraken_slippage.py` (`KrakenSlippageMixin`).
- **Data Availability**:
  - Local `user_data/data/binance/`: 68 `.feather` files covering 17 altcoins (`AAVE`, `ADA`, `ARB`, `FET`, `HBAR`, `INJ`, `LINK`, `NEAR`, `OP`, `POL`, `RENDER`, `SOL`, `STX`, `SUI`, `TIA`, etc.) and `BTC` across 15m, 1h, 2h, and 4h timeframes.
  - Local `user_data/data/kraken/`: empty.
  - VPS `vps-matthijs-trader:~/freqtrade-wolf/user_data/data/kraken/`: 93 `.feather` files covering 18 Kraken EUR pairs (`AAVE/EUR`, `ADA/EUR`, `ARB/EUR`, `BTC/EUR`, `ETH/EUR`, `FET/EUR`, `HBAR/EUR`, `INJ/EUR`, `KAS/EUR`, `LINK/EUR`, `NEAR/EUR`, `OP/EUR`, `POL/EUR`, `RENDER/EUR`, `SOL/EUR`, `STX/EUR`, `SUI/EUR`, `TIA/EUR`) with 15m, 1h, 4h candles and trade files.
- **Docker Compose Setup**:
  - Local & VPS `docker-compose.yml` defines:
    - `freqtrade-hopt-live`: Production live bot on port 8080 (`192.168.2.4:8080:8080`), mapped to `config_trend_hopt.json`, strategy `WolfTrend_1h_Candidate`.
    - `freqtrade-trend-sim` (commented out): port 8081, mapped to `config_trend.json`.
    - `freqtrade-qe-sim` (commented out): port 8082, mapped to `config_kraken_dryrun.json`, strategy `WolfQuantEdge`.
  - Image: `freqtradeorg/freqtrade:stable`.
- **VPS Connectivity (`vps-matthijs-trader`)**:
  - SSH access tested and verified: `ssh vps-matthijs-trader "uptime"` returns load average with no password needed.
  - Active container on VPS: `freqtrade-wolf-hopt-live` is running (Up 5 hours).
  - Live container logs confirm normal operation: `Bot heartbeat. PID=1, version='2026.4', state='RUNNING'`.

---

## 2. Logic Chain

### Step 1: Exchange Timeframe Compatibility
- *Observation*: Commit `2c19b77` states `Switch to 1h candidate because Kraken does not support 2h candles`. Line 18 of `WolfTrend_1h_Candidate.py` comments: `Kraken does not support 2h candles!`.
- *Inference*: Kraken exchange natively supports 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w. Any strategy designed for live/dry-run deployment on Kraken MUST NOT use unsupported timeframes like 2h. The base timeframe should be 1h, 15m, or 4h, optionally using informative pairs (e.g., 4h BTC trend filter).

### Step 2: Realistic Fee & Slippage Modeling for Kraken
- *Observation*: `kraken_slippage.py` provides `KrakenSlippageMixin` which calculates adverse limit pricing during `RunMode.BACKTEST` and `RunMode.HYPEROPT` based on `KRAKEN_SPREAD_BPS` (1.5 to 12 bps), volatility slippage (`0.08 * ATR/close * rand`), and market impact (`0.05 * sqrt(participation)`). In `fee_test.log`, backtesting is executed with `--fee 0.0026` (0.26% Kraken taker fee per side, or 0.52% round trip).
- *Inference*: To achieve Acceptance Criterion R2 (>10% profit beating Kraken fees), the strategy must inherit `KrakenSlippageMixin` or be evaluated with `--fee 0.0026`. Unfiltered high-frequency mean reversion will suffer severe fee drag, whereas volatility expansion breakout or trend-following pullbacks in established regimes comfortably clear the fee threshold (as proven by `WolfTrend_1h_Candidate` achieving +211.06% in `fee_test.log`).

### Step 3: Hyperopt Workflow & VPS Execution
- *Observation*: `user_data/scripts/run_hyperopt_candidate.sh` uses Docker Compose to run hyperopt against `user_data/config_binance.json` with timerange `20210101-` and loss function `SharpeHyperOptLoss`.
- *Inference*: Hyperopt sessions should be executed on `vps-matthijs-trader` via SSH using `docker compose run --rm freqtrade-hopt-live hyperopt ...`. The multi-year Binance dataset on the VPS spans bull (2021, 2024), bear (2022), and chop (2023, 2025-2026), providing robust out-of-sample stress testing.

### Step 4: Dry-Run Container Deployment (Acceptance Criterion R3)
- *Observation*: Port 8080 is currently occupied by the live bot `freqtrade-wolf-hopt-live`. `docker-compose.yml` already contains a template for port 8082 (`freqtrade-qe-sim`) mapped to `config_kraken_dryrun.json` with `"dry_run": true`.
- *Inference*: To safely deploy the new strategy in Dry-Run mode without interfering with the live bot, a dedicated service (`freqtrade-academic-dryrun` or re-enabling port 8082) should be configured in `docker-compose.yml` with `"dry_run": true` on port 8082, with its own sqlite database (`tradesv3_dryrun.sqlite`) and log file (`freqtrade_dryrun.log`).

### Step 5: Git Branching & Remote Protection
- *Observation*: The user rules require:
  1. Always create a new git branch before modifying code or making commits; never commit to main.
  2. Never push autonomously to any remote.
  3. Current branch is `feature/early-entry-2h-strategy`.
- *Inference*: All upcoming development work must be performed on a dedicated branch created from `main` or current clean state, specifically recommended as:
  `feat/academic-altcoin-strategy`
  The command for the implementer is:
  `git checkout -b feat/academic-altcoin-strategy`

---

## 3. Caveats

1. **Local vs Remote Kraken Data**: Local `user_data/data/kraken/` is empty; the full historical dataset for Kraken EUR pairs resides on the VPS at `~/freqtrade-wolf/user_data/data/kraken/`. Research/backtesting locally uses `user_data/data/binance/` (USDT pairs) with `KrakenSlippageMixin` to model Kraken spreads and fees.
2. **Unstaged Working Tree Change**: `config_trend_hopt.json` has a single unstaged modification (deletion of `"timeframe": "4h"`). This should be preserved or properly handled when branching.
3. **Live Bot Isolation**: The live trading bot (`freqtrade-wolf-hopt-live`) is actively managing funds on Kraken on port 8080. Any changes to `docker-compose.yml` must preserve this service intact and only introduce or modify the secondary dry-run service on port 8082.

---

## 4. Conclusion

1. **Branch Recommendation**: Create branch `feat/academic-altcoin-strategy` via `git checkout -b feat/academic-altcoin-strategy`. Do not commit directly to `main` or `feature/early-entry-2h-strategy`. Do not push to remote without explicit user authorization.
2. **Strategy Architectural Pattern**:
   - Timeframe: Base `1h` (or `15m` with `4h` informative). Never `2h`.
   - Fee Modeling: Incorporate `KrakenSlippageMixin` (`from kraken_slippage import KrakenSlippageMixin`) and configure backtest fee `--fee 0.0026`.
   - Theoretical Foundation: Volatility breakout (e.g. Keltner/Donchian with ATR expansion) or Mean Reversion with macro regime gating (e.g., Kaufman Efficiency Ratio > 0.45 or BTC > 4h EMA200).
3. **Hyperopt & Validation Target**:
   - Run on VPS: `docker compose run --rm freqtrade-hopt-live hyperopt --hyperopt-loss SharpeHyperOptLoss --spaces stoploss roi trailing --strategy <StratName> --config /freqtrade/user_data/config_binance.json --timerange "20210101-" -e 150 --fee 0.0026`.
   - Criterion: Total profit > 10% net after Kraken fees.
4. **Dry-Run Deployment Target**:
   - Add/enable service on port 8082 in `docker-compose.yml` using `config_kraken_dryrun.json`.
   - Rsync files to VPS following `GEMINI.md`:
     `rsync -avz --exclude '.git' --exclude 'user_data/data' --exclude 'user_data/logs' --exclude 'user_data/hyperopt_results' --exclude 'user_data/backtest_results' --exclude '*.sqlite*' ./ vps-matthijs-trader:~/freqtrade-wolf/`
   - Start dry-run container and verify >= 3 heartbeat logs with `state='RUNNING'`.

---

## 5. Verification Method

To independently verify these findings, execute the following commands:

```bash
# 1. Verify Git status and branches
git status
git branch -a

# 2. Verify VPS connectivity and active live bot container
ssh vps-matthijs-trader "cd freqtrade-wolf && docker compose ps"

# 3. Check live bot heartbeat logs
ssh vps-matthijs-trader "cd freqtrade-wolf && docker compose logs --tail=20 freqtrade-hopt-live"

# 4. Verify Kraken data inventory on VPS
ssh vps-matthijs-trader "cd freqtrade-wolf && ls -la user_data/data/kraken | head -n 25"

# 5. Inspect Kraken slippage mixin and fee configuration
head -n 45 user_data/strategies/kraken_slippage.py
grep -i "fee" user_data/logs/fee_test.log | head -n 10
```

Invalidation Conditions:
- If `ssh vps-matthijs-trader` fails or requires password credentials, the automated VPS workflow would be blocked.
- If Kraken native candle support changed to allow 2h candles, 2h could be re-evaluated (currently rejected by Kraken API).
