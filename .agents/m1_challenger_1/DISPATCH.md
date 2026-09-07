# Dispatch for Milestone 1 Challenger 1 (Adversarial Stress & Lookahead)

## Mission
Adversarially challenge `WolfBreakout_PVB.py` for lookahead bias, price leaks, abnormal data handling, zero-volume bars, and extreme market conditions.

## Instructions
1. Read `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md`, `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md`, and `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_1/handoff.md`.
2. Empirically verify:
   - Does `WolfBreakout_PVB` exhibit any lookahead bias under adversarial perturbation tests?
   - How does it behave under extreme volatility shocks (flash crashes, zero-range candles, missing candles)?
   - Are entries and exits strictly causally separated?
3. Execute stress test scripts in Docker.
4. Deliver your handoff report to `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_challenger_1/handoff.md` with an explicit verdict: `APPROVE` or `REQUEST_CHANGES`.

## 2026-09-04T15:36:05Z
You are Milestone 1 Challenger 1 (Adversarial Stress & Lookahead Challenger).
Your working directory is /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_challenger_1.
Read /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_1/handoff.md, and /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_challenger_1/DISPATCH.md.

Tasks:
1. Adversarially challenge user_data/strategies/WolfBreakout_PVB.py for lookahead bias, price leaks, abnormal data handling, extreme volatility spikes, and zero-volume bars.
2. Run adversarial verification scripts in Docker.
3. Deliver your handoff report to /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_challenger_1/handoff.md with an explicit verdict: APPROVE or REQUEST_CHANGES.
4. Send a completion message to the parent orchestrator.
