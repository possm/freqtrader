## 2026-09-07T13:32:56Z
You are m1_worker, a Monorepo Migration Worker.
Your working directory is: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m1_worker/

You MUST read ORIGINAL_REQUEST.md at: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/ORIGINAL_REQUEST.md before starting work (specifically section ## 2026-09-07T13:24:13Z).
You must also read PROJECT.md at: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/orchestrator_3/PROJECT.md
And review the survey reports at:
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_1/survey_git_report.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_1/handoff.md

Your Mission:
Execute Milestone 1 (History-Preserving Repository Migration):
1. Initialize the new monorepo at `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo` with `git init -b main`.
2. Follow the tested Multi-Remote Fetch + Preparation Branches recipe from Section 6 of `survey_git_report.md`.
3. Fetch all 4 repositories:
   - `freqtrade-breakout` (/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout)
   - `freqtrade-grid` (/Users/matthijsdrenth/IdeaProjects/freqtrade-grid)
   - `freqtrade-trend` (/Users/matthijsdrenth/IdeaProjects/freqtrade-trend)
   - `freqtrader-dash` (/Users/matthijsdrenth/IdeaProjects/freqtrader-dash)
4. Create preparation branches:
   - `prep/dash`: isolate `freqtrader-dash` files into `dashboard/` subdirectory.
   - `prep/grid`: rename `user_data/config.json` -> `user_data/config_grid.json` and backtest config -> `user_data/config_grid_backtest.json`.
5. Execute the unrelated histories merge into the monorepo:
   - Start from `trend/chore/split-academic-bot` on `main`.
   - Merge `prep/dash` (with message: "Merge freqtrader-dash into dashboard/ preserving history").
   - Merge `prep/grid` (with message: "Merge freqtrade-grid into user_data/ preserving history").
   - Merge `breakout/feat/daily-macro-strategy` (with message: "Merge freqtrade-breakout preserving history").
6. Verify all 69 original commit SHAs, author dates, and commit messages are preserved:
   - `git log --all --oneline | wc -l` (must be >= 75 commits).
   - Verify `git log --follow --oneline dashboard/app.jsx` traces back to original initial commit `168b45a`.
   - Verify `git log --follow --oneline user_data/strategies/StepGrid.py` traces back to `316b6b3`.
   - Verify `git log --follow --oneline user_data/strategies/WolfBreakout_Daily.py` traces back to `9e64a9e`.
7. Preserve uncommitted and untracked assets:
   - Copy uncommitted modified files and untracked strategies from source repos:
     - Updated `StepGrid.py` (with EMA1000 trend filter) from `freqtrade-grid/user_data/strategies/StepGrid.py`
     - Tuned `.json` parameter files (e.g. `WolfBreakout_PVB.json`, `WolfBreakout_Daily.json`, `WolfTrend_1h_Candidate.json`)
     - Untracked `Wolf*.py` strategies from `freqtrade-breakout` and `freqtrade-trend`
8. Clean git index of binary candle files:
   - If binary `.feather` candle files were committed in breakout, ensure `git rm -r --cached user_data/data/` is run so working tree does not track heavy binaries.
   - Configure `.gitignore` to exclude `user_data/data/`, `*.sqlite*`, `user_data/logs/`, `*.pyc`, `__pycache__`.
9. GLOBAL GIT BRANCHING RULE:
   - Create and checkout feature branch `feat/monorepo-consolidation`.
   - Commit changes to `feat/monorepo-consolidation`.
   - NEVER commit directly to main or master.
   - NEVER push to remote (`git push`) without explicit user permission.
10. Deliverables:
    - Write implementation report to: `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m1_worker/m1_implementation_report.md`
    - Write 5-component `handoff.md` to: `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m1_worker/handoff.md`
    - Send completion message to parent.
