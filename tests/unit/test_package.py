def test_package_can_be_imported() -> None:
    import trading_framework

    assert trading_framework.__version__ == "0.1.0"
