"""Smoke test for the contract chunk column microbench script."""

from __future__ import annotations

from scripts.ops.bench_contract_chunk_columns import main


def test_bench_contract_chunk_columns_smoke() -> None:
    assert main(["--rows", "1000", "--chunks", "2", "--take-fraction", "0.5"]) == 0
