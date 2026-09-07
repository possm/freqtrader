# Dispatch for Milestone 2 Worker 3 (Data Scientist & Hyperopt Specialist)

## Mission
Finish Milestone 2:
1. Check the completed hyperopt results on the VPS (`vps-matthijs-trader`).
2. Extract the best parameter configuration and integrate it into `user_data/strategies/WolfBreakout_PVB.py`.
3. Sync the updated strategy to `vps-matthijs-trader:~/freqtrade-wolf/` using rsync.
4. Run a validation backtest on the VPS with `--fee 0.0026` and verify that `Total profit %` is > 10% net after Kraken fees.
5. Verify local unit tests pass in Docker.
6. Commit the updated strategy to `feat/academic-altcoin-strategy` (DO NOT PUSH).
7. Deliver `handoff.md` in `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_3/handoff.md`.

## VPS Details & Predecessor Work
`m2_worker_2` executed the 100-epoch hyperopt run on the VPS before its connection timed out.
The hyperopt results file is located on the VPS in `~/freqtrade-wolf/user_data/hyperopt_results/`.
Inspect it via:
```bash
ssh vps-matthijs-trader "cd freqtrade-wolf && ls -lt user_data/hyperopt_results/"
ssh vps-matthijs-trader "cd freqtrade-wolf && docker compose run --rm freqtrade-hopt-live hyperopt-show --hyperopt-filename <latest_file.fthypt> --print-all"
```
If a new run or refinement is needed, run with `--fee 0.0026`, `-j 2`, and timerange `20240101-20241231` (or `20230101-20241231`).

## Rules
- Branch: `feat/academic-altcoin-strategy`. NEVER commit to main. NEVER run git push.
- NEVER touch live bot `freqtrade-wolf-hopt-live` on port 8080!
- Ephemeral containers only: `docker compose run --rm freqtrade-hopt-live ...`.
- Fees: Always pass `--fee 0.0026`.
- Acceptance Criterion: Total profit % > 10% net after Kraken fees in the validation backtest.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 2026-09-04T18:40:15Z
You are Milestone 2 Worker 3 (Data Scientist & Hyperopt Specialist).
Tasks:
1. Inspect the completed hyperopt results on the VPS.
2. Integrate best parameters into user_data/strategies/WolfBreakout_PVB.py.
3. Sync updated strategy to VPS.
4. Run validation backtest on VPS with --fee 0.0026 and confirm Total profit % > 10%.
5. Run unit tests in local Docker.
6. Commit updated strategy on branch feat/academic-altcoin-strategy.
7. Deliver handoff report.
8. Send completion message to parent orchestrator.

