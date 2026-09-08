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
- **In-browser Babel**: Geen npm build step. JSX wordt runtime in de browser gecompileerd via Babel standalone.
- **Cache-Busting**: Bij wijziging van een `.jsx` bestand, update ALTIJD het query-parameter versienummer in `index.html` (bijv. `src="api.jsx?v=[timestamp]"`).
- **Multi-Bot Defensief**: Gebruik `nr_of_successful_entries` om DCA grids te herkennen, nooit `orders.length > 1`.
- **P&L Semantiek**: `summary.totalPnl` = Closed Profit (`profit_closed_coin`). Unrealized profit wordt runtime opgeteld.
- **Testing**: Test UI-wijzigingen altijd op zowel desktop als mobiele viewports (`< 768px`).
- **Docker Nginx Rebuild (Deployment)**: Wanneer je wijzigingen aanbrengt in `dashboard/` en deze rsync't naar de VPS, dan is een simpele `docker compose restart` of `up -d` niet genoeg. De Nginx container 'bakt' de bestanden tijdens het bouwen in de image. Je MOET de dashboard container na een rsync dus expliciet herbouwen en herstarten:
  `ssh vps-matthijs-trader "cd freqtrader && docker compose build freqtrader-dash && docker compose up -d freqtrader-dash"`

## 4. Hyperopt Safety & Parameter Overrides
- Voer `freqtrade hyperopt` NOOIT direct uit in de live strategieën map (`user_data/strategies/`). Freqtrade genereert automatisch `<strategy_name>.json` bestanden die bij een bot herstart de code overschrijven.
- Verifieer vóór container herstart dat er geen onbedoelde `.json` bestanden in `user_data/strategies/` staan die live parameter overrides veroorzaken.

## 5. Kraken Fee Assumptions
Wanneer je ROI, winst, of drawdowns berekent/simuleert, gebruik dan ALTIJD de Kraken Pro tarieven (Taker fee max 0.26%, Maker fee max 0.16%). Freqtrade handelt direct via de API-orderboeken, waardoor de dure consumenten "Instant Buy" fee (1.5%) irrelevant is.
