---
name: freqtrader-dash-rules
description: Project specific rules and context for the freqtrader-dash dashboard.
trigger: always_on
---

# freqtrader-dash Project Specifics

- **Architecture:** This is an in-browser React 18 application with no build step. JSX is compiled live in the browser by Babel standalone.
- **Dependencies:** No Node toolchain, no npm, and no bundlers. Files are statically served by an Nginx container.
- **Deployment:** Deployment is typically done by `rsync`ing the updated source files to the target VPS (e.g., `vps-matthijs-trader`), followed by rebuilding and restarting the container using `docker compose up -d --build`.
- **API Backend:** Reads from Freqtrade's REST API (`/api/v1/...`) directly from the browser. credentials are saved in localStorage.

## Freqtrade API & Data Quirks
- **Profit Calculation**: In the `/api/v1/profit` endpoint, `profit_all_coin` is equal to Closed Profit + Open Unrealized Profit. To get strictly closed profit, you MUST use `profit_closed_coin`.
- **Dashboard Definitions**: In `api.jsx`, the variable `summary.totalPnl` must always represent strictly *Closed Profit*. Net Profit is calculated on-the-fly in the UI by adding `unrealizedPnl`.
- **Daily P&L Chart**: The Daily P&L bars (`DailyBars`) must strictly show closed profit only. Do not overlay or include unrealized profits in this specific chart.
- **Chronological Plotting**: Freqtrade's historical endpoints (like `/daily`) return data oldest-first. Time-series charts (like `EquityChart` and `DailyBars`) must always plot chronologically from left (oldest) to right (newest/today).

## Testing & Refactoring
- **Refactoring JSX**: Do NOT use greedy multiline regex scripts (e.g., Python `re.sub` with `re.DOTALL`) to batch-replace code across JSX files. Component scopes change rapidly, and greedy regex often swallows component boundaries or injects undefined variables. Rely on precise block-level replacements using the standard `replace_file_content` tool.
- **Responsive Testing**: The dashboard has heavily diverging mobile (`< 768px`) and desktop UI branches. When writing Puppeteer scripts to verify rendering or debug crashes, ALWAYS test both desktop and mobile viewports (e.g., `page.setViewport({ width: 375, height: 667, isMobile: true })`) to ensure no platform-specific crashes are missed.
