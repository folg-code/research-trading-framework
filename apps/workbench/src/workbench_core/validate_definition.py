"""Preflight validation of a Signal Research definition (Sprint 064 T008).

`trading-cli research run signal --config <f> --dry-run --json` is the
framework's own single source of truth for whether a definition resolves
(ADR-0038 section 3). This module writes the operator's edited definition to
a temporary file, wraps it in a `trading-cli` config, and runs exactly that
command synchronously -- it never re-validates, re-parses, or reimplements
any part of `SignalResearchDefinitionSpec`'s own validation (ADR-0038
section 1). The rendered error text an operator sees on a bad value is
`trading-cli`'s own, verbatim, not a workbench-authored message.

ADR-0041 section 2's "one job = one subprocess" rule is about *jobs*
(work that runs `run_signal_research`); a `--dry-run` never touches
`SignalResearchDatasetRepository.write` or any other side effect, so this
synchronous, unqueued, off-the-FIFO validate call does not compete with
`JobRunner`'s D-S064-03 concurrency limit -- it is a read, not a job.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from workbench_core.job_runner import DEFAULT_CLI_COMMAND, repo_root

_VALIDATE_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class ValidateSignalResearchDefinitionRequest:
    definition: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    """Exactly one of `plan` or `error_message` is set."""

    ok: bool
    plan: dict[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None


async def validate_signal_research_definition(
    request: ValidateSignalResearchDefinitionRequest,
    *,
    storage_root: Path,
    cli_command: Sequence[str] = DEFAULT_CLI_COMMAND,
) -> ValidationOutcome:
    with tempfile.TemporaryDirectory(prefix="workbench-validate-") as tmp:
        tmp_dir = Path(tmp)
        definition_path = tmp_dir / "definition.yaml"
        definition_path.write_text(
            yaml.safe_dump(request.definition, sort_keys=False), encoding="utf-8"
        )
        config_path = tmp_dir / "config.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "storage_root": str(storage_root.resolve()),
                    "research": {
                        "kind": "signal",
                        "signal": {"definition": str(definition_path)},
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        process = await asyncio.create_subprocess_exec(
            *cli_command,
            "research",
            "run",
            "--config",
            str(config_path),
            "--dry-run",
            "--json",
            cwd=str(repo_root()),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=_VALIDATE_TIMEOUT_SECONDS
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return ValidationOutcome(
                ok=False,
                error_type="TimeoutError",
                error_message=f"validation did not finish within {_VALIDATE_TIMEOUT_SECONDS}s",
            )

    if process.returncode == 0:
        payload = _parse_json(stdout)
        plan = payload.get("plan") if isinstance(payload, dict) else None
        if isinstance(plan, dict):
            return ValidationOutcome(ok=True, plan=plan)
        return ValidationOutcome(
            ok=False,
            error_type="UnexpectedOutputError",
            error_message="trading-cli exited 0 but printed no parseable dry-run plan",
        )

    payload = _parse_json(stderr) or _parse_json(stdout)
    if isinstance(payload, dict) and payload.get("status") == "error":
        return ValidationOutcome(
            ok=False,
            error_type=payload.get("error_type"),
            error_message=payload.get("message"),
        )
    return ValidationOutcome(
        ok=False,
        error_type="UnknownError",
        error_message=(stderr or stdout).decode("utf-8", errors="replace").strip()
        or f"trading-cli exited {process.returncode} with no output",
    )


def _parse_json(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
