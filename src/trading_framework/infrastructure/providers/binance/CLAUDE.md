# infrastructure/providers/binance

Responsibility: Binance USD-M futures adapters — live WebSocket streaming,
REST reconnect gap-fill, and the paginated historical klines reader. Owns all
`urllib`/HTTP/JSON handling for Binance; nothing above this package touches
raw Binance payloads.

## Gotchas

- `futures_mapper.map_kline_payload` hard-rejects any `BinanceKlinePayload`
  whose `interval != "1m"` (`ValidationError: only 1m Binance kline payloads
  are supported`). It was written for the live 1m kline stream (Sprint 019)
  and is reused as-is by `futures_klines_history.fetch_historical_klines`
  (Sprint 045, ADR-0025) to avoid touching the live path. **Practical
  consequence:** `fetch_historical_klines` — and therefore
  `application.market_data.import_binance_futures_ohlcv` — only actually
  works for `interval="1m"`. D-S045-05 was corrected after this was found in
  Wave 2 to state `1m` only for v1 (it originally listed `5m`, `15m`, `1h`,
  `4h`, `1d`, before the mapper limitation was discovered). Importing any
  non-`1m` interval raises at the first decoded row. Widening
  `map_kline_payload` (or adding an interval-aware variant) is tracked as
  **TD-023** in `docs/planning/TECHNICAL_DEBT.md`, not fixed here to avoid
  touching the live reconnect path outside its own increment.
- `fetch_closed_klines` (live reconnect gap-fill) and
  `fetch_historical_klines` (archive import) are deliberately **not**
  unified. Duplicate a helper here rather than share one that risks changing
  the live path's behaviour (D-S045-04).
