# Dispatch for Milestone 1 Worker (Strategy Implementer & Test Worker)

## Mission
Execute Milestone 1: Create git branch `feat/academic-altcoin-strategy`, implement `user_data/strategies/WolfBreakout_PVB.py`, implement `tests/test_wolfbreakout_pvb.py`, run all tests in Docker, verify 100% pass, and commit to the new branch.

## File Ownership
You exclusively own and may modify or create:
- `user_data/strategies/WolfBreakout_PVB.py`
- `tests/test_wolfbreakout_pvb.py`
- `tests/__init__.py`

Do NOT touch or modify other files (such as `config_trend_hopt.json`, `docker-compose.yml`, or other strategies).

## Input References
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md` (MANDATORY)
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md`
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_1/handoff.md`
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_2/handoff.md`
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_3/handoff.md`
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_3/proposed_test_wolfbreakout_pvb.py`

## Instructions
1. Git Branching:
   - Check current branch. Switch to a new branch: `git checkout -b feat/academic-altcoin-strategy`.
   - Never commit to main.
   - NEVER push to remote (`git push` is forbidden without explicit user permission).
2. Strategy Implementation (`user_data/strategies/WolfBreakout_PVB.py`):
   - Implement `WolfBreakout_PVB` per the architectural blueprint in `m1_explorer_2/handoff.md`.
   - Incorporate `m1_explorer_3`'s vital fixes: pre-initialize `enter_long = 0` / `exit_long = 0`, and use `safe_low = dataframe["low"].clip(lower=1e-8)` to prevent NaN propagation.
   - Make sure `KrakenSlippageMixin` is mixed in, `atr_pct` is computed, and `timeframe = '1h'`.
3. Unit Test Implementation (`tests/test_wolfbreakout_pvb.py`):
   - Deploy the comprehensive 33-test suite from `.agents/m1_explorer_3/proposed_test_wolfbreakout_pvb.py` into `tests/test_wolfbreakout_pvb.py`.
   - Ensure `tests/__init__.py` exists.
4. Testing & Verification:
   - Run unit tests inside Docker:
     `docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -m unittest discover -s tests -p "test_*.py" -v`
   - Run Freqtrade strategy validation inside Docker:
     `docker run --rm -v $(pwd)/user_data:/freqtrade/user_data freqtradeorg/freqtrade:stable list-strategies`
   - Confirm all 33 unit tests pass (100%) and strategy loads cleanly.
5. Git Commit:
   - Stage ONLY the new files:
     `git add user_data/strategies/WolfBreakout_PVB.py tests/test_wolfbreakout_pvb.py tests/__init__.py`
   - Commit on branch `feat/academic-altcoin-strategy`:
     `git commit -m "feat(strategy): implement WolfBreakout_PVB and comprehensive unit test suite"`
   - Do NOT run `git push`.
6. Deliver `handoff.md` in `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_1/handoff.md` with complete test output, git status, and verification evidence.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 2026-09-04T15:33:11Z
You are Milestone 1 Worker (Strategy Implementer & Test Worker).
Your working directory is /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_1.
Read /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/orchestrator/DISPATCH.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md, and /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_1/DISPATCH.md.

Also review input handoffs:
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_1/handoff.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_2/handoff.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_3/handoff.md
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_3/proposed_test_wolfbreakout_pvb.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You exclusively own and may create/modify:
- user_data/strategies/WolfBreakout_PVB.py
- tests/test_wolfbreakout_pvb.py
- tests/__init__.py

Tasks:
1. Create and switch to new git branch: `git checkout -b feat/academic-altcoin-strategy`. Never commit directly to main or master. NEVER run git push.
2. Implement `user_data/strategies/WolfBreakout_PVB.py` based on the architectural blueprint in `m1_explorer_2/handoff.md` and the numerical fixes from `m1_explorer_3/handoff.md` (pre-initialize enter_long/exit_long, clip low at 1e-8).
3. Create `tests/test_wolfbreakout_pvb.py` and `tests/__init__.py` using the 33-test suite from `m1_explorer_3/proposed_test_wolfbreakout_pvb.py`.
4. Run all unit tests and strategy checks inside Docker:
   `docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -m unittest discover -s tests -p "test_*.py" -v`
   `docker run --rm -v $(pwd)/user_data:/freqtrade/user_data freqtradeorg/freqtrade:stable list-strategies`
   Ensure 100% tests pass.
5. Commit only the new files on branch `feat/academic-altcoin-strategy`:
   `git add user_data/strategies/WolfBreakout_PVB.py tests/test_wolfbreakout_pvb.py tests/__init__.py`
   `git commit -m "feat(strategy): implement WolfBreakout_PVB and comprehensive unit test suite"`
   DO NOT PUSH TO REMOTE.
6. Write your comprehensive report to /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_1/handoff.md following standard handoff structure.
7. Send a completion message to the parent orchestrator.

