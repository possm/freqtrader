# BRIEFING — 2026-09-07T13:39:15Z

## Mission
Execute Milestone 2 (Architectural Consolidation) in freqtrade-monorepo: create central docker-compose.yml, enforce single root user_data/ directory with consolidated bot configs and updated api_server configs, validate with docker compose config, and commit to feat/monorepo-consolidation.

## 🔒 My Identity
- Archetype: Architectural Consolidation Worker
- Roles: implementer, qa, specialist
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m2_worker/
- Original parent: 12ebc45b-1687-46e5-a9f5-8ac053b58478
- Milestone: Milestone 2 (Architectural Consolidation)

## 🔒 Key Constraints
- Verify working on branch `feat/monorepo-consolidation` in `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo`.
- Never commit directly to main or master.
- Never push to remote (`git push`) without explicit user permission.
- Central docker-compose.yml must define all 5 containers with exact port mappings, volume mounts (`./user_data:/freqtrade/user_data`), commands, and env_file.
- Single root `user_data/` directory only; ensure no `dashboard/user_data` directory exists.
- Consolidate and verify bot configs in `user_data/`: `config.json`, `config_grid.json`, `config_grid_backtest.json`, `config_academic_dryrun.json`, `config_breakout_daily.json`, and auxiliary configs.
- Update `api_server` configuration in all active bot configs: `"listen_ip_address": "0.0.0.0"` and `"CORS_origins": ["http://192.168.2.4", "http://192.168.2.4:80", "http://localhost", "http://127.0.0.1"]`.
- Validate with `docker compose config` (exit code 0).
- Generate reports in `.agents/m2_worker/`.

## Current Parent
- Conversation ID: 12ebc45b-1687-46e5-a9f5-8ac053b58478
- Updated: 2026-09-07T13:39:15Z

## Task Summary
- **What to build**: Central docker-compose.yml and unified bot configuration architecture in freqtrade-monorepo.
- **Success criteria**: docker compose config succeeds with exit 0, all configs present in user_data/ with correct api_server settings, dashboard/user_data absent, git branch clean and committed.
- **Interface contracts**: PROJECT.md and survey_arch_report.md
- **Code layout**: /Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo

## Key Decisions Made
- [TBD]

## Change Tracker
- **Files modified**: [TBD]
- **Build status**: [TBD]
- **Pending issues**: none

## Quality Status
- **Build/test result**: [TBD]
- **Lint status**: [TBD]
- **Tests added/modified**: [TBD]

## Loaded Skills
- None required

## Artifact Index
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m2_worker/DISPATCH.md` — Dispatch prompt
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m2_worker/m2_implementation_report.md` — Implementation report (to be written)
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/m2_worker/handoff.md` — Handoff report (to be written)
