# Freqtrade Monorepo Operational & Deployment Workflow

## 1. Global Git Branching Rule
Wanneer je aan code werkt, maak dan ALTIJD eerst een nieuwe git branch aan voordat je wijzigingen doorvoert of commits maakt. Commit nooit direct naar de main of master branch.
Daarnaast mag je NOOIT zelfstandig code pushen naar een remote (bijv. GitHub met `git push`), tenzij de gebruiker hier expliciet om vraagt. Dit geldt voor ALLE branches. Wacht altijd op expliciete toestemming van de gebruiker (zoals "push maar").

## 2. Monorepo VPS Deployment Workflow
Wanneer je wijzigingen doorvoert in de bots, configuraties of dashboard:
1. **Commit**: Zorg voor een schone commit op een feature branch conform de globale regels.
2. **Permissie**: Vraag expliciet toestemming aan de gebruiker voor de push/sync. Push nooit zelfstandig.
3. **Sync met VPS**:
   Zodra je permissie hebt, push je de branch en gebruik je rsync om de bestanden met `vps-matthijs-trader` te synchroniseren. Zorg dat data, logs, hyperopt-resultaten, backtest-resultaten en databases ALTIJD uitgesloten worden:
   ```bash
   rsync -avz --exclude '.git' --exclude 'user_data/data' --exclude 'user_data/logs' --exclude 'user_data/hyperopt_results' --exclude 'user_data/backtest_results' --exclude '*.sqlite*' ./ vps-matthijs-trader:~/freqtrader/
   ```
4. **Valideer Containers**:
   Herstart na de sync altijd de containers op de VPS en check de logs om te valideren dat de services succesvol en zonder fouten laden:
   ```bash
   ssh vps-matthijs-trader "cd freqtrader && docker compose up -d freqtrade-hopt-live freqtrade-academic-dryrun freqtrader-dash && sleep 5 && docker compose ps"
   ```
   Valideer specifieke logs op runtime fouten:
   - Live Bot: `ssh vps-matthijs-trader "cd freqtrader && docker compose logs --tail=50 freqtrade-hopt-live"`
   - Academic Dry-Run Bot: `ssh vps-matthijs-trader "cd freqtrader && docker compose logs --tail=50 freqtrade-academic-dryrun"`
   - Dashboard: `ssh vps-matthijs-trader "cd freqtrader && docker compose logs --tail=50 freqtrader-dash"`

## 3. Dashboard Frontend Specifics (`dashboard/`)
- **Vite Buildstep**: Het dashboard gebruikt nu een Vite/React pipeline met ES-modules. In de `dashboard/` map bevindt zich een `package.json`. Bij wijzigingen lokaal installeer en test je via `npm install` en `npm run dev`.
- **Cache-Busting (Vite)**: Niet meer handmatig nodig. Vite genereert gehashte bundels tijdens `npm run build` die door Nginx agressief worden gecachet (permanente cache), terwijl `index.html` zelf een `no-cache` header krijgt.
- **Multi-Bot Defensief**: Gebruik `nr_of_successful_entries` om DCA grids te herkennen, nooit `orders.length > 1`.
- **P&L Semantiek**: `summary.totalPnl` = Closed Profit (`profit_closed_coin`). Unrealized profit wordt runtime opgeteld.
- **Testing**: Test UI-wijzigingen altijd op zowel desktop als mobiele viewports (`< 768px`).
- **Docker Nginx Rebuild (Deployment)**: Wanneer je wijzigingen aanbrengt in `dashboard/` en deze rsync't naar de VPS, dan is een simpele `docker compose restart` of `up -d` niet genoeg. De Nginx container gebruikt een multi-stage build om Vite uit te voeren. Je MOET de dashboard container na een rsync dus expliciet herbouwen en herstarten:
  `ssh vps-matthijs-trader "cd freqtrader && docker compose build freqtrader-dash && docker compose up -d freqtrader-dash"`

## 4. Hyperopt Safety & Parameter Overrides (CRITICAL)
- **Shared Volume Risk**: Alle bots (live én dry-runs) delen dezelfde `user_data` volume mount. Voer `freqtrade hyperopt` NOOIT direct uit in de live strategieën map (`user_data/strategies/`). Freqtrade genereert automatisch `<strategy_name>.json` bestanden die bij een bot herstart de code overschrijven. Een lek van een `.json` bestand infecteert potentieel **alle** draaiende bots.
- **Cleanup**: Verifieer vóór container herstart altijd met `ls user_data/strategies/*.json` dat er geen onbedoelde `.json` bestanden aanwezig zijn. Als je ze wist, herstart dan óók de dry-run bots om hun werkgeheugen te wissen.

## 5. Bybit Fee Assumptions & Pairs (Updated Oct 2026)
Wanneer je ROI, winst, of drawdowns berekent/simuleert, gebruik dan ALTIJD de actuele Bybit (SATOS) Spot tarieven (Unified Flat Fee per 5 okt 2026):
- **Maker fee:** 0.25%
- **Taker fee:** 0.25%
Let op: Voor Europese accounts (SATOS) is USDT Spot handel geblokkeerd. Gebruik altijd de **USDC** of **EUR** paren.

## 6. Environment Variables & API Keys Security
- Plaats API-keys, geheimen of tokens NOOIT direct in configuratiebestanden (zoals `config.json` of `config_academic_dryrun.json`).
- Gebruik altijd het `.env` bestand in de hoofdmap in combinatie met de Freqtrade environment variable syntax (bijv. `FREQTRADE__EXCHANGE__KEY` en `FREQTRADE__EXCHANGE__SECRET`).
- Het `.env` bestand wordt genegeerd door Git via `.gitignore`, maar wordt wél veilig door het `rsync` commando naar de VPS gesynchroniseerd.

## 7. Local Testing Safety (CRITICAL)
- **NO LIVE BOTS LOCALLY**: Start NOOIT de `freqtrade-hopt-live` container lokaal via Docker Compose als je backend functionaliteit (zoals het dashboard of API-koppelingen) wilt testen. Omdat de lokale map een `.env` bestand bevat met actieve API-keys, zal de bot direct in `live` mode opstarten en **ECHTE TRADES** uitvoeren met echt geld op Bybit.
- **Enkel Dry-Run**: Gebruik voor lokaal testen ALTIJD de `freqtrade-academic-dryrun` container, of zorg dat je expliciet `dry_run: true` forceert, zodat er nooit onbedoeld geld wordt uitgegeven.

## 8. VPS Debugging & Database Access
- Het `sqlite3` CLI commando is **niet** geïnstalleerd op de VPS (`vps-matthijs-trader`).
- Om snel actieve trades uit de Freqtrade databases te lezen (bijv. `tradesv3_hopt_live.sqlite`), gebruik je een Python one-liner in plaats van de sqlite3 tool. Bijvoorbeeld:
  `ssh vps-matthijs-trader "python3 -c \"import sqlite3; conn = sqlite3.connect('freqtrader/user_data/tradesv3_hopt_live.sqlite'); print(conn.execute('SELECT pair, open_rate FROM trades WHERE is_open=1').fetchall())\""`
