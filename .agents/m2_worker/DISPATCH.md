## 2026-09-07T13:38:54Z
You are m2_worker, an Architectural Consolidation Worker.
Your working directory is: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m2_worker/

You MUST read ORIGINAL_REQUEST.md at: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/ORIGINAL_REQUEST.md before starting work (specifically section ## 2026-09-07T13:24:13Z).
You must also read PROJECT.md at: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/orchestrator_3/PROJECT.md
And review:
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/survey_arch_report.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/handoff.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m1_worker/handoff.md

Target Monorepo: `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo`

Your Mission:
Execute Milestone 2 (Architectural Consolidation):
1. In `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo`, verify you are on feature branch `feat/monorepo-consolidation`.
2. Construct the central `docker-compose.yml` at the root of the monorepo based on the verified design in `survey_arch_report.md`.
   The compose file must define:
   - `freqtrader-dash`: build `./dashboard`, container `freqtrader-dash`, ports `"${LISTEN_IP:-192.168.2.4}:80:80"`, restart `unless-stopped`.
   - `freqtrade-hopt-live`: image `freqtradeorg/freqtrade:stable`, container `freqtrade-wolf-hopt-live`, ports `"${LISTEN_IP:-192.168.2.4}:8080:8080"`, volumes `./user_data:/freqtrade/user_data`, command `trade --logfile /freqtrade/user_data/logs/freqtrade_hopt_live.log --db-url sqlite:////freqtrade/user_data/tradesv3_hopt_live.sqlite --config /freqtrade/user_data/config.json --strategy WolfTrend_1h_Candidate`, env_file `.env`.
   - `freqtrade-grid`: image `freqtradeorg/freqtrade:stable`, container `freqtrade-grid`, ports `"${LISTEN_IP:-192.168.2.4}:8081:8080"`, volumes `./user_data:/freqtrade/user_data`, command `trade --logfile /freqtrade/user_data/logs/freqtrade_grid.log --db-url sqlite:////freqtrade/user_data/tradesv3_grid.sqlite --config /freqtrade/user_data/config_grid.json --strategy StepGrid`, env_file `.env`.
   - `freqtrade-academic-dryrun`: image `freqtradeorg/freqtrade:stable`, container `freqtrade-wolf-academic-dryrun`, ports `"${LISTEN_IP:-192.168.2.4}:8082:8080"`, volumes `./user_data:/freqtrade/user_data`, command `trade --logfile /freqtrade/user_data/logs/freqtrade_academic_dryrun.log --db-url sqlite:////freqtrade/user_data/tradesv3_academic_dryrun.sqlite --config /freqtrade/user_data/config_academic_dryrun.json --strategy WolfBreakout_PVB`, env_file `.env`.
   - `freqtrade-breakout-daily`: image `freqtradeorg/freqtrade:stable`, container `freqtrade-wolf-breakout-daily`, ports `"${LISTEN_IP:-192.168.2.4}:8083:8080"`, volumes `./user_data:/freqtrade/user_data`, command `trade --logfile /freqtrade/user_data/logs/freqtrade_breakout_daily.log --db-url sqlite:////freqtrade/user_data/tradesv3_breakout_daily.sqlite --config /freqtrade/user_data/config_breakout_daily.json --strategy WolfBreakout_Daily`, env_file `.env`.
3. Single Root `user_data/` Directory:
   - Exactly one `user_data/` directory at the root level serving all bots. Ensure NO `dashboard/user_data` directory exists.
   - Organize all bot configs cleanly into `user_data/`:
     - `config.json` (trend live bot)
     - `config_grid.json` (grid bot)
     - `config_grid_backtest.json` (grid backtest)
     - `config_academic_dryrun.json` (academic dryrun bot)
     - `config_breakout_daily.json` (breakout daily macro bot)
     - Any additional auxiliary configs (`config_backtest.json`, `config_trend_hopt.json`, etc.)
   - Ensure all active bot configs have API server configured with:
     - `"listen_ip_address": "0.0.0.0"`
     - `"CORS_origins": ["http://192.168.2.4", "http://192.168.2.4:80", "http://localhost", "http://127.0.0.1"]`
4. Validation:
   - Run `docker compose config` in `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo` and verify it succeeds with exit code 0.
   - Verify that all referenced config files in `docker-compose.yml` actually exist inside `user_data/`.
5. Git Branching:
   - Commit changes to `feat/monorepo-consolidation` with a clear commit message.
   - NEVER commit directly to main.
   - NEVER push to remote (`git push`) without explicit user permission.
6. Deliverables:
   - Write implementation report to: `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m2_worker/m2_implementation_report.md`
   - Write 5-component `handoff.md` to: `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m2_worker/handoff.md`
   - Send completion message to parent.
