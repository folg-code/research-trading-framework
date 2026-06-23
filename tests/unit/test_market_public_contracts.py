"""Public market domain contract export tests."""

import trading_framework.market.datasets as datasets
import trading_framework.market.importers as importers
import trading_framework.market.normalization as normalization
import trading_framework.market.repositories as repositories
import trading_framework.market.validation as validation


def test_market_importers_exports_contract_types() -> None:
    assert hasattr(importers, "FileInspector")
    assert hasattr(importers, "FileInspectionResult")
    assert hasattr(importers, "DetectedFileFormat")


def test_market_normalization_exports_contract_types() -> None:
    assert hasattr(normalization, "OhlcvNormalizer")
    assert hasattr(normalization, "OhlcvImportConfig")
    assert hasattr(normalization, "NormalizedBarRow")


def test_market_validation_exports_contract_types() -> None:
    assert hasattr(validation, "OhlcvValidator")
    assert hasattr(validation, "ValidationResult")
    assert hasattr(validation, "ValidationIssue")


def test_market_repositories_exports_contract_types() -> None:
    assert hasattr(repositories, "DatasetRepository")
    assert hasattr(repositories, "HistoricalBarQuery")


def test_market_datasets_exports_identity_and_lifecycle_types() -> None:
    assert hasattr(datasets, "DatasetId")
    assert hasattr(datasets, "DatasetRef")
    assert hasattr(datasets, "DatasetMetadata")
    assert hasattr(datasets, "DatasetLifecycleState")
    assert hasattr(datasets, "transition_dataset_lifecycle")
