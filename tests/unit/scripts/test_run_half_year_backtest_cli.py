"""CLI tests for run_half_year_backtest script."""

from scripts.market_data import run_half_year_backtest as half_year_cli


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
