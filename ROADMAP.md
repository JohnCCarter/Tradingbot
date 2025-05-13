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
- Strategi-prestanda-sektion i dashboarden för analys av handelsresultat

## 🚧 Pågår / Nästa steg

- Förbättrad strategi-prestanda-sektion:
  - Mer detaljerad statistik och visualiseringar
  - Förbättrad beräkning av vinst/förlust
  - Export av statistik till CSV/Excel
- Förbättrad loggning och debug-funktionalitet:
  - Detaljerad loggning av handelsbeslut
  - Visualisering av specifika felkällor
  - Enkel debug-panel för felsökning
- Bättre felhantering och loggning i både backend och frontend
- Visa tydligare felmeddelanden i webbgränssnittet
- Stöd för fler exchanges (t.ex. Bitfinex ,Binance, Coinbase)
- Fler indikatorer och strategier (t.ex. MACD, Bollinger Bands)
- Lösenordsskydd/adgang till dashboarden
- Automatiska e-postrapporter om tradingresultat
- Mobilanpassning av dashboarden
- dockerisering och möjlighet till molndeployment

## 🔮 Framtida planer

- Utveckla en modern frontend med React:
  - Separera frontend från backend för bättre arkitektur
  - Förbättrad användarupplevelse med moderna UI-komponenter
  - Responsiv design för alla enheter
  - Mer interaktiva grafer och visualiseringar
  - State management med Redux eller Context API
  - Realtidsuppdateringar med WebSockets
  - Möjlighet till teman och anpassning av användargränssnittet
- Utökad API-dokumentation för enklare integration
- Potentiell deployment till molntjänster (Azure, AWS, etc.)
- Dashboard-applikation för mobiltelefoner

---
Uppdatera denna fil löpande när nya funktioner implementeras eller påbörjas.
