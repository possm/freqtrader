# Freqtrade VPS Deployment Workflow

Wanneer je wijzigingen doorvoert of nieuwe strategieën live zet in deze repository, volg dan ALTIJD exact deze workflow:

1. **Commit**: Pas de code aan en maak een git commit (zorg dat je op een nieuwe branch zit conform de globale regels).
2. **Vraag Permissie**: Push nooit zelfstandig. Vraag eerst toestemming aan de gebruiker.
3. **Sync met VPS**: 
   Zodra je permissie hebt, push je de branch en gebruik je rsync om de bestanden met de VPS te synchroniseren. Zorg ervoor dat data, logs en databases ALTIJD uitgesloten worden:
   `rsync -avz --exclude '.git' --exclude 'user_data/data' --exclude 'user_data/logs' --exclude 'user_data/hyperopt_results' --exclude 'user_data/backtest_results' --exclude '*.sqlite*' ./ vps-matthijs-trader:~/freqtrade-wolf/`
4. **Valideer**: 
   Herstart na de sync altijd de container op de VPS en check de logs om te valideren dat de strategie succesvol en zonder fouten laadt:
   `ssh vps-matthijs-trader "cd freqtrade-wolf && docker compose up -d freqtrade-hopt-live && sleep 5 && docker compose logs --tail=50 freqtrade-hopt-live"`
