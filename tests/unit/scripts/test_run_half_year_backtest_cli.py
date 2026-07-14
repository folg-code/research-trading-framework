"""CLI tests for run_half_year_backtest script."""

from pathlib import Path

import pytest
from scripts.market_data import run_half_year_backtest as half_year_cli

from trading_framework.core.exceptions import ValidationError


def test_half_year_backtest_parser_accepts_profile_flags() -> None:
    parser = half_year_cli._build_parser()
    args = parser.parse_args(
        [
            "--storage-root",
            "user_data/storage",
            "--contract-dataset-ref",
            "NQ.NQU5|trades|tick|databento|nq-cme-trades-half-year@1",
            "--profile",
            "--profile-deep",
            "--profile-top",
            "25",
        ]
    )

    assert args.profile is True
    assert args.profile_deep is True
    assert args.profile_top == 25


def test_half_year_backtest_parser_accepts_skip_build_and_no_persist() -> None:
    parser = half_year_cli._build_parser()
    args = parser.parse_args(
        [
            "--storage-root",
            "user_data/storage",
            "--skip-build",
            "--no-persist",
            "--continuous-ohlcv-dataset-ref",
            "NQ.c.0|ohlcv|1m|derived|volume-rth-close@1",
        ]
    )

    assert args.skip_build is True
    assert args.no_persist is True
    assert args.refs is None
    assert args.continuous_ohlcv_dataset_ref == "NQ.c.0|ohlcv|1m|derived|volume-rth-close@1"


def test_main_requires_contract_refs_without_skip_build() -> None:
    exit_code = half_year_cli.main(
        [
            "--storage-root",
            "user_data/storage",
            "--continuous-ohlcv-dataset-ref",
            "NQ.c.0|ohlcv|1m|derived|volume-rth-close@1",
        ]
    )

    assert exit_code == 1


def test_resolve_continuous_ohlcv_dataset_ref_uses_explicit_ref() -> None:
    explicit = "NQ.c.0|ohlcv|1m|derived|volume-rth-close@1"
    resolved = half_year_cli.resolve_continuous_ohlcv_dataset_ref(
        storage_root=Path("user_data/storage"),
        product="NQ",
        policy_slug="volume-rth-close",
        explicit_ref=explicit,
    )

    assert str(resolved) == explicit


def test_resolve_continuous_ohlcv_dataset_ref_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="no published continuous OHLCV"):
        half_year_cli.resolve_continuous_ohlcv_dataset_ref(
            storage_root=tmp_path,
            product="NQ",
            policy_slug="volume-rth-close",
            explicit_ref=None,
        )
