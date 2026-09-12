# Documentation restructuring audit — 2026-09-12

## Scope and evidence

The maintainer approved a documentation-first review of the whole repository,
with targeted checks against code and tests for important implementation
claims. The review covers `docs/`, root entry points, agent instructions and
the dashboard's Markdown links. No runtime contract was intentionally changed.

The pre-review inventory found 247 files in `docs/`, including 83 documents
over 250 nonempty lines. The final layout has 338 Markdown files because
mixed documents and large registries were split into focused pages. Every
file moved from an old path has an entry in [path-map.csv](path-map.csv):
132 moves, mostly completed sprint evidence into `docs/archive/phases/`.

## Classification and decisions

| Action | Result |
|---|---|
| Keep / link / index | Root `AGENTS.md`, `docs/README.md` and the section READMEs now route readers from overview to module, workflow and contract. |
| Edit | Current status, roadmap, system overview, module map, vision and agent entry points were made shorter and given distinct temporal roles. |
| Split | Large planning registries, Phase 16, research methodologies, analysis workspace and the old module map were divided by topic. Stable IDs and section links were retained where possible. |
| Move / archive | Finished sprint records and historical audits are indexed under `docs/archive/`; active sprint 062 and draft sprint 063 remain in planning. |
| ADR | ADR files remain together. Their index now has consistent area classification, and the Market Analysis decision register sits beside them. Accepted ADR prose was preserved. |
| Snapshot | Pre-review versions of materially rewritten documents live under `docs/archive/snapshots/` to retain provenance and support comparison. |

`reference/modules/` follows source ownership by capability rather than one
file per Python package. `vision/` describes future direction; as-built
behavior is routed to `reference/`, and completed work to the archive.

## Deliberate length exceptions

The Market Analysis agent contract, architecture principles, domain model,
Market Analysis architecture, strategy examples, the AWS dry-run runbook and
individual ADRs remain long because their sections form cohesive contracts,
operational procedures, worked examples or immutable decision records. They
are reached only from short indexes or topic-specific links; the two longest
living contracts have a local navigation summary. Length was treated as a
reading-cost guide, not as a hard limit.

## Validation

- `python scratch/validate_docs.py`: 932 local Markdown links checked across
  338 files; no missing files or anchors. The script is a local, ignored
  migration helper, not a new project dependency.
- The skill-prescribed `node .ai-toolkit/bin/devteam.mjs validate` could not
  run: `.ai-toolkit/bin/devteam.mjs` is absent from this checkout.
- `uv run ruff check .`: passed.
- `uv run mypy`: passed (994 source files).
- `uv run pytest`: 1919 passed, 19 skipped, 37 warnings.
- `uv run ruff format --check .`: failed on 116 Python files already outside
  this documentation change; those files were not reformatted as part of the
  migration.

The migration intentionally preserved historical prose. Its links were
rebased so archived records remain navigable from their new locations.
