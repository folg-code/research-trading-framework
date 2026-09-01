"""Loader test matrix for `trading_cli.strategy_loader` (S047-T004, ADR-0027 Sec5).

All nine D-S047-07 error rows, the same-stem collision guarantee, and a
`sys.path`-is-never-mutated assertion. Fixture files live under
`apps/cli/tests/fixtures/strategies/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from trading_framework.strategy import StrategyModelDefinition

from trading_cli.errors import ConfigError, WorkflowError
from trading_cli.strategy_loader import load_strategy_definition

_FIXTURES = Path(__file__).parent / "fixtures" / "strategies"


def test_loads_a_valid_strategy_file() -> None:
    loaded = load_strategy_definition(str(_FIXTURES / "valid_strategy.py"))

    assert isinstance(loaded.definition, StrategyModelDefinition)
    assert loaded.definition.strategy_model_id == "fixture_valid_strategy"
    assert loaded.strategy_file == (_FIXTURES / "valid_strategy.py").resolve()
    assert loaded.strategy_file.is_absolute()


def test_missing_path_is_config_error(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.py"

    with pytest.raises(ConfigError) as excinfo:
        load_strategy_definition(str(missing))

    assert "research.strategy.strategy_file" in str(excinfo.value)
    assert str(missing.resolve()) in str(excinfo.value)


def test_directory_path_is_config_error(tmp_path: Path) -> None:
    directory = tmp_path / "a_directory.py"
    directory.mkdir()

    with pytest.raises(ConfigError) as excinfo:
        load_strategy_definition(str(directory))

    assert "directory" in str(excinfo.value)


def test_wrong_extension_is_config_error() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_strategy_definition(str(_FIXTURES / "wrong_extension.txt"))

    assert ".txt" in str(excinfo.value)


def test_import_raising_is_config_error_and_chained() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_strategy_definition(str(_FIXTURES / "raises_on_import.py"))

    assert "raises_on_import.py" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, RuntimeError)


def test_missing_entry_point_is_config_error() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_strategy_definition(str(_FIXTURES / "missing_entry_point.py"))

    assert "build_strategy" in str(excinfo.value)


def test_not_callable_entry_point_is_config_error() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_strategy_definition(str(_FIXTURES / "not_callable.py"))

    assert "str" in str(excinfo.value)


def test_entry_point_requiring_arguments_is_config_error() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_strategy_definition(str(_FIXTURES / "requires_arguments.py"))

    message = str(excinfo.value)
    assert "market_model_id" in message
    assert "signal_model_id" in message


def test_entry_point_raising_when_called_is_workflow_error_and_chained() -> None:
    with pytest.raises(WorkflowError) as excinfo:
        load_strategy_definition(str(_FIXTURES / "raises_when_called.py"))

    assert "raises_when_called.py" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, RuntimeError)


def test_wrong_return_type_is_config_error() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_strategy_definition(str(_FIXTURES / "wrong_return_type.py"))

    assert "dict" in str(excinfo.value)


def test_definition_failing_validation_is_config_error_with_framework_message() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_strategy_definition(str(_FIXTURES / "fails_validation.py"))

    assert "directional entry" in str(excinfo.value)


def test_same_stem_files_load_independently_without_collision() -> None:
    loaded_a = load_strategy_definition(str(_FIXTURES / "same_stem_a" / "strategy.py"))
    loaded_b = load_strategy_definition(str(_FIXTURES / "same_stem_b" / "strategy.py"))

    assert loaded_a.definition.strategy_model_id == "fixture_same_stem_a"
    assert loaded_b.definition.strategy_model_id == "fixture_same_stem_b"
    assert loaded_a.strategy_file != loaded_b.strategy_file


def test_loading_never_mutates_sys_path() -> None:
    before = list(sys.path)

    load_strategy_definition(str(_FIXTURES / "valid_strategy.py"))

    assert sys.path == before
