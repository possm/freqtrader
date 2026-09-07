# AI Context Preservation, Rules Unification & Cleanup Survey Report

**Author**: survey_monorepo_explorer_3 (AI Context, Rules, Obsolete Cleanup & Constraints Specialist Explorer)  
**Date**: 2026-09-07T15:30:00+02:00  
**Target Monorepo**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo`  
**Source Repositories**:
1. `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout`
2. `/Users/matthijsdrenth/IdeaProjects/freqtrade-grid`
3. `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend`
4. `/Users/matthijsdrenth/IdeaProjects/freqtrader-dash`

---

## 1. Executive Summary

This investigation performed a comprehensive, read-only survey across all four target repositories to identify:
1. **AI instruction and context files** requiring strict preservation and unification (`.agents/`, `GEMINI.md`, rules, workflows).
2. **User rules and constraints** governing git branching, VPS deployment, frontend rendering, and hyperopt safety.
3. **Obsolete, redundant, and temporary artifacts** targeted for cleanup, totaling **over 2.0 Gigabytes and >2,000 files** across the repositories.
4. **Programmatic validation design** to guarantee 100% preservation of AI context while verifying zero residual clutter.

### Key Takeaways
- **AI Context Integrity**: `freqtrade-breakout/.agents` is the superset containing all 32 agent workspaces from `freqtrade-trend`, plus active orchestrator and survey agent workspaces. `freqtrader-dash/.agents/rules/project-specifics.md` holds critical frontend architecture rules. `freqtrade-grid` has no existing AI context.
- **Rule Unification**: A single, root-level `GEMINI.md` and root `.cursorrules` in `freqtrade-monorepo` can unify the Global Git Branching Rule, the multi-service VPS deployment workflow for `vps-matthijs-trader`, hyperopt parameter leak guards, and dashboard Babel cache-busting requirements without conflicts.
- **Cleanup Potential**: An estimated **~2.05 GB** of temporary logs, old backtest archives, hyperopt dumps, node_modules, and an accidental 77MB pytest coverage trace dump (`coverdir`) can be safely eliminated, resulting in a lean, fast monorepo.

---

## 2. Comprehensive Inventory of AI Instruction & Context Files

### 2.1 Repository-by-Repository AI File Inventory

| Repository | `.agents/` Directory | `GEMINI.md` | Third-Party AI Files (`.cursorrules`, `.aider*`, `.copilot*`) | Other Context / Reports |
|---|---|---|---|---|
| **freqtrade-breakout** | **37 workspaces** + `ORIGINAL_REQUEST.md` (Tracked in git) | **Present** (13 lines, identical to trend) | None | `PROJECT.md`, `reports/ACADEMIC_STRATEGY_REPORT.md`, `user_data/logs/backtest_results.md` |
| **freqtrade-grid** | None | None | None | None |
| **freqtrade-trend** | **32 workspaces** (Untracked duplicate of breakout) | **Present** (13 lines, identical to breakout) | None | `PROJECT.md`, `reports/ACADEMIC_STRATEGY_REPORT.md` |
| **freqtrader-dash** | **1 workspace** (`.agents/rules/project-specifics.md`) | None | None | `README.md`, `plan.md` |

### 2.2 Detailed Breakdown of `.agents/`

#### `freqtrade-breakout/.agents/` (Primary AI Context Source)
Contains 37 subdirectories and `ORIGINAL_REQUEST.md`:
- **Active Task Workspaces**:
  - `orchestrator_3/` (Active Monorepo Project Orchestrator)
  - `survey_monorepo_explorer_1/` (Git & Structure Survey)
  - `survey_monorepo_explorer_2/` (Architecture & Docker Survey)
  - `survey_monorepo_explorer_3/` (AI Context & Cleanup Survey - current agent)
  - `sentinel/` (Project Sentinel with updated 2026-09-07 briefing & handoff)
- **Historical Workspaces from Previous Milestones**:
  - `orchestrator/`, `orchestrator_2/`
  - `survey_explorer_1/`, `survey_explorer_2/`, `survey_explorer_3/`
  - `survey2_explorer_quant/`, `survey2_explorer_datascientist/`, `survey2_explorer_riskmanager/`
  - `m1_worker_1/`, `m1_worker_hvrspb/`, `m1_worker_remediation/`
  - `m1_reviewer_1/`, `m1_reviewer_2/`, `m1_reviewer_hvrspb_1/`, `m1_reviewer_hvrspb_2/`
  - `m1_challenger_1/`, `m1_challenger_2/`, `m1_challenger_hvrspb_1/`, `m1_challenger_hvrspb_2/`
  - `m1_explorer_1/`, `m1_explorer_2/`, `m1_explorer_3/`, `m1_fix_explorer_1/`, `m1_fix_explorer_2/`, `m1_fix_explorer_3/`
  - `m1_auditor_1/`, `m1_auditor_hvrspb_1/`
  - `m2_worker_1/`, `m2_worker_2/`, `m2_worker_3/`, `m3_worker_1/`
  - `victory_auditor_1/`
- **Anomalous Content in `.agents/m1_reviewer_1/`**:
  - Contains `coverdir/` with **1,684 files (77 MB)** of Python library coverage traces (`aiohttp`, `numpy`, `scipy`, `sqlalchemy`, etc.). This violates the `.agents` metadata-only protocol and represents temporary test residue.

#### `freqtrade-trend/.agents/`
- Contains identical copies of the 32 historical workspaces present in `freqtrade-breakout`.
- Verified via `diff -qr --exclude='coverdir'`: There are **zero unique agent workspaces or unique agent files** in `freqtrade-trend` that do not already exist in `freqtrade-breakout`.
- `ORIGINAL_REQUEST.md` in `freqtrade-breakout` is a strict superset of the trend version (includes Milestone 3).

#### `freqtrader-dash/.agents/`
- Contains `.agents/rules/project-specifics.md` (4,576 bytes).
- Contains vital frontend domain knowledge:
  1. In-browser React 18 / Babel compilation rules.
  2. Cache-busting requirement (`?v=[timestamp]` in `index.html`).
  3. Freqtrade REST API profit nuances (`profit_closed_coin` vs `profit_all_coin`).
  4. Multi-bot compatibility rules (`nr_of_successful_entries` flag check for DCA bots).
  5. Dual-viewport testing (mobile `< 768px` vs desktop).
  6. Hyperopt parameter leak risk in live bots.

---

## 3. User Rules & Constraints Analysis

### 3.1 Global Git Branching Rule (Mandatory Across All Agents)
```markdown
# Global Git Branching Rule
Wanneer je aan code werkt, maak dan ALTIJD eerst een nieuwe git branch aan voordat je wijzigingen doorvoert of commits maakt. Commit nooit direct naar de main of master branch.

