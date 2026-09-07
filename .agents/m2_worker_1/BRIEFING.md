# BRIEFING — 2026-09-04T15:44:00Z

## Mission
Execute Milestone 2: Data preparation and Hyperopt parameter optimization on VPS for WolfBreakout_PVB strategy under strict Kraken fee modeling (--fee 0.0026), achieve >10% net profit verification, integrate optimized parameters, pass unit tests, and commit to feat/academic-altcoin-strategy.

## 🔒 My Identity
- Archetype: Data Scientist & Hyperopt Specialist
- Roles: implementer, qa, specialist
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_1
- Original parent: 90978f93-4bda-450d-89cf-eb27ba874681
- Milestone: Milestone 2 (Data Prep & Hyperopt on VPS)

## 🔒 Key Constraints
- Branch constraint: All work strictly on `feat/academic-altcoin-strategy`. NEVER commit to main/master. NEVER run git push without explicit user command.
- Production isolation: NEVER stop, restart, or touch the live production bot `freqtrade-wolf-hopt-live` on port 8080!
- Ephemeral execution: All remote VPS commands must use `docker compose run --rm freqtrade-hopt-live ...`.
- Fee modeling: Strictly pass `--fee 0.0026` to hyperopt and backtest commands.
- Hardware efficiency: Limit VPS jobs to `-j 2`.
- Minimum hurdle: Verification backtest Total profit % must exceed +10% net after fees.

## Current Parent
- Conversation ID: 90978f93-4bda-450d-89cf-eb27ba874681
- Updated: 2026-09-04T15:44:00Z

## Task Summary
- **What to build**: Parameter optimization and integration for `WolfBreakout_PVB`
- **Success criteria**: Hyperopt completed on multi-year 1h Binance dataset with `--fee 0.0026`; best parameters integrated into strategy; backtest net profit > 10%; unit tests pass (33/33); committed locally.
- **Interface contracts**: PROJECT.md
- **Code layout**: `user_data/strategies/WolfBreakout_PVB.py`, `tests/test_wolfbreakout_pvb.py`

## Change Tracker
- **Files modified**: None yet
- **Build status**: Unit tests passed in M1 (33/33)
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pass (33 tests in 0.241s)
- **Lint status**: Clean
- **Tests added/modified**: In M1 (33 tests in tests/test_wolfbreakout_pvb.py)

## Key Decisions Made
- Multi-year dataset: Use Binance 1h data (5.4 years) with Kraken fee override `--fee 0.0026`.
- Spaces: buy, roi, stoploss, trailing. Loss function: SharpeHyperOptLoss or ProfitHyperOptLoss.

## Artifact Index
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_1/DISPATCH.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_1/handoff.md (pending)
