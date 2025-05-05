# Tradingbot Roadmap

## ✅ Klart/Implementerat

- Webbgränssnitt (dashboard.html) med orderläggning, saldo, orderhistorik och prisgraf
- Orderformulär med valbar symbol, ordertyp, mängd och pris (anpassat för Bitfinex paper trading-symboler)
- Realtidsuppdatering av saldo, ordrar och pris
- API (api.py) med endpoints för start/stop, saldo, orderläggning, orderhistorik, realtidsdata och konfiguration
- Backend tar emot symbol från frontend och skickar vidare till tradingbot.py
- Tradinglogik (tradingbot.py) med market/limit orders, stop loss, take profit
- Hantering av Bitfinex paper trading-symboler
- Realtidsdata via WebSocket
- E-postnotifieringar vid orderhändelser
- Backtest-funktionalitet
- Felhantering för ogiltiga symboler och orderproblem

## 🚧 Pågår / Nästa steg

- Bättre felhantering och loggning i både backend och frontend
- Visa tydligare felmeddelanden i webbgränssnittet
- Stöd för fler exchanges (t.ex. Binance, Coinbase)
- Fler indikatorer och strategier (t.ex. MACD, Bollinger Bands)
- Lösenordsskydd/adgang till dashboarden
- Automatiska e-postrapporter om tradingresultat
- Mobilanpassning av dashboarden
- dockerisering och möjlighet till molndeployment

---
Uppdatera denna fil löpande när nya funktioner implementeras eller påbörjas.
