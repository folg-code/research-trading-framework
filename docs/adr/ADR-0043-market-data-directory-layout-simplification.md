# ADR-0043 — Market-Data Directory Layout Simplification and Asset-Class-Qualified Dataset Identity

## Status

PROPOSED

Drafted implementing the maintainer's own ticket
(`docs/vision/MARKET_DATA_LAYOUT_TICKET.md`, status `in progress`) rather
than a maintainer-approval conversation transcript — the maintainer wrote
the ticket's acceptance criteria themselves. Recorded as `PROPOSED` per this
project's governance rule that no agent marks its own ADR `ACCEPTED`; the
maintainer's review of the implementing PR is the approval step.

## Context

`ADR-0008` (Parquet Historical Storage, Sprint 002) specified a "suggested
logical layout" for market-data storage:

```text
user_data/data/
├── metadata/<instrument>/<data_type>/<timeframe>/<provider>/<source_id>/v<version>.json
└── normalized/<instrument>/<data_type>/<timeframe>/<provider>/<source_id>/v<version>/bars.parquet
```

Two problems accumulated since:

1. **The documented root was already stale.** The actual implementation
   (`src/trading_framework/infrastructure/storage/paths.py`) has used
   `market_data/` as the root since at least Sprint 011 (`ADR-0014`), not
   `user_data/data/` — a pre-existing doc/code drift independent of this
   ADR.
2. **The layout itself grew unwieldy for a human browsing the filesystem.**
   Five identity segments (`instrument/data_type/timeframe/provider/
   source_id`) plus a `v{version}` directory sit between the market-data
   root and the actual Parquet/JSON file — for the common case (one
   provider, one source series per instrument/timeframe), most of that
   nesting carries no information a human needs to navigate by. The
   maintainer's own ticket names the target shape directly: `market_data/
   {raw|normalized}/{asset_class}/{provider}/{instrument}/{timeframe}/` with
   the data type, source series and version disambiguated in the filename
   instead of the directory chain.
3. **`DatasetId` had no asset-class concept at all.** Classification
   (crypto vs. futures vs. equity vs. fx) existed only on the separate
   `Instrument` domain model, never on the dataset's own storage identity —
   so a directory layout keyed by asset class had nothing to key on, and a
   future importer could default an instrument's class incorrectly (the
   ticket names a concrete risk: a Dukascopy CFD instrument silently
   classified `futures`) with no structural guard against it.

## Decision

### 1. `DatasetId.asset_class: AssetClass | None = None`

Optional, and deliberately never inferred or defaulted:

```text
None      legacy identity -- every DatasetId that existed before this ADR,
          and the only value DatasetRef.parse() produces for an old
          5-field canonical string. Resolves through the LEGACY layout
          (unchanged) below. Never migrated or rewritten by this ADR.
set       new identity -- every DatasetId a caller constructs going
          forward MUST set this explicitly. Resolves through the NEW
          layout below.
```

`AssetClass` (`src/trading_framework/market/models/instrument.py`) gains a
`CFD` member alongside the existing `FUTURES`/`EQUITY`/`CRYPTO`/`FX`.

### 2. Two storage layouts, selected by `DatasetId.asset_class`

```text
NEW (asset_class set):
    market_data/{metadata|normalized}/{asset_class}/{provider}/{instrument_id}/{timeframe}/
        {data_type}.{source_id}.v{version}.{json|parquet}

    e.g. market_data/normalized/crypto/binance/BTCUSDT.P/1m/
         ohlcv.binance-usdm-klines-v1.v1.parquet

