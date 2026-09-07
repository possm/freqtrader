# BRIEFING — 2026-09-07T15:30:45+02:00

## Mission
Comprehensive survey of AI instruction and context preservation and obsolete cleanup targets across 4 repositories (freqtrade-breakout, freqtrade-grid, freqtrade-trend, freqtrader-dash) to inform monorepo consolidation.

## 🔒 My Identity
- Archetype: explorer
- Roles: AI Context, Rules, Obsolete Cleanup & Constraints Specialist
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_3/
- Original parent: 12ebc45b-1687-46e5-a9f5-8ac053b58478
- Milestone: monorepo_survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source files outside working directory
- Preserves all AI instruction and context files across all 4 repos (GEMINI.md, .agents, .cursorrules, .aider*, .github/copilot, etc.)
- Strict user rules analysis (Global Git Branching Rule, VPS Deployment Workflow)
- Clear retention vs deletion rules for cleanup targets

## Current Parent
- Conversation ID: 12ebc45b-1687-46e5-a9f5-8ac053b58478
- Updated: 2026-09-07T15:30:45+02:00

## Investigation State
- **Explored paths**:
  - `freqtrade-breakout`: `.agents/` (37 workspaces), `GEMINI.md`, `docker-compose.yml`, `user_data/`, `tests/`
  - `freqtrade-trend`: `.agents/` (32 workspaces), `GEMINI.md`, `docker-compose.yml`, `user_data/`
  - `freqtrade-grid`: root and `user_data/`, git status, uncommitted diffs
  - `freqtrader-dash`: `.agents/rules/project-specifics.md`, `README.md`, `plan.md`, `unify.py`, `node_modules`
  - Live VPS inspection on `vps-matthijs-trader` via SSH (running containers, ports, directories)
- **Key findings**:
  - `freqtrade-breakout/.agents` is a complete superset of `freqtrade-trend/.agents`. Zero unique files in trend agents.
  - `freqtrader-dash/.agents/rules/project-specifics.md` has essential frontend & hyperopt rules to preserve in monorepo root `.agents/rules/`.
  - Pytest coverage dump `.agents/m1_reviewer_1/coverdir/` has 1,684 files (77MB) violating metadata-only rules; targeted for deletion.
  - GEMINI.md in breakout and trend are identical. Proposed unified GEMINI.md merges Git branching rules, multi-bot VPS sync, dashboard Babel rules, and hyperopt safety.
  - Cleanup targets across 4 repos total ~2.02 GB (1.83 GB hyperopt dumps, 77 MB coverage traces, 54 MB backtests, 46 MB node_modules, 15 MB local sqlite, logs, and scratch scripts).
  - Designed programmatic validation script satisfying acceptance criterion `find . -name ".agents" -o -name "GEMINI.md" -o -name ".cursorrules"`.
- **Unexplored areas**: None. Survey is complete.

## Key Decisions Made
- Authored comprehensive survey report at `survey_ai_rules_cleanup_report.md`.
- Completed 5-component handoff report at `handoff.md`.

## Artifact Index
- DISPATCH.md — Recorded dispatch prompt
- BRIEFING.md — Working memory and status
- progress.md — Liveness heartbeat
- survey_ai_rules_cleanup_report.md — Comprehensive Survey Report (AI Context, Rules & Cleanup)
- handoff.md — Self-contained 5-component handoff report
