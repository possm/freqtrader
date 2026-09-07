# BRIEFING — 2026-09-04T19:37:00Z

## Mission
Review WolfBreakout_HVRSPB.py focusing on risk management, exit logic, and hyperopt configuration; stress-test edge cases and verify test suite.

## 🔒 My Identity
- Archetype: reviewer_critic
- Roles: reviewer, critic
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_reviewer_hvrspb_2
- Original parent: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Milestone: Milestone 1: Strategy Implementation & Verification
- Instance: 2 of 2

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Reviewer 2 focus: risk management, exit logic, hyperopt configuration
- No pushing to remote without permission
- Integrity violation detection: check for hardcoded test results, dummy implementations, shortcuts, fabricated outputs, self-certifying work

## Current Parent
- Conversation ID: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Updated: 2026-09-04T19:37:00Z

## Review Scope
- **Files to review**: user_data/strategies/WolfBreakout_HVRSPB.py, tests/test_wolfbreakout_hvrspb.py, .agents/m1_worker_hvrspb/handoff.md
- **Interface contracts**: PROJECT.md, ORIGINAL_REQUEST.md
- **Review criteria**: Risk management, exit logic, custom_stoploss two-tier trailing stop, fast invalidation, hyperopt spaces, correctness, adversarial stress-testing, integrity violations

## Review Checklist
- **Items reviewed**: WolfBreakout_HVRSPB.py, tests/test_wolfbreakout_hvrspb.py, worker handoff.md, Freqtrade hyperopt engine
- **Verdict**: REQUEST_CHANGES
- **Unverified claims**: Worker claim that hyperopt spaces are ready across buy, sell, stoploss, and trailing spaces — FALSIFIED (crashes with KeyError).

## Attack Surface
- **Hypotheses tested**:
  1. Hyperopt spaces compatibility: Tested whether Freqtrade HyperOptimizer can evaluate `stoploss` and `trailing` spaces. Result: FAILED with fatal `KeyError: 'hard_stoploss'` and `KeyError: 'be_lock_margin'`.
  2. Facade parameter check: Tested whether `hard_stoploss` is used in strategy logic. Result: FAILED (dead-code facade).
  3. Two-tier trailing stoploss math: Verified `stoploss_from_open` at +3.5% open profit locks +0.8%, and +8.0% trails by 4.0%. Result: PASSED.
  4. Fast invalidation holding period: Checked whether `populate_exit_trend` respects 4-candle breathing room. Result: FAILED (unconditionally exits on candle close below midline).
- **Vulnerabilities found**:
  1. CRITICAL / INTEGRITY VIOLATION: `hard_stoploss` is an unused facade parameter that fatally crashes hyperopt.
  2. CRITICAL: `space="trailing"` on custom trailing parameters causes `KeyError: 'be_lock_margin'` during hyperopt.
  3. MAJOR: `populate_exit_trend` overrides and voids 4-candle breathing room in `custom_exit`.
- **Untested angles**: Live websocket execution on Kraken exchange.

## Key Decisions Made
- Verdict: REQUEST_CHANGES with 2 Critical findings (one tagged INTEGRITY VIOLATION for dead-code parameter facade) and 1 Major finding.

## Artifact Index
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_reviewer_hvrspb_2/DISPATCH.md — Dispatch instructions
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_reviewer_hvrspb_2/BRIEFING.md — Persistent working memory
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_reviewer_hvrspb_2/progress.md — Liveness heartbeat
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_reviewer_hvrspb_2/handoff.md — Review & adversarial challenge report
