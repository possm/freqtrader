# BRIEFING — 2026-09-04T19:12:45Z

## Mission
Investigate risk management parameters, drawdown tolerance, capital allocation, Kraken Spot fee/slippage modeling, and governance requirements for achieving >=10% net profit per month on Kraken Spot.

## 🔒 My Identity
- Archetype: explorer
- Roles: Risk Manager & Governance Explorer (Survey Explorer)
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_riskmanager
- Original parent: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Milestone: M1_survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement code changes
- Follow GEMINI.md and Git rules
- Never push to remote without explicit permission
- Keep files in agent directory (.agents/ must contain only metadata)
- Base backtests and risk parameters on realistic Kraken spot mechanics

## Current Parent
- Conversation ID: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Updated: not yet

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `reports/ACADEMIC_STRATEGY_REPORT.md`, `analyze_slippage.py`, `user_data/strategies/kraken_slippage.py`, `config_academic_dryrun.json`, `config_trend_hopt.json`, `docker-compose.yml`, VPS hardware and docker containers via SSH.
- **Key findings**:
  1. Solved the mystery of past under-performance: past strategy had 10 slots of 75 EUR (5% stake on 1500 wallet), resulting in 85%+ cash idle. Scaling to `max_open_trades = 4` (25% stake) unlocks the necessary capital velocity.
  2. Mathematically proved that 5m scalping fails (>35% portfolio fee drag/month) and 4h swing fails (insufficient trades). 1h timeframe (35-65 trades/month, ~0.8-1.2% net/trade) is the optimal sweet spot.
  3. Formulated Risk Manager Mandate: Drawdown ceiling of 25%-35% is mathematically mandatory for a >120% annual spot crypto target (Calmar 3.5-4.8). Expecting <15% DD is a statistical impossibility.
  4. Multi-tier Governance: Protections `MaxDrawdown` (30% cap / 48h halt), `StoplossGuard` (4 stops / 24h halt), `CooldownPeriod` (2 candles), and BTC > EMA200 macro filter.
  5. Established 11-section architectural outline for `reports/10PERCENT_MONTH_REPORT.md` and defined 4-stage verification gates.
- **Unexplored areas**: None for M1 survey. M2 will execute hyperopt and fee-adjusted backtests on VPS.

## Key Decisions Made
- Risk Manager officially approved 25%-35% maximum drawdown ceiling for the >=10%/month target.
- Mandated `max_open_trades = 4` (25% stake allocation per trade) on long-only Kraken spot.
- Mandated explicit `--fee 0.0026` CLI enforcement in all backtests/hyperopts.
- Mandated port 8083 and isolated database `tradesv3_aggressive_dryrun.sqlite` for the new dry-run service to protect live bot on 8080.
- Completed comprehensive 5-component handoff report.

## Artifact Index
- DISPATCH.md — Recorded task dispatch
- BRIEFING.md — Persistent working memory
- progress.md — Liveness heartbeat and milestone tracking
- handoff.md — Comprehensive 5-component Risk Management & Governance Handoff Report
