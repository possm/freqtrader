## 2026-09-07T13:52:41Z

You are m3_worker, a Cleanup & AI Context Preservation Worker.
Your working directory is: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m3_worker/

You MUST read ORIGINAL_REQUEST.md at: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/ORIGINAL_REQUEST.md before starting work (specifically section ## 2026-09-07T13:24:13Z).
You must also read PROJECT.md at: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/orchestrator_3/PROJECT.md
And review:
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_3/survey_ai_rules_cleanup_report.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_3/handoff.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m2_worker_2/handoff.md

Target Monorepo: `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo`

Your Mission:
Execute Milestone 3 (Aggressive Cleanup & AI Context Preservation):
1. In `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo`, verify you are on feature branch `feat/monorepo-consolidation`.
2. Aggressive Cleanup of Obsolete Artifacts (~2.02 GB):
   - Remove `user_data/hyperopt_results/` (~1.83 GB of pickles and epoch dumps)
   - Remove `user_data/backtest_results/` (~54 MB of old backtest archives)
   - Remove `dashboard/node_modules/` (~46 MB - dashboard runs Babel standalone in-browser, node_modules is unused)
   - Remove `.agents/m1_reviewer_1/coverdir/` (~77 MB / 1,684 pytest coverage files)
   - Remove stray root benchmark text files: `result_*.txt` (14 files)
   - Remove stray 0-byte file: `2026-05-09`
   - Remove stray root strategy duplicates: `WolfCustomSwingCH.py`, `WolfMR_4h_btc_noMFI.py`, `WolfTrend_EMA_hopt_tuned.py` (ensure active versions exist in `user_data/strategies/`)
   - Remove empty root scaffold directories: `freqaimodels/`, `hyperopts/`, `notebooks/`, `plot/`, `strategies/`
   - Remove scratch test scripts: `unify.py`, `rename_tf.py`, `btc_price*.py`, `test-puppeteer*.js`, `screenshot*.png`
   - Remove local/stale SQLite databases and backups (`user_data/tradesv3*.sqlite*`, `*.bak`)
   - Remove local logs in `user_data/logs/*.log`
   - Remove `__pycache__` and `.pytest_cache`
   - Ensure `.gitignore` properly excludes `user_data/hyperopt_results/`, `user_data/backtest_results/`, `user_data/logs/`, `*.sqlite*`, `user_data/data/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`.
3. AI Context & Rules Preservation:
   - Ensure master `.agents/` folder is present at monorepo root:
     - Includes all agent workspaces (minus coverdir).
     - Includes `ORIGINAL_REQUEST.md`.
     - Includes `.agents/rules/project-specifics.md` containing the dashboard and bot operational rules.
   - Implement consolidated root `GEMINI.md` as designed in Section 4 of `survey_ai_rules_cleanup_report.md`:
     - Global Git Branching Rule (new feature branch, never push to remote without explicit permission).
     - Multi-service VPS sync for `vps-matthijs-trader`:
       `rsync -avz --exclude '.git' --exclude 'user_data/data' --exclude 'user_data/logs' --exclude 'user_data/hyperopt_results' --exclude 'user_data/backtest_results' --exclude '*.sqlite*' ./ vps-matthijs-trader:~/freqtrade-wolf/`
     - Restart/validation command on VPS for services (`freqtrade-wolf-hopt-live`, `freqtrade-grid`, `freqtrade-wolf-academic-dryrun`, `freqtrader-dash`).
     - Hyperopt parameter leak precautions (prohibit hyperopt inside `user_data/strategies/`).
     - Babel cache-busting rule (`?v=` query strings in dashboard).
   - Implement root `.cursorrules` as designed in Section 5 of `survey_ai_rules_cleanup_report.md`.
4. Programmatic Validation:
   - Run: `find . -name ".agents" -o -name "GEMINI.md" -o -name ".cursorrules"`
     Verify all three are found and non-empty.
   - Run: `docker compose config` in the monorepo to verify it still passes with exit code 0.
   - Verify that obsolete files/folders are completely deleted from the working tree and git index.
5. Git Branching:
   - Commit all changes to `feat/monorepo-consolidation` with a clear commit message.
   - NEVER commit directly to main.
   - NEVER push to remote (`git push`) without explicit user permission.
6. Deliverables:
   - Write implementation report to: `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m3_worker/m3_implementation_report.md`
   - Write 5-component `handoff.md` to: `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m3_worker/handoff.md`
   - Send completion message to parent.
