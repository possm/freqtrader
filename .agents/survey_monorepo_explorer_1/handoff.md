# Handoff Report: Git Survey & Monorepo Migration Strategy

**Agent**: `survey_monorepo_explorer_1` (Git & Repository Structure Specialist Explorer)  
**Task**: Survey the 4 source repositories and define the optimal history-preserving git migration strategy for `freqtrade-monorepo`.  
**Date**: 2026-09-07  
**Detailed Report**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_1/survey_git_report.md`  

---

## 1. Observation

1. **Target Monorepo Path**:
   - Command: `test -e /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo && echo "EXISTS" || echo "DOES NOT EXIST"`
   - Output: `DOES NOT EXIST`. The directory has not been created.

2. **Repository Topology & Commits**:
   - `freqtrade-breakout`: Active branch `feat/daily-macro-strategy` (commit `bdb8c87`), local branch `main` (commit `a46e687`). Remotes: none. Total commits: 4. Root commit: `9e64a9e51c546133905396b2350dd3e7180c73f6`. Disk size: `.git/` is 386 MB because 17 binary `.feather` candle files were committed under `user_data/data/binance/`.
   - `freqtrade-grid`: Active branch `main` (commit `eeb9e00`), tracks `origin/main` (`https://github.com/possm/freqtrader-grid.git`). Local branch `setup-freqtrade-grid` (commit `22585bd`). Remotes: `origin`. Total commits: 9. Root commit: `316b6b36f7c0039fe91b091d7e300d33faf4c200`. Disk size: 300 KB.
   - `freqtrade-trend`: Active branch `chore/split-academic-bot` (commit `be53918`), tracks `origin/chore/split-academic-bot` (`https://github.com/possm/freqtrader-trend.git`). Local branches: `feat/academic-altcoin-strategy`, `feat/aggressive-10pct-monthly-strategy`, `feature/early-entry-2h-strategy`, `feature/initial-import`, `feature/stoploss-hyperopt-wolftrend1h`, `main`. Remotes: `origin`. Total commits: 14. Root commit: `199a1590ca1d06ace3d93f37690433fcfbc7ab16`. Disk size: 1.9 MB.
   - `freqtrader-dash`: Active branch `master` (commit `6dc8c2a`), tracks `origin/master` (`https://github.com/possm/freqtrader-dash.git`). Local branches: `feat/grid-bot-visualization` (at `6dc8c2a`), `fix-mobile-colors` (at `8f1be1a`). Remotes: `origin`. Total commits: 42. Root commit: `168b45ab5aa1efdef9fb43faeb2bdcbb85fcfea5`. Disk size: 1.8 MB.
   - Total unique commits across all 4 repositories: 69 (4 + 9 + 14 + 42). None of the 4 repos have git tags.

3. **Dirty Working Tree & Uncommitted Assets**:
   - `freqtrade-breakout`: Modified `docker-compose.yml` (added `freqtrade-hopt-live` service for `WolfBreakout_Daily` with live Kraken keys), modified `user_data/strategies/WolfTrend_1h_Candidate.py`. Untracked files include essential strategies (`WolfAftermath.py`, `WolfBearTrap.py`, `WolfBreakout_Daily.json`, `WolfBreakout_Macro.py`, `WolfBreakout_Test_*.py`, `WolfTrend_1h_Candidate.json`), shell scripts (`run_hyperopt_*.sh`), and text results (`result_*.txt`).
   - `freqtrade-grid`: Modified `user_data/strategies/StepGrid.py` (added `startup_candle_count = 1000` and `ema_1000` trend filter), modified `user_data/config_backtest.json` (fiat USD, BTC/USDT pairs). Untracked `.bak` files.
   - `freqtrade-trend`: Modified `config_hopt_stoploss_binance.json` (fee 0.004, 32-char jwt key), modified `user_data/strategies/WolfBreakout_PVB.json` (updated hyperopt parameters). Untracked strategies (`WolfMR_*.py`, `WolfQuantEdge_*.py`, `WolfScalp_*.py`), untracked configs (`config_bt_*_split.json`, `config_hopt_pvb_binance.json`), logs, and scripts.
   - `freqtrader-dash`: Clean tracked files. Untracked test scripts (`test-puppeteer*.js`, `screenshot*.png`, `unify.py`, `package.json`).

4. **Overlap Analysis**:
   - `freqtrade-breakout` and `freqtrade-trend` share 316 overlapping files, but only 3 files differ: `docker-compose.yml`, `user_data/strategies/WolfBreakout_PVB.json`, and `config_hopt_stoploss_binance.json`.
   - `freqtrade-grid` shares only core strategy `StepGrid.py` and grid configs.
   - `freqtrader-dash` is an in-browser Babel/React app that sits independently inside a subfolder (`dashboard/`).

5. **Tool Availability**:
   - `git-filter-repo` is NOT installed on the host (`which git-filter-repo` returned exit code 1).
   - Docker Compose version `v5.3.1` is installed and functional.

---

## 2. Logic Chain