Daarnaast mag je NOOIT zelfstandig code pushen naar een remote (bijv. GitHub met `git push`), tenzij de gebruiker hier expliciet om vraagt. Dit geldt voor ALLE branches, dus óók voor tijdelijke branches of reeds gepushte feature branches. Wacht altijd op toestemming van de gebruiker (zoals "push maar") voordat je een push uitvoert.
```

### 3.2 Freqtrade VPS Deployment Workflow (`GEMINI.md`)
Found identically in `freqtrade-breakout/GEMINI.md` and `freqtrade-trend/GEMINI.md`:
```markdown
# Freqtrade VPS Deployment Workflow
Wanneer je wijzigingen doorvoert of nieuwe strategieën live zet in deze repository, volg dan ALTIJD exact deze workflow:

1. **Commit**: Pas de code aan en maak een git commit (zorg dat je op een nieuwe branch zit conform de globale regels).
2. **Vraag Permissie**: Push nooit zelfstandig. Vraag eerst toestemming aan de gebruiker.
3. **Sync met VPS**: 
   Zodra je permissie hebt, push je de branch en gebruik je rsync om de bestanden met de VPS te synchroniseren. Zorg ervoor dat data, logs en databases ALTIJD uitgesloten worden:
   `rsync -avz --exclude '.git' --exclude 'user_data/data' --exclude 'user_data/logs' --exclude 'user_data/hyperopt_results' --exclude 'user_data/backtest_results' --exclude '*.sqlite*' ./ vps-matthijs-trader:~/freqtrade-wolf/`
4. **Valideer**: 
   Herstart na de sync altijd de container op de VPS en check de logs om te valideren dat de strategie succesvol en zonder fouten laadt:
   `ssh vps-matthijs-trader "cd freqtrade-wolf && docker compose up -d freqtrade-hopt-live && sleep 5 && docker compose logs --tail=50 freqtrade-hopt-live"`
