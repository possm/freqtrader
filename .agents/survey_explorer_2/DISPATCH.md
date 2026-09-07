# Dispatch for Survey Explorer 2 (VPS Infrastructure)

## Mission
Investigate VPS environment (`vps-matthijs-trader`), existing freqtrade setup in `~/freqtrade-wolf/`, docker containers, existing data, and fee configuration.

## Instructions
1. Read `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md` and `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/orchestrator/DISPATCH.md`.
2. Inspect `vps-matthijs-trader` via SSH commands:
   - Check directory layout in `~/freqtrade-wolf/`.
   - Inspect `docker-compose.yml` and running containers (`docker ps` / `docker compose ps`).
   - Check available pairs and historical candle data in `~/freqtrade-wolf/user_data/data/`.
   - Check existing configs (`config.json`), exchange settings, and fee structures.
   - Determine how dry-run containers are set up and how logs are monitored.
3. Deliver your findings in `handoff.md` in `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2/handoff.md`.

## 2026-09-04T15:22:35Z
You are Survey Explorer 2 (VPS Infrastructure Explorer).
Your working directory is /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2.
Read /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/orchestrator/DISPATCH.md, and /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2/DISPATCH.md.

Tasks:
1. Use SSH to query the VPS `vps-matthijs-trader`:
   - Inspect ~/freqtrade-wolf/ directory, docker-compose configuration, and currently running docker containers.
   - Inspect available historical candle data in ~/freqtrade-wolf/user_data/data/ (exchanges, pairs, available timeframes and date spans).
   - Inspect configuration files on the VPS (e.g. config.json, dry-run configs, fee definitions, exchange settings).
   - Check how hyperopt is currently executed on the VPS and how dry-run containers are named and managed.
2. Summarize all findings and produce a comprehensive report in /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2/handoff.md following the standard handoff format (Observation, Logic Chain, Caveats, Conclusion, Verification).
3. Send a completion message to the parent orchestrator.
