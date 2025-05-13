# Bitfinex Integration & Trading Bot Best Practices

Detta dokument sammanfattar rekommendationer och lösningar för vanliga problem när en tradingbot interagerar med Bitfinex via API.

---
## 1. Autentisering och konfiguration

- Använd API-nycklar (API Key & Secret) med minst privilegier: aktivera endast de rättigheter boten behöver (orders, balans, läsdata).
- Spara nycklar säkert i en `.env`–fil eller hemligt valv (Key Vault, Azure Key Vault) – aldrig hårdkoda.
- Ladda och validera miljövariabler vid uppstart (som ni redan gör i `script_start.sh`).

## 2. Bibliotek och beroenden

- Använd CCXT för förenklad access:
  ```python
  import ccxt
  exchange = ccxt.bitfinex({
      'apiKey': os.getenv('BITFINEX_API_KEY'),
      'secret': os.getenv('BITFINEX_API_SECRET'),
  })
  ```
- Kontrollera version och uppdatera regelbundet för att få senaste fixar.

## 3. Hastighetsbegränsningar (Rate Limits)

- Bitfinex tillåter upp till **10 REST-förfrågningar per sekund**.
- Bitfinex ger **30 REST-förfrågningar per minut** för plattformsstatus-endpointen.
- Övriga publika REST-endpoints: upp till 10 reqs/sek.
- Justera limiter efter endpoint: t.ex. fler requests/min för marknadsdata, färre för orderhantering.
- Hämta aktuella gränser från docs: https://docs.bitfinex.com/reference#rest-public-rates-limits
- Implementera en enkel limiter/pacing:
  ```python
  import time
  LAST_CALL = 0
  def rate_limit():
      global LAST_CALL
      delta = time.time() - LAST_CALL
      if delta < 0.11:
          time.sleep(0.11 - delta)
      LAST_CALL = time.time()
  ```
- För WebSocket: håll anslutningen vid liv, hantera heartbeats.

## 4. Felsäkert (Robust) API-anrop

- Inför retry-logik med exponential backoff:
  - HTTP 429 (Too Many Requests)
  - 5xx (serverfel)
- Exempel med `tenacity`:
  ```python
  from tenacity import retry, wait_exponential, stop_after_attempt
  @retry(wait=wait_exponential(multiplier=1, max=10), stop=stop_after_attempt(5))
  def place_order(...):
      return exchange.create_order(...)
  ```

## 5. WebSocket för marknadsdata

- Minimerar REST-kall och sparar latens.
- Hantera automatisk återanslutning:
  - Fånga avbrott
  - Vänta + exponetiell backoff
  - Resubskribera till orderbook-, trades-kanaler

## 6. Orderhantering & synkronisering

- Efter skapande av limit-order, verifiera med `fetch_order(id)` att status stämmer.
- Använd idempotenta nycklar om möjligt.
- Hantera partial fills och cancellerade ordrar.

## 7. Testning mot simulering

- Använd Bitfinex Paper Trading-konto i din vanliga Bitfinex UI:
  - Skapa API-nycklar under ditt Paper Trading-konto och spara dem som miljövariabler (`BITFINEX_API_KEY`, `BITFINEX_API_SECRET`).
- Använd samma REST- och WS-URL: `api-pub.bitfinex.com` respektive `wss://api.bitfinex.com/ws/2`.
- Verifiera via `/v2/auth/r/orders` att fälten `account`/`wallet` pekar på ditt Paper Trading-konto.

## 8. Loggning & övervakning

- Logga:
  - Begäran/respons
  - Felkoder
  - Latens (timestamp före/efter)
- Exempel med standard `logging`:
  ```python
  logger.info("Order placed: %s", order)
  logger.error("API error: %s", e)
  ```
- Integrera med monitoring (Prometheus, Grafana, Azure Monitor).

## 9. Säkerhet & drift

- Regelbunden rotation av API-nycklar.
- Begränsa IP-adresser i nyckelinställningar.
- Backup/restore av konfigurering.

## 10. Plattformstatus & Underhållshantering

- Endast REST: GET https://api-pub.bitfinex.com/v2/platform/status (30 reqs/min).
- WebSocket events **20060** (maintenance start) & **20061** (maintenance end).
  ```python
  # Exempel: hantera maintenance via WS
  def on_event(msg):
      if msg[1] == 20060:
          bot.pause_trading()
      elif msg[1] == 20061:
          bot.resume_trading()
  ```