```

### 3.3 Live VPS Reality Check (`vps-matthijs-trader`)
Live inspection of `vps-matthijs-trader` revealed the following running containers:
1. `freqtrade-wolf-hopt-live` (port `8080`): Live production trading bot (currently running in `~/freqtrade-wolf`).
2. `freqtrade-wolf-academic-dryrun` (port `8082`): Academic dry-run bot (`WolfBreakout_PVB`).
3. `freqtrader-dash` (port `80`): Nginx web dashboard (running in `~/freqtrader-dash`).
4. `code-server-agy` (port `8443`): Remote IDE container.
*(Note: `freqtrade-grid` on port `8081` has a directory `~/freqtrade-grid` on the VPS but is currently inactive).*

---

## 4. AI Context Preservation & Monorepo Consolidation Design

### 4.1 `.agents/` Consolidation Architecture
To preserve complete AI history without collision or loss:
1. **Root `.agents/`**: Copy the entire `.agents/` hierarchy from `freqtrade-breakout/.agents/` to the monorepo root. This preserves:
   - All 37 agent workspaces (`sentinel`, `orchestrator_3`, historical explorers/reviewers/challengers/auditors).
   - Complete verbatim `ORIGINAL_REQUEST.md` capturing all three milestones.
2. **Dashboard Rules Preservation**: Place `freqtrader-dash/.agents/rules/project-specifics.md` into:
   - Root `.agents/rules/project-specifics.md` (or `.agents/rules/dash-specifics.md`).
   - If the dashboard code is placed under a subdirectory (e.g. `dash/` or `freqtrader-dash/`), create a symlink or mirror `dash/.agents/rules/project-specifics.md` so per-project tooling automatically finds it.
3. **Prune Coverage Residue**: Remove `.agents/m1_reviewer_1/coverdir/` (77 MB of library trace dumps) so `.agents/` remains strictly clean metadata.

### 4.2 Proposed Consolidated Root `GEMINI.md`
The root `GEMINI.md` in `freqtrade-monorepo` should merge all operational workflows into a single authoritative document:

```markdown
# Freqtrade Monorepo Operational & Deployment Workflow

## 1. Global Git Branching Rule
Wanneer je aan code werkt, maak dan ALTIJD eerst een nieuwe git branch aan voordat je wijzigingen doorvoert of commits maakt. Commit nooit direct naar de main of master branch.
Daarnaast mag je NOOIT zelfstandig code pushen naar een remote (bijv. GitHub met `git push`), tenzij de gebruiker hier expliciet om vraagt. Dit geldt voor ALLE branches. Wacht altijd op expliciete toestemming van de gebruiker (zoals "push maar").

## 2. Monorepo VPS Deployment Workflow
Wanneer je wijzigingen doorvoert in de bots, configuraties of dashboard:
1. **Commit**: Zorg voor een schone commit op een feature branch.
2. **Permissie**: Vraag expliciet toestemming aan de gebruiker voor de push/sync.
3. **Sync met VPS**:
   Gebruik `rsync` om de monorepo naar `vps-matthijs-trader` te synchroniseren. Zorg dat data, logs, hyperopt-resultaten, backtests, lokale databases en node_modules ALTIJD worden uitgesloten:
   ```bash
   rsync -avz --delete \
     --exclude '.git' \
     --exclude 'user_data/data' \
     --exclude 'user_data/logs' \
     --exclude 'user_data/hyperopt_results' \
     --exclude 'user_data/backtest_results' \
     --exclude '*.sqlite*' \
     --exclude 'node_modules' \
     ./ vps-matthijs-trader:~/freqtrade-monorepo/
   ```
4. **Valideer Containers**:
   Herstart de betreffende services of de gehele stack via docker compose:
   ```bash
   ssh vps-matthijs-trader "cd freqtrade-monorepo && docker compose up -d && sleep 5 && docker compose ps"
   ```
   Valideer specifieke logs op runtime fouten:
   - Live Trend/Breakout Bot: `docker compose logs --tail=50 freqtrade-hopt-live`
   - Academic Dry-Run: `docker compose logs --tail=50 freqtrade-academic-dryrun`
   - Grid Bot: `docker compose logs --tail=50 freqtrade-grid`
   - Dashboard: `docker compose logs --tail=50 freqtrader-dash`