LEGACY (asset_class unset, unchanged from ADR-0008's implementation):
    market_data/{metadata|normalized}/{instrument_id}/{data_type}/{timeframe}/{provider}/{source_id}/v{version}/...
```

The new layout has no `v{version}` *directory* — version moves into the
filename alongside data type and source id, which is also what
disambiguates two source series for the same instrument/timeframe sharing
one directory (the ticket's explicit acceptance criterion). This is
implemented as two private helpers in `paths.py`
(`_new_layout_dataset_dir` / `_legacy_layout_dataset_dir`); every public
path function (`dataset_metadata_path`, `dataset_bars_path`,
`dataset_ohlcv_partitions_dir`, `continuous_ohlcv_manifest_path`) branches
on `dataset_id.asset_class is not None` and calls the matching helper — the
branch lives in one place per function, not duplicated ad hoc.

### 3. `DatasetRef` canonical string: 5 fields (legacy) or 6 (new)

```text
legacy   {instrument}|{data_type}|{timeframe}|{provider}|{source_id}@{version}
new      {instrument}|{data_type}|{timeframe}|{provider}|{source_id}|{asset_class}@{version}
```

`DatasetRef.parse()` accepts both lengths and maps `asset_class` accordingly
(5 fields → `None`; 6 → the parsed `AssetClass`, refused with
`ValidationError` if the trailing field isn't a known member). This is the
acceptance criterion "reads through an existing `DatasetRef` keep working" —
every `DatasetRef` value persisted, logged, or embedded in an existing
manifest before this ADR still parses and still resolves to the same
physical file it always did.

### 4. `discovery.list_dataset_refs` branches the same way

Version-listing globs `v*.json` sibling files for a legacy identity (as
before) or `{data_type}.{source_id}.v*.json` for a new identity, parsing the
version out of the filename rather than the directory name.

### 5. Scope: OHLCV only in this ADR, trades explicitly deferred

Only the OHLCV-shaped path functions gained the new-layout branch. Trade
datasets (`dataset_contract_trades_partition_path`,
`dataset_trades_partition_path`, and their continuous-futures counterparts
in `continuous_trade_repository.py`) are untouched and remain legacy-only —
matching the ticket's own explicit example (OHLCV) and its stated follow-up
ordering: a second ticket migrates existing files to the new layout, a
third removes legacy read support, both dependent on this one. Extending
the new layout to trade datasets is a decision for whichever ticket takes
that up, not assumed here.

Two production call sites were wired to the new layout, matching the
ticket's own worked example and the only two OHLCV-producing writers that
exist today:

```text
import_binance_futures_ohlcv.py   asset_class=CRYPTO  (Binance USD-M
                                   perpetuals are a crypto derivative, not
                                   traditional-exchange futures -- the
                                   ticket's own example)
build_continuous.py               asset_class=FUTURES (continuous futures
(_continuous_ohlcv_dataset_id)    like NQ.c.0, ES.c.0 are genuinely
                                   futures instruments)
```

No Dukascopy/CFD importer exists yet in this codebase (confirmed by
repository search); the `CFD` member and the "never inferred" rule exist to
structurally prevent the misclassification the ticket names, once such an
importer is written — this ADR does not itself add one.

## Consequences

### Positive

- A human browsing `market_data/normalized/` sees asset class, provider,
  instrument and timeframe directly — no `v1`/source-id noise between
  instrument and file for the common case.
- Two source series for one instrument/timeframe coexist in one directory
  without a path collision (filename-level disambiguation).
- `DatasetId` now carries the same asset-class concept `Instrument` always
  had, closing a real classification gap the ticket names concretely
  (Dukascopy CFD vs. futures).
- Zero data migration required to ship this: every existing file stays
  exactly where it is, addressed exactly as it always was.

### Negative

- Two storage layouts now coexist indefinitely until tickets 2 and 3 land —
  `paths.py` carries a permanent branch until then, and any new path
  function added to this module must remember to branch too (nothing
  enforces this structurally beyond code review).
- Trade datasets do not get the simplified layout in this ADR — an operator
  browsing `market_data/normalized/` will see OHLCV under the new shape and
  trades under the old shape side by side until a follow-up ticket unifies
  them.
- `discovery.list_dataset_refs`'s two glob strategies must both keep
  working correctly as the codebase evolves; a future change to either
  filename convention needs to update this function too, not just
  `paths.py` (already true before this ADR for the legacy shape; now true
  for two shapes).

### Neutral

- `asset_class` is optional at the type level for backward compatibility
  only. No code path may treat `None` as a valid choice for a *newly
  constructed* identity — that discipline lives in code review and this
  ADR, not in a language-level guarantee (a `TD` entry may be warranted if
  a future call site is found constructing a new identity without setting
  it).

## Alternatives Considered

1. **Migrate all existing files to the new layout immediately, in this same
   change.** Rejected: a physical migration is materially riskier than a
   backward-compatible dual-read scheme, and the maintainer's own ticket
   explicitly sequences it as a separate, dependent follow-up ticket.
2. **Make `asset_class` required on `DatasetId` (no `None`).** Rejected: it
   would force either a migration in this same change (see above) or a
   fabricated default asset class for every historical identity, which is
   exactly the "silent inference" failure mode this ADR exists to prevent.
3. **Extend the new layout to trade datasets too, in this same change.**
   Rejected: larger blast radius (touches `continuous_trade_repository.py`
   and its hardcoded partition filename) for no acceptance-criterion
   requirement; the ticket's own examples and follow-up ordering scope this
   ADR to OHLCV.

## Follow-up

- Ticket 2 (referenced in `docs/vision/MARKET_DATA_LAYOUT_TICKET.md`):
  migrate existing legacy-layout files to the new layout.
- Ticket 3: remove legacy read support once ticket 2's migration is
  complete and verified.
- Whether/how trade datasets adopt the new layout is an open question for
  whichever ticket takes it up — not decided here.
- `docs/reference/workflows/MARKET_DATA.md`'s "Futures Contract Identity"
  section should eventually cross-reference `asset_class` as an explicit
  identity field.

## Related

- `docs/adr/ADR-0008-parquet-historical-storage.md` — the original storage
  format and (now-superseded, for OHLCV) suggested layout decision this ADR
  updates; ADR-0008's own content is left unedited per this project's ADR
  convention (a changed decision gets a new ADR, not a rewrite).
- `docs/adr/ADR-0014-historical-archive-import-and-market-trade-storage.md`
  — established the `market_data/` root name this ADR's layout continues to
  use.
- `docs/vision/MARKET_DATA_LAYOUT_TICKET.md` — the maintainer's own ticket
  this ADR implements.
