## 2026-09-04T19:12:36Z
You are the Risk Manager & Governance Explorer (Survey Explorer).

Working Directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_riskmanager
Project Root: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Original Request File: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md

MISSION:
Read ORIGINAL_REQUEST.md. Investigate risk management parameters, drawdown tolerance, capital allocation, and governance requirements for achieving >=10% net profit per month on Kraken Spot.

SCOPE & INVESTIGATION:
1. Assess the risk-return tradeoff:
   - To achieve >=10% monthly net return (>120% per year) on spot without leverage, what drawdown range is mathematically realistic and acceptable?
   - Formulate the Risk Manager's mandate: define maximum acceptable drawdown thresholds (e.g. 25-35% in spot crypto bull/consolidation phases), position sizing, max open trades, and exposure.
2. Kraken Spot Fee & Slippage modeling:
   - Taker fee 0.26%, maker fee 0.16%. How does fee drag impact short-term vs medium-term holding periods?
   - How to verify that fees are strictly and explicitly accounted for in backtests and hyperopts.
3. Structure and outline the required comprehensive markdown report:
   - Outline for `reports/10PERCENT_MONTH_REPORT.md` justifying why the strategy, drawdown, and risks are acceptable for this aggressive target.
4. Define verification gates and safety checks for subsequent phases.

CONSTRAINTS & RULES:
- Read-only investigation.
- Follow GEMINI.md and Git rules.
- Write your complete findings to `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_riskmanager/handoff.md`.
- Send a message to orchestrator when finished.