## 3. Dashboard Frontend Specifics (`dash/`)
- **In-browser Babel**: Geen npm build step. JSX wordt runtime in de browser gecompileerd.
- **Cache-Busting**: Bij wijziging van een `.jsx` bestand, update ALTIJD het query-parameter versienummer in `index.html` (bijv. `src="api.jsx?v=[timestamp]"`).
- **Multi-Bot Defensief**: Gebruik `nr_of_successful_entries` om DCA grids te herkennen, nooit `orders.length > 1`.
- **P&L Semantiek**: `summary.totalPnl` = Closed Profit (`profit_closed_coin`). Unrealized profit wordt runtime opgeteld.
- **Testing**: Test UI-wijzigingen altijd op zowel desktop als mobiele viewports (`< 768px`).

## 4. Hyperopt Safety & Parameter Overrides
- Voer `freqtrade hyperopt` NOOIT direct uit in de live strategieën map (`user_data/strategies/`). Freqtrade genereert automatisch `<strategy_name>.json` bestanden die bij een bot herstart de code overschrijven.
- Verifieer vóór container herstart dat er geen onbedoelde `.json` bestanden in `user_data/strategies/` staan.
```

### 4.3 Proposed Monorepo `.cursorrules`
To support Cursor / Windsurf / Copilot IDEs and satisfy the Acceptance Criterion:
```markdown
# Freqtrade Monorepo AI Agent Guidelines

1. Follow the Global Git Branching Rule:
   - Always create a new feature branch before making changes or commits.
   - Never commit to main or master.
   - Never run `git push` without explicit user permission.

2. Architecture:
   - Single central `docker-compose.yml` orchestrates all services:
     - `freqtrade-hopt-live` (Port 8080)
     - `freqtrade-grid` (Port 8081)
     - `freqtrade-academic-dryrun` (Port 8082)
     - `freqtrader-dash` (Port 80)
   - Exactly one unified `user_data/` directory at the root level serving all Freqtrade bots.
   - Dashboard source located in `dash/` (or `freqtrader-dash/`).

3. Safety & Hygiene:
   - Never commit `*.sqlite*`, `*.log`, `__pycache__`, or `node_modules`.
   - Never run hyperopt in `user_data/strategies/` without cleaning generated `.json` files.
   - Always bump cache-busting `?v=` timestamp in `index.html` when altering `.jsx` files.
