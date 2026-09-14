"""Structured phase events for `research run signal` (Sprint 064 T005).

D-S064-04 / ADR-0041 section 7 (Tier 1, the only tier this sprint implements):
one newline-delimited JSON object per line, on stdout, naming the phase that
just STARTED. The workbench job runner parses only these structured lines;
everything else on stdout stays ordinary human-readable text, surfaced
verbatim as logs. No percentage, ETA, row count or other number is ever
derived from prose -- if a fact is not one of these events, the runner does
not know it.

Emission is gated on `--json` (ADR-0041 section 2: the workbench always
spawns `trading-cli ... --json`), so a human running the CLI interactively
from a terminal keeps the exact output this command already had -- no event
lines mixed into it.

Sprint 064 emits this schema for `research.run.signal` only. D-S064-04 also
declares (but does not yet emit) phase lists for `data.import.local` and
`data.fetch.binance`; those are 17C's to implement.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

PHASE_EVENT_SCHEMA_VERSION = "workbench.phase_event.v1"

#: The declared, static, ordered phase list for `research.run.signal`
#: (D-S064-04): the seams in resolve_signal_research_definition ->
#: map_definition_to_run_request -> run_signal_research. `evaluate` is the
#: long one and is honestly a single opaque phase; `persist` is emitted once
#: `run_signal_research` returns successfully, since that call bundles
#: evaluation and persistence with no observable boundary between them this
#: sprint (ADR-0041 section 7's Tier 2 `ProgressSink` remains deferred) --
#: consistent with "a job that fails mid-phase emits no further phase
#: events", a failure during persistence simply never emits this event.
SIGNAL_RESEARCH_RUN_PHASES: tuple[str, ...] = (
    "load-definition",
    "resolve-models",
    "load-dataset",
    "evaluate",
    "persist",
)

_SIGNAL_RESEARCH_JOB_KIND = "research.run.signal"


def emit_signal_research_phase(name: str, *, json_mode: bool) -> None:
    """Print one `workbench.phase_event.v1` line for `research.run.signal`.

    A no-op unless `json_mode` -- see the module docstring for why emission
    is gated on `--json` rather than unconditional.
    """
    if not json_mode:
        return
    index = SIGNAL_RESEARCH_RUN_PHASES.index(name) + 1
    event = {
        "schema_version": PHASE_EVENT_SCHEMA_VERSION,
        "event": "phase",
        "job_kind": _SIGNAL_RESEARCH_JOB_KIND,
        "name": name,
        "index": index,
        "of": len(SIGNAL_RESEARCH_RUN_PHASES),
        "at": datetime.now(tz=UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }
    print(json.dumps(event, sort_keys=True), file=sys.stdout, flush=True)