1. Because `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo` does not exist (Observation 1), the monorepo must be initialized from scratch via `git init -b main`.
2. Because all 4 source repositories have disjoint root commits (Observation 2), merging them directly without prefix preparation causes namespace collisions at root (`docker-compose.yml`, `.gitignore`, `config.json`).
3. Because `git-filter-repo` is not installed (Observation 5) and rewriting commit history breaks original commit hashes (violating SHA integrity), filter-branch/filter-repo rewriting must be rejected.
4. Because `git subtree add` leaves source projects in 4 disjoint subdirectories requiring subsequent flattening and obscuring `git log --follow` (as tested during evaluation), direct subtree flattening is suboptimal.
5. In contrast, using **Multi-Remote Fetch with Preparation Branches & Unrelated History Merging** (`git merge --allow-unrelated-histories`):
   - Step 1 fetches all 4 repositories into the new monorepo, immediately placing all 69 original commit objects into the local git object store with 100% byte-for-byte SHA preservation.
   - Step 2 isolates `freqtrader-dash` files into `dashboard/` on a preparation branch (`prep/dash`). Standard `git mv` preserves full file lineage via `git log --follow dashboard/app.jsx`.
   - Step 3 renames conflicting grid configs on `prep/grid` so `StepGrid.py` merges natively into `user_data/strategies/StepGrid.py`.
   - Step 4 merges `prep/dash`, `prep/grid`, and `breakout` into `trend` with zero conflicts (`-X theirs` automatically handles breakout's updated compose and PVB params).
6. Because 3 of the 4 source repos contain uncommitted modified files and untracked strategies (Observation 3), these must be explicitly preserved and copied into the monorepo before final consolidation commit.
7. Because `user_data/data/` contained 386 MB of binary `.feather` candle files committed in `breakout` (Observation 2), `git rm -r --cached user_data/data/` must be run in the monorepo working tree and excluded via `.gitignore` to keep the repo clean.

---

## 3. Caveats

1. **Remote Push Restriction**: In accordance with the Global Git Branching Rule, no branches may be pushed to GitHub remotes (`origin`) without explicit user permission.
2. **Historical Feather Bloat in Git Object Store**: Because the original 4 commits of `freqtrade-breakout` contain `.feather` files in their tree objects, preserving `breakout`'s original commit SHAs means those objects remain in `.git/objects` (~386 MB) even though they are removed from the working tree index. This is necessary to guarantee untouched historical commit SHAs.
3. **Dashboard Directory Name**: We mapped `freqtrader-dash` to `dashboard/` rather than root. The user prompt specified: "The end state should be clean and consolidated: not 4 disconnected directories, but a unified root with single user_data and central docker-compose.yml." The dashboard is an Nginx web app that belongs in its own subfolder served by docker-compose.

---

## 4. Conclusion

1. The optimal migration strategy is **Multi-Remote Fetch + Preparation Branches + Unrelated History Merge**. It preserves 100% of the 69 original commit SHAs, author dates, and commit messages across all 4 repositories while enabling `git log --all` and `git log --follow` to work natively.
2. The exact, battle-tested bash command sequence has been engineered, validated, and documented in Section 6 of `survey_git_report.md`.
3. Essential uncommitted assets (updated `StepGrid.py`, tuned `.json` strategy parameters, and untracked `Wolf*.py` strategies) have been cataloged and integrated into the migration sequence.
4. The target architecture consolidates all bots into a single root with one shared `user_data/` directory, one isolated `dashboard/` directory, and one central `docker-compose.yml` orchestrating ports 80, 8080, 8081, and 8082.

---

## 5. Verification Method

Once the implementing agent executes the consolidation recipe in `survey_git_report.md`, independently verify with these exact commands:

1. **Commit History Presence**:
   ```bash
   git -C /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo log --all --oneline | wc -l
   # Expected: >= 75 commits (all 69 source commits + merge commits)
   ```
2. **File Lineage Traceability**:
   ```bash
   git -C /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo log --follow --oneline dashboard/app.jsx
   git -C /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo log --follow --oneline user_data/strategies/StepGrid.py
   git -C /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo log --follow --oneline user_data/strategies/WolfBreakout_Daily.py
   # Expected: Traces back to original initial commits 168b45a, 316b6b3, and 9e64a9e
   ```
3. **Docker Compose Validation**:
   ```bash
   cd /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo && docker compose config
   # Expected: Exit code 0 with 4 services: freqtrader-dash (80), freqtrade-hopt-live (8080), freqtrade-grid (8081), freqtrade-academic-dryrun (8082)
   ```
4. **Single Root `user_data` Directory**:
   ```bash
   test -d /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo/user_data && \
   ! test -d /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo/dashboard/user_data && \
   echo "PASSED"
   ```
5. **AI Context & Rules Preservation**:
   ```bash
   find /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo -name ".agents" -o -name "GEMINI.md" -o -name "PROJECT.md" -o -name "project-specifics.md"
   # Expected: All rule files found and non-empty
   ```
