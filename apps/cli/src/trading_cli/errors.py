"""Error taxonomy and exit codes for `trading-cli` (D-S046-09).

```text
0   success
1   workflow failure   -- a wrapped workflow raised, returned non-zero, or
                           (until Wave 2 lands its body) is not implemented yet
2   configuration/usage error -- bad YAML, unknown key, missing required key,
                                  credential-shaped key, bad CLI arguments
```

An operator must never see a raw `argparse` usage message referring to flags
they never typed. Where the `main(argv)` fallback is used in a later wave,
`SystemExit` raised by `argparse.parse_args` is caught and translated into a
`ConfigError` here.
"""

from __future__ import annotations

EXIT_SUCCESS = 0
EXIT_WORKFLOW_FAILURE = 1
EXIT_CONFIG_ERROR = 2


class CliError(Exception):
    """Base class for controlled `trading-cli` failures with an exit code."""

    exit_code: int = EXIT_CONFIG_ERROR


class ConfigError(CliError):
    """Bad YAML, a schema violation, or a bad CLI argument (exit code 2)."""

    exit_code = EXIT_CONFIG_ERROR


class WorkflowError(CliError):
    """A wrapped application-layer workflow raised or failed (exit code 1)."""

    exit_code = EXIT_WORKFLOW_FAILURE


class NotImplementedCommandError(WorkflowError):
    """The command's application-layer wiring has not shipped yet.

    Wave 1 (this package) builds the argument/config/plan skeleton only; every
    command body lands in Wave 2 (S046-T005..T009). Until then, invoking a
    command outside ``--dry-run`` fails clearly instead of crashing.
    """
