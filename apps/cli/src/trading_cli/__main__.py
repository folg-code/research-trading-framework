"""Console-script entry point for `trading-cli` (`[project.scripts]`)."""

from __future__ import annotations

import sys

from trading_cli.cli import main as _main


def main(argv: list[str] | None = None) -> int:
    return _main(argv)


if __name__ == "__main__":
    sys.exit(main())
