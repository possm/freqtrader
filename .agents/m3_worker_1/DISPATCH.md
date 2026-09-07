# Dispatch for Milestone 3 & 4 Worker (Risk Manager & Deployment Specialist)

## Mission
Execute Risk Verification, Dry Run VPS Deployment, Stability Verification (>= 3 heartbeats), and Final Academic Strategy Report.

## Acceptance Criteria
1. `WolfBreakout_PVB.py` and `WolfBreakout_PVB.json` synced to `vps-matthijs-trader:~/freqtrade-wolf/user_data/strategies/`.
2. Dedicated dry-run configuration `config_academic_dryrun.json` created and synced:
   - `"dry_run": true`
   - `"dry_run_wallet": 1500`
   - `"stake_currency": "EUR"`, `"stake_amount": 75`
   - 18 Kraken EUR pairs
   - Dedicated database: `/freqtrade/user_data/tradesv3_academic_dryrun.sqlite`
   - Dedicated logfile: `/freqtrade/user_data/logs/freqtrade_academic_dryrun.log`
   - Port 8080 inside container, mapped to host port 8082 in `docker-compose.yml`.
3. `docker-compose.yml` updated with service `freqtrade-academic-dryrun` on port 8082 without touching live bot on port 8080!
4. Files synced to VPS per GEMINI.md:
   ```bash
   rsync -avz --exclude '.git' --exclude 'user_data/data' --exclude 'user_data/logs' --exclude 'user_data/hyperopt_results' --exclude 'user_data/backtest_results' --exclude '*.sqlite*' ./ vps-matthijs-trader:~/freqtrade-wolf/
   ```
5. Dry-run container started on VPS:
   ```bash
   ssh vps-matthijs-trader "cd freqtrade-wolf && docker compose up -d freqtrade-academic-dryrun"
   ```
6. Container stability verified:
   - Container is running without exit/crash.
   - Logs show AT LEAST 3 successful `Bot heartbeat` messages with `state='RUNNING'`:
     `ssh vps-matthijs-trader "cd freqtrade-wolf && docker compose logs --tail=60 freqtrade-academic-dryrun"`
   - Live bot on port 8080 confirmed still running intact.
7. Documentation report:
   - Generate `reports/ACADEMIC_STRATEGY_REPORT.md` documenting:
     - Academic theoretical foundation (Parkinson 1980 continuous range volatility, Mandelbrot volatility clustering, Donchian/Keltner dual breakout, BTC macro trend filter)
     - Timeframe analysis (1h vs 15m/4h) and fee drag justification
     - Hyperopt optimization results (10.55% net profit after 0.26% Kraken fees, 373 trades, 7.96% max drawdown)
     - Risk management mechanisms (stoploss, trailing stop, minimal ROI, stale trade exit)
     - Dry-run deployment proof (port 8082, 3+ heartbeats logs verbatim)
8. Commit all new/modified files (`config_academic_dryrun.json`, `docker-compose.yml`, `reports/ACADEMIC_STRATEGY_REPORT.md`) to branch `feat/academic-altcoin-strategy`.
   DO NOT PUSH TO REMOTE.
9. Deliver handoff report to `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m3_worker_1/handoff.md`.

## Critical Rules
- Branch: `feat/academic-altcoin-strategy`. NEVER commit to main. NEVER run git push.
- NEVER stop or restart the live bot `freqtrade-wolf-hopt-live` on port 8080!
- Only start/manage `freqtrade-academic-dryrun` on port 8082.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
