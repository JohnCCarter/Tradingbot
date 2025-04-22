# Tradingbot

## Användarguide

### Installation

1. Klona detta repo:
   ```bash
   git clone <repo-url>
   cd Tradingbot
   ```
2. Installera beroenden (kräver Conda):
   ```bash
   conda env update -f environment.yml
   conda activate tradingbot_env
   ```

### Konfiguration

- Fyll i din API_KEY och API_SECRET i en .env-fil:
  ```env
  API_KEY=din_bitfinex_api_key
  API_SECRET=din_bitfinex_api_secret
  ```
- Justera config.json för att ändra symbol, strategi-parametrar, riskregler m.m.

### Användning

- Starta tradingboten:
  ```bash
  python tradingbot.py
  ```
- Kör tester:
  ```bash
  pytest
  ```
- Kör backtest direkt:
  ```bash
  python test_tradingbot.py
  ```

### Tips
- Använd Bitfinex paper trading för att testa utan risk.
- Kontrollera loggar och API-nycklar noggrant.
- Läs och följ roadmapen nedan för vidareutveckling.

## Roadmap och TODO

- Utöka testtäckningen för fler marknader och strategier
- Implementera loggning till fil och/eller molntjänst
- Lägg till notifieringar (t.ex. e-post eller Slack) vid utförda trades
- Bygg ett enkelt webbgränssnitt för övervakning och status
- Gör strategin mer konfigurerbar via config.json
- Lägg till fler riskhanteringsregler (t.ex. trailing stop, max position size)
- Dokumentera API-nyckelhantering och säkerhet
- Lägg till CI/CD för automatiska tester och kodkvalitet
- Utvärdera och optimera prestanda för realtidsdata
- Lägg till fler backtest-möjligheter och statistik