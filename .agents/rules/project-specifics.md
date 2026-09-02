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
