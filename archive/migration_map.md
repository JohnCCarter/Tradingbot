| Ursprunglig fil                | Ny modul/fil                | Kommentar |
|-------------------------------|-----------------------------|----------|
| tradingbot.py                 | main.py, api_server.py      | Funktionalitet uppdelad |
| api.py                        | api_server.py               | Migrerad till Flask-baserad modul |
| core.py                       | strategy.py, exchange.py    | Klasser/funktioner fördelade |
| data.py                       | db.py, performance.py       | Databas och analys separerade |
| test_tradingbot.py            | tests/                      | Enhetstester flyttade |
| strategy_performance.js       | static/strategy_performance.js | Frontendmodul flyttad |
| dashboard.html                | static/dashboard.html       | Frontend flyttad |
| script.sh, script_start.sh    | scripts/setup.sh, scripts/start.sh | Automationsskript flyttade |
