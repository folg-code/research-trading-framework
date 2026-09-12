# Sprint 051 — BTCUSDT.P Data Inventory (S051-T002)

Data acquisition record for the Binance USD-M historical OHLCV import run
for Sprint 051 (Phase 15A). This document is the measured, factual output of
running Sprint 045's importer (ADR-0025) via `trading-cli data fetch
binance`; **no framework code was modified to produce it.**

```text
Task:      S051-T002
Range:     maintainer-fixed, D-S051-07 (BTCUSDT.P, 1m, 2024-01-01 -> 2026-06-30)
Outcome:   SUCCESS — one PUBLISHED DatasetRef, zero gaps, zero rejected rows
Date run:  2026-09-03
```

---

## 1. Command used

```powershell
uv run --project apps/cli trading-cli data fetch --config scratch/s051_btc_import.yaml --json
```

Config (not committed — a scratch file, mirroring
`apps/cli/examples/data_fetch_binance.yaml`'s shape with the maintainer-fixed
range substituted):

```yaml
version: 1
storage_root: user_data/workspace

data:
  provider: binance
  binance:
    mode: ohlcv
    symbol: BTCUSDT
    instrument_id: BTCUSDT.P
    interval: 1m
    start: 2024-01-01T00:00:00Z
    end: 2026-06-30T00:00:00Z
    publish: true
