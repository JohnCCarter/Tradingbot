### Omstrukturerad Refaktoreringsplan för Tradingbot


#### 1. Konfigurationshantering (`config.py`)

* **Miljö- och hemlighetshantering**: Ladda `.env` med `python-dotenv`, validera med Pydantic `BotConfig` (fälten `API_KEY`, `API_SECRET`, `SUPABASE_URL`, `SUPABASE_KEY`).
* **Versionsstyrd konfiguration**: `ConfigManager` för läsning/skrivning av `config.json`, med schema-validering, versionshantering och fallback.
* **Felhantering**: Definiera entydiga undantag vid saknade eller ogiltiga värden.

#### 2. Loggning och Telemetri (`logger.py`)

* **ANSI-färgade strukturerade loggar**: `TerminalColors` + `StructuredLogger` med kategorier (`STRATEGY`, `MARKET`, `ORDER`, `WEBSOCKET`).
* **Loggmål**: Konfigurera handlers för fil, konsol och extern logghantering (ELK/Graylog).
* **JSON-format**: Validerbar struktur för nätverksexport.

#### 3. Verktygsmodul (`utils.py`)

* **Retry-decorator**: Generisk med exponentiell backoff för nätverks- och API-anrop.
* **Nonce och tidsstämpling**: `get_next_nonce()`, `timestamp_nonce()` för monotonicitet enligt exhange-krav.
* **Symbolnormalisering**: `ensure_paper_trading_symbol()` för Bitfinex-prefix.
* **Tidszonskonvertering**: `convert_to_local_time(ts, tz)` med `pytz`.
* **Export**: CSV/Excel-export för backtest- och prestandadata.

#### 4. Indikatorer och Mönsterigenkänning (`indicators.py`)

* **Tekniska indikatorer**: `calculate_indicators(df, params)` med TA-Lib och `lru_cache`.
* **Fair Value Gap**: `detect_fvg(df)` med datarensning och outlier-hantering.

#### 5. Exchange-adapter (`exchange.py`)

* **`ExchangeClient`**: CCXT-initiering, autentisering, signering, rate-limit.
* **Sync/Async**: `fetch_balance()`, `fetch_market_data()`, `fetch_historical_data()` + `async_fetch_market_data()`.
* **Orderbok & Ticker**: `get_orderbook()`, `get_current_price()`, robust felhantering.

#### 6. Orderhantering (`orders.py`)

* **Ordertyper**: `create_limit_order()`, `create_market_order()` med parameterkontroll.
* **Orderparsing**: `parse_order_data(raw)` → uniform intern representation.
* **Orderkontroll**: `cancel_order()`, `get_open_orders()`, resilient retry.

#### 7. Strategiutförande och Backtest (`strategy.py`)

* **`TradingStrategy`-klass**: Konfigurationsinjektion, states, lifecycle.
* **Exekveringsalgoritm**: `execute_trading_strategy()` med daglig stop-loss, maxtrades.
* **Backtest**: `run_backtest()` med parametrisk kalibrering, CSV/Excel-export, prestandarapport.

#### 8. Realtidsbearbetning (`realtime.py`)

* **WebSocket-klient**: `listen_order_updates()`, autentisering, keep-alive.
* **Candlestickflöde**: `process_candles(msg)`, integrera `calculate_indicators`.
* **Async orchestration**: `start_realtime_loop()` med `asyncio.gather`.

#### 9. Prestandaanalys (`performance.py`)

* **Loggparsing**: `parse_order_log(path)` extraherar `EXECUTED/CANCELED`-rader.
* **Statistikberäkning**: `compute_summary_statistics(data)` (P\&L, win-rate, volymsammanställning).
* **Daglig prestanda**: `format_daily_performance(stats)` → strukturerad output.
* **Export**: CSV/Excel av analysresultat.

#### 10. Hälsa & Metrik (`health.py`, `metrics.py`)

* **Health-check**: Flask-blueprint `GET /health` → `{ status: "ok" }`.
* **Prometheus**: `metrics.py` med `Counter`, `Gauge`, `Histogram` och `start_metrics_server(port)`.
* **Metrics-endpoint**: `GET /metrics` exposar Prometheus-format.

#### 11. Datapersistens & DB (`db.py`)

* **SupabaseClient**: CRUD för loggar, orderhistorik, backtest.
* **Fallback**: Lokal fil `order_status_log.txt`, migrations- och schemahantering.