## 11. REST Public Endpoints

Bitfinex erbjuder flera publika REST-resurser för marknadsdata:

### Ticker
- GET https://api-pub.bitfinex.com/v2/ticker/{symbol}
- Exempel: `GET /v2/ticker/tBTCUSD`
- Respons: `[ BID, BID_SIZE, ASK, ASK_SIZE, DAILY_CHANGE, ... ]`
```python
resp = requests.get(f"https://api-pub.bitfinex.com/v2/ticker/{symbol}")
data = resp.json()
bid, ask = data[0], data[2]
```

### Trades
- GET https://api-pub.bitfinex.com/v2/trades/{symbol}/hist
- Parametrar: `limit`, `start`, `end`, `sort`

### Orderbook
- GET https://api-pub.bitfinex.com/v2/book/{symbol}/{precision}
- Precision: `P0`–`P3` eller `R0`

### Candles
- GET https://api-pub.bitfinex.com/v2/candles/trade:{timeframe}:{symbol}/hist
- Timeframe: `1m`, `5m`, `1h`, `1D` etc.

Läs fullständig lista på https://docs.bitfinex.com/reference/rest-public

## 12. Authenticated REST Endpoints

För orderhantering och kontoinformation krävs signering:

### Skapa order
- POST https://api-pub.bitfinex.com/v2/auth/w/order/submit
```python
order = exchange.create_order(symbol, 'limit', 'buy', amount, price)
```

### Uppdatera och avboka
- `update_order` och `cancel_order` via CCXT
- Direkta REST-kall: `/v2/auth/w/order/update`, `/v2/auth/w/order/cancel`

### Konto & plånböcker
- ID: `/v2/auth/r/wallets`, `/v2/auth/r/login/hist`

Se https://docs.bitfinex.com/reference/rest-auth för alla endpoints.

## 13. WebSocket Public Endpoints

Effektiv realtidsström av marknadsdata:

```json
// Exempelprenumeration
{ "event": "subscribe", "channel": "ticker", "symbol": "tBTCUSD" }
```
- Server: `wss://api-pub.bitfinex.com/ws/2`
- Kanaler: `ticker`, `trades`, `book`, `candles`, `status`
- Heartbeat: händelser för anslutningskontroll
- Reconnect: exponetiell backoff + återprenumeration

## 14. WebSocket Authenticated Endpoints

Autentisera först:
```json
{ "event": "auth", "apiKey": KEY, "authSig": SIG, "authNonce": NONCE, "authPayload": PAYLOAD }
```
- Kanaler: `orders`, `positions`, `balance`, `wallets`, `notifications`
- Meddelandeformat: `[ CHANNEL_ID, "on", [ ORDER_ARRAY ] ]`

## 15. Felhantering

### REST
- 429: Too Many Requests → backoff + retry
- 4xx/5xx → logga och återförsök med exponential backoff

### WebSocket
- `{ "event": "error", "msg": ... }` → stäng + reconnect
- Timeout: om inget hjärtslag → reconnect

---
## 16. Symbol Naming & Konfiguration

- Trading pairs: prefix ‘t’ följt av BASE+QUOTE, t.ex. `tBTCUSD`, `tETHBTC`.
- Funding-valutor: prefix ‘f’, t.ex. `fUSD`, `fBTC`.
- Hämta giltiga symboler dynamiskt:
  - REST: `GET /v2/conf/pub:list:pair:exchange` → lista alla trading-par.
  - WS: prenumerera på `conf`-kanal om tillgängligt.
- Exempel med CCXT:
  ```python
  symbols = exchange.public_get_conf_pub_list_pair_exchange()
  print(symbols)  # ['BTCUSD', 'ETHBTC', ...]
  # CCXT lägger till 't' automatiskt för trade-symboler
  ```
- Före order: kontrollera att symbol finns i listan för att undvika HTTP 400.

---
## Referenser

- Bitfinex API docs: https://docs.bitfinex.com
- CCXT docs: https://docs.ccxt.com
- Tenacity (Python retry-lib): https://github.com/jd/tenacity