```

`--dry-run` was run first (twice — see §5) to confirm the resolved plan
before any network call, per the example config's own guidance. A 1-hour
smoke-range fetch (`2024-01-01T00:00:00Z` -> `2024-01-01T01:00:00Z`) was run
before the full-range import to confirm network/auth behaviour cheaply; it
produced 60 rows, `api_key_used: false`, and was discarded before the full
import ran (see §5) — it did not become part of the published range below
and is not otherwise part of the deliverable.

No API key was configured in this environment
(`TRADING_FRAMEWORK_BINANCE_API_KEY` unset). Per ADR-0025 §5, the key is
optional and raises only the request-weight limit on public market-data
endpoints; anonymous requests are fully supported for this endpoint. The
import ran anonymously and completed without hitting a rate limit that
required a key.

---

## 2. Published `DatasetRef` — measured facts

Read directly from the registry metadata JSON,
`user_data/workspace/market_data/metadata/BTCUSDT.P/ohlcv/1m/binance/binance-usdm-klines-v1/v1.json`
(not from the request):

```text
dataset_ref:       BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1
lifecycle_status:  published
validation_status: passed
start_at:          2024-01-01T00:00:00+00:00
end_at:             2026-06-29T23:59:00+00:00   (open time of the last bar)
row_count:         1,311,840
checksum:          df83ecfaba111aeaad24d68905e3e978a11e8ef968f3f7429d3df0aaea28ffed
created_at:        2026-09-03T07:57:30.574664+00:00
published_at:      2026-09-03T07:58:05.911913+00:00
```

`end_at` is the **open time** of the last persisted bar, consistent with the
requested half-open `[start, end)` range (ADR-0025 §3): the request's
`end=2026-06-30T00:00:00Z` is exclusive, so the last bar is
`2026-06-29T23:59:00+00:00` (closing at `2026-06-29T23:59:59.999Z`, per
`last_bar_close_time` in the manifest below).

`row_count` (1,311,840) equals exactly `911 days x 1,440 minutes/day`, i.e.
one bar per minute with no missing or duplicated timestamps over the entire
requested range — consistent with `gap_count: 0` below.

---

## 3. `import_manifest.json` — every recorded gap

Read directly from
`user_data/workspace/market_data/normalized/BTCUSDT.P/ohlcv/1m/binance/binance-usdm-klines-v1/v1/import_manifest.json`:

```json
{
  "provider": "binance",
  "mode": "ohlcv",
  "symbol": "BTCUSDT",
  "instrument_id": "BTCUSDT.P",
  "interval": "1m",
  "requested_start": "2024-01-01T00:00:00+00:00",
  "requested_end": "2026-06-30T00:00:00+00:00",
  "first_bar_open_time": "2024-01-01T00:00:00+00:00",
  "last_bar_close_time": "2026-06-29T23:59:59.999000+00:00",
  "page_count": 875,
  "request_count": 875,
  "retry_count": 0,
  "rows_decoded": 1311840,
  "rows_rejected": 0,
  "gaps": [],
  "normalization_version": "binance-usdm-klines-v1",
  "schema_version": "market-bar-v1",
  "api_key_used": false
}
```

**Gap count: 0.** No page in the full 30-month, 875-request pagination
sequence returned zero rows inside the requested range, so `gaps` is empty
and every requested minute is backed by a real, decoded bar
(`rows_rejected: 0`, all 1,311,840 requested minutes decoded and passed
`OhlcvBarValidator`).

**`api_key_used: false`** — confirmed at the manifest level, matching the
registry-level observation in §1: the import ran fully anonymously.

---

## 4. Observed wall-clock and weight-limit behaviour

```text
Import launched (repo-root, UTC):   2026-09-03T07:49:29Z
Registry record created_at:          2026-09-03T07:57:30.574664+00:00
Dataset published_at:                2026-09-03T07:58:05.911913+00:00
Observed wall-clock (launch -> publish): ~8 minutes 36 seconds
```

**Backoff / retries: none.** `retry_count: 0` in the manifest — the
importer's weight governor (`DEFAULT_WEIGHT_LIMIT_PER_MINUTE = 2400`,
`DEFAULT_WEIGHT_THROTTLE_RATIO = 0.8`, per `futures_klines_history.py`) never
had to pause the fetch loop or retry a `429`/`418`/`5xx` response across all
875 requests. This is faster than ADR-0025's own Consequences section
anticipates for "a year of 1m bars" — anonymous throughput for this endpoint
was evidently ample for this range on the day this import ran; the ADR's
caution about multi-hour imports is a stated worst case, not a guarantee,
and this run did not exercise the backoff path at all.

---

## 5. What was attempted before the successful run (for the record)

Two false starts, both harmless and both cleaned up before the successful
run below — recorded here for transparency, not because they represent a
problem with the range or the importer:

1. **First full-range attempt ran with the wrong working directory.**
   `storage_root: user_data/workspace` in the config is a path relative to
   the process's current working directory, not the repo root. Invoking the
   CLI from `apps/cli` (`cd apps/cli && uv run trading-cli data fetch ...`)
   resolved it to `apps/cli/user_data/workspace` instead of the repo-root
   `user_data/workspace` the maintainer's canonical workspace uses.
   **This also surfaced a real gap in the root `.gitignore`:** the
   `user_data/**` pattern has a slash in the middle, which makes it rooted
   to the `.gitignore` file's own directory (repo root) per git's own
   pattern semantics — it does **not** match `apps/cli/user_data/**` at a
   nested location. `git status` confirmed the misplaced files showed as
   untracked, not ignored. That partial run was killed
   (`kill <pid>`, exit via `SIGTERM`) before it could publish anything, and
   the misplaced directory (`apps/cli/user_data/`) was deleted before any
   commit. The successful run in §1 was invoked from the repo root so
   `storage_root` resolves to the correctly-gitignored, canonical
   `user_data/workspace`.
2. **A 1-hour smoke-range fetch** (§1) confirmed anonymous network access
   and the CLI's config-to-workflow wiring cheaply before committing to the
   full 30-month range. It produced a separate, smaller dataset version
   under the same dataset identity, which was not carried forward; only the
   full-range import in §2–§4 is the deliverable of this task.

Neither false start touched any file under `src/`, and nothing from either
attempt was committed. This is logged as a candidate module-context note for
`apps/cli/CLAUDE.md` (a gotcha about `storage_root` resolving relative to
invocation `cwd`, not repo root) — not a framework code change, and not part
of this task's scope to fix the `.gitignore` pattern itself. Tracked as
`TD-030` in `docs/planning/TECHNICAL_DEBT.md`, repayable opportunistically.

---

## 6. Sufficiency for Sprint 052's walk-forward study

**Yes — the imported range is sufficient for at least 5 walk-forward folds
at a reasonable horizon.**

The published range spans 2024-01-01 to 2026-06-29 (911 days, ~30 months) of
uninterrupted 1-minute bars. D-S051-07's own rationale (recorded in
`S051_WAVE0_DECISIONS.md`) sized this range for "six 30-day out-of-sample
folds with a multi-year expanding train window" — the measured range matches
that assumption exactly (zero gaps means the full 911 days is usable, not
just an expected subset). At a 30-day out-of-sample fold width, the range
supports roughly 30 non-overlapping 30-day windows, comfortably above the
5-fold minimum; even a coarser fold width (e.g. 60 or 90 days) still clears
5 folds with room for a multi-year expanding training window ahead of the
first fold. The exact fold boundaries, embargo, and evaluation timeframe are
Sprint 052's Wave 0 decision, not this task's — this section only confirms
the data volume does not block that design.

---

## 7. Compliance checklist (acceptance criteria)

- [x] Exact published `DatasetRef` string recorded (§2).
- [x] `start_at` / `end_at` / `row_count` read from the registry metadata
      JSON, not the request (§2).
- [x] Every gap listed from `import_manifest.json` (§3 — none recorded).
- [x] `api_key_used` recorded (§1, §3 — `false`).
- [x] Observed wall-clock and weight-limit backoff recorded (§4).
- [x] Sufficiency for >=5 walk-forward folds stated plainly (§6).
- [x] No file under `src/` modified by this task.
- [x] Nothing from `user_data/` committed — `user_data/workspace/...` stays
      local; only this document enters git.
- [x] D-S051-07a hard stop **not** triggered — the import succeeded, so no
      substitute instrument question arises.

---

## 8. Hand-off to Sprint 052

Per `S051_WAVE0_DECISIONS.md` D-S051-11, this document is one of the two
artifacts Sprint 052's Wave 0 needs before it can open:

```text
dataset_ref: BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1
range:       2024-01-01T00:00:00+00:00 -> 2026-06-29T23:59:00+00:00 (911 days)
row_count:   1,311,840
gaps:        none
```

Sprint 052 may proceed to plan its fold design against these measured facts.
