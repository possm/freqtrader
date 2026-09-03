---
name: freqtrader-dash-rules
description: Project specific rules and context for the freqtrader-dash dashboard.
trigger: always_on
---

# freqtrader-dash Project Specifics

- **Architecture:** This is an in-browser React 18 application with no build step. JSX is compiled live in the browser by Babel standalone.
- **Cache Busting:** Because Babel standalone runs in the browser, caching is aggressive. Whenever you modify a `.jsx` file, you MUST ALSO update its corresponding `?v=[timestamp]` query parameter in `index.html` (e.g., `src="api.jsx?v=12345"`). If you forget to bump this version number, the user's browser will stubbornly load the old cached code.
- **Dependencies:** No Node toolchain, no npm, and no bundlers. Files are statically served by an Nginx container.
- **Deployment (CRITICAL):** Code edits made in this local workspace are NOT automatically visible in the browser (which runs off the VPS). After making functional code changes, you MUST explicitly deploy them to the VPS (`vps-matthijs-trader`) using `rsync` and restart the dashboard container (`docker compose up -d --build`) BEFORE asking the user to verify the changes.
- **API Backend:** Reads from Freqtrade's REST API (`/api/v1/...`) directly from the browser. credentials are saved in localStorage.

## Freqtrade API & Data Quirks
- **Multi-Bot Feature Design**: The user runs multiple distinct strategy types on the same dashboard (e.g., standard single-entry trend bots on port 8080 and multi-entry DCA/Grid bots on port 8081). When building features, you MUST build them defensively so they degrade gracefully and render correctly for *both* types of bots. For example, never use naive checks like `orders.length > 1` to identify a DCA grid, as Freqtrade also logs exchange stop-losses as "orders" which breaks standard bots. Always rely on specific data flags like `nr_of_successful_entries`.
- **Profit Calculation**: In the `/api/v1/profit` endpoint, `profit_all_coin` is equal to Closed Profit + Open Unrealized Profit. To get strictly closed profit, you MUST use `profit_closed_coin`.
- **Dashboard Definitions**: In `api.jsx`, the variable `summary.totalPnl` must always represent strictly *Closed Profit*. Net Profit is calculated on-the-fly in the UI by adding `unrealizedPnl`.
- **Daily P&L Chart**: The Daily P&L bars (`DailyBars`) must strictly show closed profit only. Do not overlay or include unrealized profits in this specific chart.
- **Chronological Plotting**: Freqtrade's historical endpoints (like `/daily`) return data oldest-first. Time-series charts (like `EquityChart` and `DailyBars`) must always plot chronologically from left (oldest) to right (newest/today).

## Testing & Refactoring
- **Refactoring JSX**: Do NOT use greedy multiline regex scripts (e.g., Python `re.sub` with `re.DOTALL`) to batch-replace code across JSX files. Component scopes change rapidly, and greedy regex often swallows component boundaries or injects undefined variables. Rely on precise block-level replacements using the standard `replace_file_content` tool.
- **Responsive Testing**: The dashboard has heavily diverging mobile (`< 768px`) and desktop UI branches. When writing Puppeteer scripts to verify rendering or debug crashes, ALWAYS test both desktop and mobile viewports (e.g., `page.setViewport({ width: 375, height: 667, isMobile: true })`) to ensure no platform-specific crashes are missed.
- **Visual Parity Verification**: When asked to unify layouts or investigate UI styling issues ("look different"), do NOT rely purely on JSX code reading. You MUST write a Puppeteer script (`screenshot.js`) that intercepts API calls (mocking Freqtrade's `/api/v1/status` and `/api/v1/trades`), renders the relevant views, and saves screenshots (e.g., `screenshot_positions.png`). View these screenshots using the `view_file` tool to visually compare layout hierarchy, column alignments, font weights, and edge cases.

## VPS & Hyperopt Safety (Freqtrade)
- **Hyperopt Parameter Leaks**: NEVER run `freqtrade hyperopt` directly in the live bot's directory (specifically `user_data/strategies/`). Freqtrade automatically saves intermediate hyperopt results to a `<strategy_name>.json` file in the strategy folder. If the live bot is restarted, it will automatically load these experimental `.json` parameters instead of the strategy's hardcoded ROI/stoploss, causing it to unexpectedly dump open positions. Always run hyperopt in a segregated test directory, or absolutely guarantee the deletion of any generated `.json` parameter files before restarting the live container.