#### 12. Notifieringar (`notifications.py`)

* **Email**: `EmailNotifier` (TLS/SSL via smtplib, bakåtkompatibilitet).
* **Slack**: `SlackNotifier`.

#### 13. API-server (`api_server.py`)

* **Flask/Blueprints**: Moduler `orders`, `performance`, `config`, `health`.
* **CORS & Felhantering**: Global `@after_request`, `@errorhandler`.
* **OpenAPI**: Dokumentation via `flasgger` eller `apispec`.

#### 14. Huvudskript (`main.py`)

* **Init**: Ladda config, initiera `ExchangeClient`, `DB`, `Logger`.
* **Parallel runtime**: `asyncio` för realtid, strategi, API-server, metrics.
* **Graceful shutdown**: Hantera `SIGINT`/`SIGTERM` korrekt.

#### 15. Automationsskript & Drift (`scripts/`)

* **`setup.sh`**: Serversetup (Conda, Git, beroenden).
* **`start.sh`**: Screen/Tmux, loggrotator, container-entrypoint.

#### 16. Containerisering & CI/CD

* **Docker**: `Dockerfile`, `docker-compose.yml`.
* **GitHub Actions**: `.github/workflows/ci.yml` med lint, tester, Docker-build.
* **Pre-commit**: `.pre-commit-config.yaml` (Black, isort, flake8, autoflake).
* **Makefile**: Mål `format`, `lint`, `test`, `docker-build`.

#### 17. Frontend (`static/`)

* **Struktur**: `static/` med `css/`, `js/`, `img/`.
* **HTML/CSS**: `dashboard.html`, `styles.css` (Tailwind alternativt).
* **JS-moduler**: `main.js`, `strategy_performance.js`, React/TS-arkitektur för framtiden.

#### 18. Dokumentation och Bevarande

* **Docs**: `README.md`, `ROADMAP.md`, `docs/` via MkDocs eller Sphinx.
* **Guides**: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`.
* **API-dokument**: Autogenerated via OpenAPI.

#### 19. Testinfrastruktur (`tests/`)

* **Enhetstester**: `pytest`-moduler per komponent med `pytest-mock`.
* **Integrationstester**: `vcrpy` för inspelning/återspelning av CCXT-anrop.
* **E2E-tester**: Simulera WebSocket och order-flöde.




# Upddatering 
20. Rensning och Dublettkontroll (cleanup)

Filjämförelse: Kör git diff --name-status mot förra commit eller trädstruktur för att identifiera kvarblivna/duplicerade filer.

Obsoleta filer: Lista alla ursprungliga filer som nu ersatts av nya moduler (t.ex. tradingbot.py, api.py, strategy_performance.js) och radera dessa eller flytta dem till archive/.

Dublettkontroll: Sök igenom projektet efter moduler med överlappande funktioner (samma klasser/funktioner i flera filer) och slå samman eller ta bort duplicerad kod.

CI-check: Lägg till lint-regel eller pytest-test som säkerställer att inga referenser bryts av borttagna filer.

Git-stage: Automatisera git rm för onödiga filer och skapa en commit chore: cleanup obsolete files


# Ny uppdatering
21. Verifiering av kodplacering (placement_review)

Kodplacering: Granska att varje funktion, klass och modul har migrerats till respektive fil i enlighet med den specificerade modulstrukturen.

Mapping-dokumentation: Generera automatiskt en jämförelsetabell (migration_map.csv eller .md) som länkar ursprungliga filnamn till nya moduler för spårbarhet.

Enhetstester: Utvidga testsviten med verifieringsmekanismer som säkerställer att alla moduler och deras beroenden överensstämmer med den omstrukturerade arkitekturen, och att inga referenser till de ursprungliga filerna kvarstår.

# En till uppdatering
22. Paketinitialisering: Säkerställ att varje modulmapp innehåller en __init__.py (kan vara tom), för korrekt paketupptäckt.

Importjustering: Kör isort och flake8 för att korrigera importvägar; överväg verktyg som rope eller sed-skript för massuppdatering av imports.

Enhetstest: Tillägg i testsviten som verifierar att gamla referenser inte används.

CI‑integration: Nytt GitHub Actions‑jobb som kör placement_verify.py och bryter bygget vid avvikelser.