```

---

## 5. Inventory of Obsolete Files & Cleanup Targets

A detailed audit across all 4 repositories identified **~2.05 GB** of obsolete, redundant, and temporary files.

### 5.1 Categorized Cleanup Inventory

| Category | File Pattern / Location | Count / Size | Action | Rationale |
|---|---|---|---|---|
| **Caches** | `*/.pytest_cache/` | 2 dirs (~40 KB) | **DELETE** | Local pytest runtime cache |
| **Caches** | `freqtrader-dash/node_modules/` | 1 dir (**46 MB**) | **DELETE** | Leftover from local puppeteer test; dash has no Node toolchain |
| **Caches** | `*/__pycache__/` | Multiple dirs | **DELETE** | Python compiled bytecode |
| **OS Files** | `*/.DS_Store` | Multiple files | **DELETE** | macOS Finder metadata |
| **Coverage Traces** | `.agents/m1_reviewer_1/coverdir/` | **1,684 files (77 MB)** | **DELETE** | Pytest `--cov` dump inside `.agents/`; violates metadata-only rule |
| **Hyperopt Results** | `user_data/hyperopt_results/` | Breakout: **1.4 GB**, Trend: **427 MB** | **DELETE / EXCLUDE** | Old hyperopt pickle and epoch dumps (`.fthypt`, `.pkl`) |
| **Backtest Results** | `user_data/backtest_results/` | Breakout: **16 MB**, Trend: **38 MB** | **DELETE / EXCLUDE** | Old zip archives and `.meta.json` from historical test runs |
| **Local Databases** | `user_data/tradesv3*.sqlite*` | ~15 files (**~15 MB**) | **DELETE / GITIGNORE** | Local trade DBs, WAL, and SHM files; live DBs reside on VPS |
| **DB / Config Backups**| `user_data/*.bak*`, `user_data/config*.bak` | 5+ files | **DELETE** | Temporary `.bak` files from previous edits |
| **Temporary Logs** | Root `*.log` (e.g. `hyperopt_pvb_mac.log` 1.1MB) | ~12 files (**~1.5 MB**) | **DELETE** | Old execution logs sitting in project roots |
| **Temporary Logs** | `user_data/logs/*.log` | 15 files (**~750 KB**) | **DELETE** | Expired local run logs |
| **Benchmark Dumps** | Root `result_*.txt` (in breakout) | 14 files (~260 KB) | **DELETE** | Ad-hoc terminal text dumps from hyperopt/backtest runs |
| **Scratch Scripts** | `freqtrader-dash/unify.py`, `plan.md` | 2 files | **DELETE** | One-off regex replacement script and temporary scratch plan |
| **Test Scripts** | `freqtrader-dash/test-puppeteer*.js`, `test.js` | 7 files | **DELETE** | One-off ad-hoc puppeteer test scripts (keep `screenshot.js`) |
| **Screenshot Images** | `freqtrader-dash/screenshot*.png` | 3 files (~230 KB) | **DELETE** | Temporary visual regression screenshots |
| **Root Scratch Files** | `2026-05-09` (in breakout & trend) | 2 files (0 bytes) | **DELETE** | Accidental 0-byte file created in root |
| **Root Scratch Scripts**| `rename_tf.py`, `user_data/btc_price*.py`, `user_data/test_fee.py` | 5 files | **DELETE** | Scratch scripts; replaced by active strategy code |
| **Empty Scaffold Dirs**| `freqaimodels/`, `hyperopts/`, `notebooks/`, `plot/`, `strategies/` (in root) | 5 dirs (0 files) | **DELETE** | Empty scaffold directories left over in project root |
| **Root Strategy Clones**| `WolfCustomSwingCH.py`, `WolfMR_4h_btc_noMFI.py`, `WolfTrend_EMA_hopt_tuned.py` | 3 files (~20 KB) | **DELETE** | Older clones in root; canonical versions live in `user_data/strategies/` |
| **Lockfiles** | `user_data/hyperopt.lock` | 1 file | **DELETE** | Stale hyperopt process lockfile |

### 5.2 Summary of Disk Space Reclaimed
$$\text{Total Space Reclaimed} \approx 1,400\,\text{MB (breakout hopt)} + 427\,\text{MB (trend hopt)} + 77\,\text{MB (coverdir)} + 54\,\text{MB (backtests)} + 46\,\text{MB (node\_modules)} + 15\,\text{MB (sqlite)} + 3\,\text{MB (logs)} \approx \mathbf{2.02\,\text{GB}}$$

---

## 6. Retention vs Deletion Rules Matrix

| Component | Target Monorepo Location | Action | Rule & Rationale |
|---|---|---|---|
| **AI Context Files** | `/.agents/` | **RETAIN & MERGE** | Monorepo root `.agents/` receives all 37 agent workspaces from breakout + dash rules. |
| **User Instructions** | `/GEMINI.md`, `/.cursorrules` | **RETAIN & UNIFY** | Unified root files establishing Git branching, VPS workflow, and multi-bot standards. |
| **Live & Dry-Run Strategies** | `/user_data/strategies/` | **RETAIN** | All active strategies (`WolfBreakout_Daily.py`, `WolfBreakout_PVB.py`, `StepGrid.py`, `WolfTrend_1h_Candidate.py`, `WolfTrend_EMA_hopt_tuned.py`). |
| **Active Strategy JSONs** | `/user_data/strategies/*.json` | **RETAIN (AUDITED)** | Retain intended hyperopt parameters (`WolfBreakout_Daily.json`, `WolfBreakout_PVB.json`, etc.); document leak risks. |
| **Active Bot Configs** | `/user_data/` or `/` | **RETAIN & RENAME** | Consolidate and disambiguate configs (`config_trend_hopt.json`, `config_academic_dryrun.json`, `config_grid.json`). |
| **Unit Test Suites** | `/tests/` | **RETAIN** | Keep all verified unit tests (`test_wolfbreakout_pvb.py`, `test_boundary_sensitivity.py`, etc.). |
| **Analytical Reports** | `/reports/` | **RETAIN** | Preserve `ACADEMIC_STRATEGY_REPORT.md` and move `user_data/logs/backtest_results.md` to `/reports/`. |
| **Dashboard Web App** | `/dash/` (or `/freqtrader-dash/`) | **RETAIN** | Core frontend files (`index.html`, `app.jsx`, `api.jsx`, `views.jsx`, `components.jsx`, `nginx.conf`, `Dockerfile`). |
| **Dashboard Tooling** | `/dash/screenshot.js` | **RETAIN** | Retain standard visual parity verification tool. |
| **Environment Template** | `/.env.example` | **RETAIN & EXPAND** | Document all environment variables for all services; strictly gitignore `.env`. |
| **Market Candle Data** | `/user_data/data/` | **GITIGNORE** | Exclude from git tracking and VPS sync. Can be downloaded on demand via `download_data.sh`. |
| **Caches & node_modules** | Anywhere | **DELETE** | Remove `node_modules/`, `.pytest_cache/`, `__pycache__/`, `.DS_Store`. |
| **Test & Coverage Residue**| `.agents/m1_reviewer_1/coverdir/` | **DELETE** | Delete all 1,684 `.cover` files from `.agents/`. |
| **Backtest & Hyperopt Dumps**| `user_data/backtest_results/`, `hyperopt_results/` | **DELETE / PURGE** | Delete old `.zip`, `.fthypt`, `.pkl` artifacts. |
| **Local SQLite Files** | `user_data/*.sqlite*` | **DELETE & GITIGNORE** | Keep SQLite local databases out of version control and VPS sync. |
| **Logs & Text Dumps** | Root & `user_data/logs/` | **DELETE & GITIGNORE** | Purge `*.log` and `result_*.txt`. |

---

## 7. Programmatic Validation Design

### 7.1 Evaluation of Acceptance Criterion
The acceptance criterion defined in `ORIGINAL_REQUEST.md` is:
```bash
find . -name ".agents" -o -name "GEMINI.md" -o -name ".cursorrules"
```

In the migrated monorepo, executing this command from the repository root will find:
1. `./.agents` (Root directory containing all 37 historical/active agent records + dashboard rules).
2. `./GEMINI.md` (Authoritative instructions for Git, VPS deployment, and multi-bot execution).
3. `./.cursorrules` (IDE rules ensuring third-party AI assistants adhere to monorepo conventions).
*(If dashboard rules are preserved in a subdirectory, `./dash/.agents` will also be discovered).*

### 7.2 Comprehensive Automated Validation Script
To verify both AI preservation and obsolete artifact removal during Milestone M4, the following programmatic script is specified:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "RUNNING MONOREPO AI CONTEXT & CLEANUP VALIDATION"
echo "============================================================"

FAIL=0

# 1. Check AI Instruction Files Preservation
echo "[1/6] Verifying AI Context Files..."
for required_file in ".agents" "GEMINI.md" ".cursorrules"; do
  if [ ! -e "$required_file" ]; then
    echo "❌ Missing required AI context file: $required_file"
    FAIL=1
  else
    echo "  ✅ Found $required_file"
  fi
done

# Verify critical content inside .agents
if [ ! -f ".agents/ORIGINAL_REQUEST.md" ]; then
  echo "❌ Missing .agents/ORIGINAL_REQUEST.md"
  FAIL=1
fi
if [ ! -d ".agents/orchestrator_3" ]; then
  echo "❌ Missing .agents/orchestrator_3 workspace"
  FAIL=1
fi
if [ ! -f ".agents/rules/project-specifics.md" ] && [ ! -f "dash/.agents/rules/project-specifics.md" ]; then
  echo "❌ Missing dashboard project-specifics.md rules"
  FAIL=1
fi

# 2. Verify GEMINI.md Rules Content
echo "[2/6] Verifying GEMINI.md Rule Content..."
grep -q "Global Git Branching Rule" GEMINI.md || { echo "❌ GEMINI.md missing Git Branching Rule"; FAIL=1; }
grep -q "vps-matthijs-trader" GEMINI.md || { echo "❌ GEMINI.md missing VPS sync target"; FAIL=1; }
grep -q "Hyperopt" GEMINI.md || { echo "❌ GEMINI.md missing Hyperopt safety guidelines"; FAIL=1; }

# 3. Verify Absence of Obsolete Files in Git Tracking
echo "[3/6] Verifying Clean Git Index (no tracked obsolete artifacts)..."
TRACKED_SQLITE=$(git ls-files "*.sqlite*" | wc -l)
if [ "$TRACKED_SQLITE" -gt 0 ]; then
  echo "❌ Git index contains $TRACKED_SQLITE tracked SQLite files!"
  FAIL=1
fi

TRACKED_LOGS=$(git ls-files "*.log" | wc -l)
if [ "$TRACKED_LOGS" -gt 0 ]; then
  echo "❌ Git index contains $TRACKED_LOGS tracked log files!"
  FAIL=1
fi

TRACKED_RESULTS=$(git ls-files "user_data/hyperopt_results/*" "user_data/backtest_results/*" | wc -l)
if [ "$TRACKED_RESULTS" -gt 0 ]; then
  echo "❌ Git index contains $TRACKED_RESULTS tracked hyperopt/backtest result files!"
  FAIL=1
fi

# 4. Verify Absence of .agents/m1_reviewer_1/coverdir
echo "[4/6] Verifying .agents/ Metadata Compliance (no coverdir)..."
if [ -d ".agents/m1_reviewer_1/coverdir" ]; then
  echo "❌ .agents/m1_reviewer_1/coverdir still exists (77MB coverage residue)!"
  FAIL=1
fi

# 5. Verify Clean Workspace Artifacts
echo "[5/6] Verifying Workspace Hygiene..."
if [ -d "node_modules" ] || [ -d "dash/node_modules" ]; then
  echo "❌ Found obsolete node_modules directory!"
  FAIL=1
fi

DS_STORE_COUNT=$(find . -name ".DS_Store" | wc -l)
if [ "$DS_STORE_COUNT" -gt 0 ]; then
  echo "❌ Found $DS_STORE_COUNT .DS_Store files in workspace!"
  FAIL=1
fi

if [ -f "2026-05-09" ]; then
  echo "❌ Found accidental 0-byte file 2026-05-09!"
  FAIL=1
fi

# 6. Verify User Data Structure
echo "[6/6] Verifying Single user_data Directory..."
USERDATA_COUNT=$(find . -maxdepth 2 -name "user_data" -type d | wc -l)
if [ "$USERDATA_COUNT" -ne 1 ]; then
  echo "❌ Expected exactly 1 user_data directory at root, found: $USERDATA_COUNT"
  FAIL=1
fi

echo "============================================================"
if [ "$FAIL" -eq 0 ]; then
  echo "🎉 ALL VALIDATION CHECKS PASSED: AI context preserved & obsolete files purged!"
  exit 0
else
  echo "⚠️ VALIDATION FAILED: See errors above."
  exit 1
fi
```

---

## 8. Actionable Recommendations for Implementation Phases

### Milestone M1: History-Preserving Migration
- Use `git subtree` or unrelated-history merge to import all 4 repositories into `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo`.
- Ensure uncommitted changes in `freqtrade-grid` (`StepGrid.py` and `config_backtest.json`) and `freqtrade-breakout` are committed to dedicated branches prior to subtree pull so zero work is lost.

### Milestone M2: Architectural Consolidation
- Unify all Freqtrade environments into a single root `user_data/` containing:
  - `user_data/strategies/` (consolidating breakout, trend, and grid strategies).
  - `user_data/` configs (disambiguating names: `config_trend_hopt.json`, `config_academic_dryrun.json`, `config_grid.json`).
- Structure the dashboard into `dash/` (or `freqtrader-dash/`).
- Create single central `docker-compose.yml` defining `freqtrade-hopt-live` (8080), `freqtrade-grid` (8081), `freqtrade-academic-dryrun` (8082), and `freqtrader-dash` (80).

### Milestone M3: Cleanup & AI Rule Preservation
- Copy `.agents/` from `freqtrade-breakout` to monorepo root.
- Copy `.agents/rules/project-specifics.md` from `freqtrader-dash` into `.agents/rules/`.
- Purge `.agents/m1_reviewer_1/coverdir/` (77 MB).
- Write consolidated `GEMINI.md` and `.cursorrules` at root.
- Execute cleanup of all Category A–H obsolete files (~2.05 GB).
- Run the programmatic validation script to confirm 100% compliance.
