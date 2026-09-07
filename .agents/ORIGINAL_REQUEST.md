# Original User Request

## 2026-09-04T15:21:02Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: 3 agents (Quant, Data Scientist, Risk Manager)

Zoek op het internet naar academische theorieën (zoals volatility breakout of mean-reversion) om een nieuwe Freqtrade altcoin strategie te ontwerpen. Ontwikkel de code, draai een hyperopt op de VPS, en zorg ervoor dat de strategie de Kraken-fees ruim verslaat (minimaal >10% winst) voordat de Risk Manager deze verifieert en goedkeurt. Zodra goedgekeurd, wordt de strategie in Dry Run modus gedeployed op de VPS.

Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Integrity mode: demo

## Requirements

### R1. Strategie Ontwikkeling
Voer een literatuuronderzoek uit op het internet naar een recente, theorie-onderbouwde aanpak (bijv. volatility breakout of mean-reversion) voor altcoins. Vertaal deze theorie naar een bruikbare Python-strategie voor Freqtrade.

### R2. Optimalisatie (Hyperopt)
De Data Scientist bepaalt zelfstandig de meest logische timeframe en dataset-lengte op basis van de gekozen theorie. Voer vervolgens Hyperopt-sessies uit op de VPS om de parameters te optimaliseren, waarbij de Kraken-tradingfees expliciet meegerekend worden. De resulterende parameters moeten zorgen voor een verwachte winst van structureel >10%.

### R3. Veilige Deploy (Dry Run)
De Risk Manager controleert de code op fatale bugs. Vervolgens wordt er een nieuwe container of configuratie aangemaakt in de bestaande setup (via de VPS) die expliciet in **Dry Run** (simulatie) modus staat. De bot wordt gestart en gecontroleerd.

### R4. VPS Infrastructuur
Je gebruikt de lokale terminal om via SSH commando's te sturen naar `vps-matthijs-trader`. Je mag bestanden (strategieën, configs) lokaal schrijven en via `rsync` of `scp` synchroniseren naar de VPS, exact zoals omschreven in de `GEMINI.md` regels.

## Acceptance Criteria

### Verificatie & Kwaliteit
- [ ] Een Freqtrade backtest- of hyperopt-log toont objectief aan dat de strategie na fees een `Total profit %` van >10% behaalt op de gekozen periode.
- [ ] De nieuwe strategie `.py` is succesvol gesynchroniseerd naar `~/freqtrade-wolf/user_data/strategies/` op de VPS.
- [ ] De Docker container voor de dry-run bot is gestart zonder direct af te sluiten (geen opstart-crashes).
- [ ] De VPS logs tonen op z'n minst 3 succesvolle `Bot heartbeat` meldingen met `state='RUNNING'` in de logs van de nieuwe dry-run bot, wat bewijst dat de indicatoren correct laden en er geen syntax fouten zijn.

## 2026-09-04T19:10:54Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full team (Quant, Data Scientist, Risk Manager)

Voer onderzoek uit naar een compleet nieuwe crypto trading theorie en ontwikkel een Freqtrade strategie. Het expliciete en agressieve doel is om een rendement te behalen van gemiddeld minimaal **10% netto winst per máánd** (ca. >120% per jaar).

Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Integrity mode: development

## Requirements

### R1. Agressieve Strategie Ontwikkeling
Zoek naar en implementeer een theorie/strategie die potentie heeft voor extreme rendementen. De markt blijft strikt beperkt tot Kraken Spot (Spot trading, dus geen hefbomen of shorting toegestaan). 

### R2. Flexibel Risicomanagement
Om 10% per maand te halen op uitsluitend de spot-markt, moeten er significante risico's genomen worden. De Risk Manager krijgt de volledige vrijheid om de maximale acceptabele drawdown grens zelf te bepalen.

### R3. Hyperopt & Optimalisatie
Voer een hyperopt uit op de VPS (`vps-matthijs-trader`) over historische data (bijv. vanaf 2024 of een andere relevante periode). Kraken trading fees moeten nadrukkelijk in de berekening worden meegenomen.

### R4. VPS Infrastructuur
Je gebruikt de lokale terminal om via SSH commando's te sturen naar `vps-matthijs-trader`. Bestanden mogen lokaal geschreven worden en via `rsync` of `scp` gesynchroniseerd worden naar de VPS.

## Acceptance Criteria

### Verificatie & Kwaliteit
- [ ] Een Freqtrade backtest log (of hyperopt log) op de VPS bewijst objectief dat de strategie een gemiddelde netto winst van >10% per maand behaalt over de geteste periode.
- [ ] De backtest/hyperopt toont aan dat Kraken fees expliciet zijn afgetrokken.
- [ ] De code levert geen opstartfouten of syntax-errors op in Freqtrade.
- [ ] Er is een markdown eindrapport (bijv. `reports/10PERCENT_MONTH_REPORT.md`) gegenereerd waarin de Risk Manager de theorie toelicht en verantwoordt waarom de gekozen drawdown en risico's acceptabel zijn voor dit doel.

