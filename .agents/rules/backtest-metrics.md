# Backtest Metrics in Dashboard

Wanneer er een nieuwe of geoptimaliseerde strategie wordt gebacktest met significante prestaties, moet dit backtest-resultaat (Winstpercentage, Winrate) hardcoded worden weergegeven in het dashboard, specifiek onder het robot icoontje in de zijbalk navigatie (`Sidebar` in `dashboard/app.jsx`).

Zo behoudt de gebruiker altijd context over hoe de geselecteerde live/dry-run strategie historisch presteert.

## Implementatie
De metrics worden geplot in de `Sidebar` component in `app.jsx` via de `getBacktestResult()` mapping:
```javascript
  const getBacktestResult = (name) => {
    if (!name) return null;
    if (name.includes("WolfSqueeze")) return "Backtest: +41.27% (78.3% WR)";
    if (name.includes("WolfBreakout_Daily")) return "Backtest: +19.43% (79.5% WR)";
    if (name.includes("WolfBreakout_PVB")) return "Backtest: -2.30% (44.0% WR)";
    return null;
  };
```
Zorg dat je bij toekomstige backtests deze mapping in `dashboard/app.jsx` update met de meest recente cijfers.
