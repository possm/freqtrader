# BRIEFING — 2026-09-04T17:48:45Z

## Mission
Execute Milestone 2 as replacement worker: inspect/run Hyperopt parameter optimization on VPS for WolfBreakout_PVB with `--fee 0.0026` and `-j 2`, extract best parameters, update `user_data/strategies/WolfBreakout_PVB.py`, sync to VPS, run full validation backtest verifying `Total profit %` > 10% after Kraken fees, run local unit tests in Docker, commit to branch `feat/academic-altcoin-strategy` (no push), and write handoff report.

## 🔒 My Identity
- Archetype: Data Scientist & Hyperopt Specialist
- Roles: implementer, qa, specialist
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_2
- Original parent: 90978f93-4bda-450d-89cf-eb27ba874681
- Milestone: Milestone 2 (Data Prep & Hyperopt on VPS)

## 🔒 Key Constraints
- Branch constraint: All work strictly on `feat/academic-altcoin-strategy`. NEVER commit to main/master. NEVER run git push without explicit user command.
- Production isolation: NEVER stop, restart, or touch the live production bot `freqtrade-wolf-hopt-live` on port 8080!
- Ephemeral execution: All remote VPS commands must use `docker compose run --rm freqtrade-hopt-live ...`.
- Fee modeling: Strictly pass `--fee 0.0026` to hyperopt and backtest commands.
- Hardware efficiency: Limit VPS jobs to `-j 2`.
- Minimum hurdle: Verification backtest Total profit % must exceed +10% net after Kraken fees.

## Current Parent
- Conversation ID: 90978f93-4bda-450d-89cf-eb27ba874681
- Updated: 2026-09-04T17:48:45Z

## Task Summary
- **What to build**: Hyperopt parameter optimization and integration for `WolfBreakout_PVB`
- **Success criteria**: Hyperopt checked/completed on VPS with `--fee 0.0026`; best parameters integrated into `user_data/strategies/WolfBreakout_PVB.py`; synced to VPS; backtest net profit > 10%; unit tests pass (33/33) in Docker locally; committed locally on `feat/academic-altcoin-strategy`.
- **Interface contracts**: PROJECT.md
- **Code layout**: `user_data/strategies/WolfBreakout_PVB.py`, `tests/test_wolfbreakout_pvb.py`

## Change Tracker
- **Files modified**: None yet
- **Build status**: Unit tests passed in M1
- **Pending issues**: Check VPS hyperopt status

## Quality Status
- **Build/test result**: Pass (33 tests in M1)
- **Lint status**: Clean
- **Tests added/modified**: Pending verification

## Key Decisions Made
- Use isolated ephemeral containers on VPS `docker compose run --rm freqtrade-hopt-live ...`
- Strict fee modeling `--fee 0.0026`

## Artifact Index
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_2/DISPATCH.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_2/progress.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_2/handoff.md
