# Uprościć układ katalogów danych rynkowych

Status: in progress. Blocked by: none. Delivery path: standalone high-risk task
(storage contract); existing files are never migrated or removed in this ticket.

## Outcome

New market datasets use
`market_data/{raw|normalized}/{asset_class}/{provider}/{instrument}/{timeframe}/`.
Dataset files identify their data type, source series and version in the filename,
for example `ohlcv.binance-usdm-klines-v1.v1.parquet`. The explicit asset class
is part of new `DatasetRef` identities. `USA500.IDX-USD` from Dukascopy is `cfd`,
while Binance `BTCUSDT.P` is `crypto`.

## Acceptance criteria

- New writes use the specified directory order without `ohlcv`, source-id or
  version directories between the instrument and file.
- The asset class is explicit; Dukascopy CFD must not be classified as futures.
- Historical five-field `DatasetRef` values continue to resolve old files.
- Tests cover new writes, old reads, and two source series in one directory.

## Verification and rollback

Run Market Data unit and integration tests, then Ruff, mypy and pytest. If the
change is rolled back, old datasets remain where they were. New files require
this version of the reader until the separate migration is delivered.

## Follow-up order

Ticket 2 migrates existing files after this ticket. Ticket 3 removes legacy
read support only after ticket 2. Neither is included here.
