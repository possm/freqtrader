## 2026-09-04T15:43:03Z

You are Milestone 2 Worker (Data Scientist & Hyperopt Specialist).
Your working directory is /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_1.
Read /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2/handoff.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_1/handoff.md, and /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_1/DISPATCH.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Critical Rules:
1. All work must be on branch `feat/academic-altcoin-strategy`. NEVER commit to main or master. NEVER run git push.
2. NEVER stop, restart, or touch the live production bot `freqtrade-wolf-hopt-live` on port 8080!
3. All remote commands on the VPS must use `docker compose run --rm freqtrade-hopt-live ...` to execute as isolated ephemeral tasks.
4. Always pass `--fee 0.0026` to hyperopt and backtest commands to strictly model Kraken taker fees (0.26%).
5. Use `-j 2` on VPS commands.

Tasks:
1. Sync strategy to VPS:
   rsync -avz --exclude '.git' --exclude 'user_data/data' --exclude 'user_data/logs' --exclude 'user_data/hyperopt_results' --exclude 'user_data/backtest_results' --exclude '*.sqlite*' ./ vps-matthijs-trader:~/freqtrade-wolf/
2. Verify strategy loaded on VPS:
   ssh vps-matthijs-trader "cd freqtrade-wolf && docker compose run --rm freqtrade-hopt-live list-strategies | grep WolfBreakout_PVB"
3. Run Hyperopt on VPS:
   Run hyperopt on Binance 1h data with Kraken fees `--fee 0.0026`, `--spaces buy roi stoploss trailing`, `--hyperopt-loss SharpeHyperOptLoss` (or ProfitHyperOptLoss), e.g. 100-150 epochs, `-j 2`.
4. Integrate the best parameters into `user_data/strategies/WolfBreakout_PVB.py`.
5. Run a full validation backtest on the VPS with `--fee 0.0026` and verify `Total profit %` > 10% after fees!
6. Verify local unit tests still pass:
   docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -m unittest discover -s tests -p "test_*.py" -v
7. Commit updated strategy on branch `feat/academic-altcoin-strategy` (DO NOT PUSH).
8. Produce detailed report in /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m2_worker_1/handoff.md following standard handoff structure.
9. Send completion message to parent orchestrator.
