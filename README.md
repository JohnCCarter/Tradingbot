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

## Starta boten på server/arbetsyta (t.ex. Azure VM)

1. Logga in på din server/VM via SSH:

   ```bash
   ssh användare@server-ip
   ```

2. Navigera till din Tradingbot-mapp:

   ```bash
   cd Tradingbot
   ```

3. Aktivera miljön:

   ```bash
   conda activate tradingbot_env
   ```

4. **Installera screen om det inte redan finns:**

   ```bash
   sudo apt-get update
   sudo apt-get install screen
   ```

5. (Rekommenderat) Starta en screen-session så boten fortsätter även om du tappar anslutningen:

   ```bash
   screen -S tradingbot
   ```

6. Starta boten:

   ```bash
   python tradingbot.py
   ```

7. Koppla från screen (boten fortsätter köra):
   - Tryck `Ctrl+A` följt av `D`
8. Återanslut till din screen-session:

   ```bash
   screen -r tradingbot
   ```

## Arbetsflöde för att köra på både hemdator och jobbdator

1. Lägg till och spara din .env-fil på ett säkert ställe (t.ex. på din hemdator eller i en lösenordshanterare). Lägg aldrig .env i repo:t.
2. På jobbdatorn:
   - Klona eller uppdatera projektet från GitHub:

     ```bash
     git clone <repo-url>
     # eller om du redan har klonat:
     git pull
     ```

   - Arbeta med koden, gör ändringar och pusha till GitHub:

     ```bash
     git add .
     git commit -m "Dina ändringar"
     git push
     ```

   - Kör endast kod som inte kräver API-nycklar eller känsliga filer.
3. När du är hemma:
   - Klona eller uppdatera projektet från GitHub:

     ```bash
     git pull
     ```

   - Lägg till din .env-fil i projektmappen manuellt på din lokala maskin. **Se till att .env-filen aldrig läggs till i versionshantering (t.ex. Git).**
   - Skapa och aktivera miljön:

     ```bash
     conda env update -f environment.yml
     conda activate tradingbot_env
     ```

   - Starta boten:

     ```bash
     python tradingbot.py
     ```

**Tips:**

- Spara alltid din .env-fil på ett säkert ställe och kopiera in den när du ska köra boten hemma eller på server.
- Koden och miljön synkas via GitHub, men .env-filen måste du alltid lägga till manuellt.
- På jobbdatorn kan du utveckla och testa kod utan att köra boten live.

## Tips för drift

- Kontrollera att din .env och config.json är korrekt ifyllda.
- Kontrollera loggar och order_status_log.txt för status och felsökning.
- Boten skickar e-postnotis när order skickas och när den fylls.
- För att se att boten är igång: `screen -ls` och `screen -r tradingbot`.
- Stoppa boten med `Ctrl+C` inuti screen-sessionen.

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

## Projektstruktur

- Uppdatera projektstruktur för att matcha aktuella filer och mappar

```plaintext
Tradingbot/
├── api.py                    # API-klient och wrapper (om används)
├── config.json               # Konfigurationsparametrar för boten
├── dashboard.html            # Enkel HTML-dashboard
├── dockerfile                # Docker-konfiguration
├── environment.yml           # Conda-miljödefinition
├── tradingbot.py             # Huvudscript för tradingbot
├── test_tradingbot.py        # Pytest-tester
├── script.sh                 # Installationsscript för ny server/VM
├── script_start.sh           # Startscript för daglig drift
├── README.md                 # Denna fil
├── ROADMAP.md                # Roadmap och TODO-lista
├── order_status_log.txt      # Loggfil för orderstatus
└── __pycache__/              # Kompilerade Python-filer
```

## Felsökning & Vanliga problem

> **Denna sektion är min personliga felsökningslogg. Här skriver jag kortfattat problem och lösningar för framtida mig själv. Det är ok med punktform, informellt språk och snabba anteckningar!**

### Problem: Tom marknadsdata vid test mot Bitfinex

**Symptom:**

- Testet `test_execute_trading_strategy_with_live_data` misslyckas med felmeddelandet "Kunde inte hämta marknadsdata".
- Loggar visar att DataFrame är tom efter hämtning av OHLCV-data.

**Orsak:**

- TIMEFRAME i `config.json` var satt till ett värde som Bitfinex inte stöder (t.ex. "35m"). Bitfinex och de flesta börser stöder endast vissa standardintervall, t.ex. "1m", "5m", "15m", "1h" osv.

**Lösning:**

- Ändra TIMEFRAME i `config.json` till ett giltigt värde, t.ex. "1m".
- Efter ändringen returneras marknadsdata korrekt och testet passerar.

**Exempel på korrekt konfiguration:**

```json
{
  ...
  "TIMEFRAME": "1m",
  ...
}
```

---

> **Notera:**
> Alla framtida problem och deras lösningar ska dokumenteras i denna sektion i README.md så att felsökning och kunskapsöverföring blir enkel för framtida mig.
