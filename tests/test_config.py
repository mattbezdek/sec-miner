from __future__ import annotations

from pathlib import Path

import pytest

from sec10k_fetcher.config import load_config


def test_load_config_reads_toml(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        'identity = "Jane Doe jane@example.com"\n'
        'targets = ["0000320193"]\n'
        'combined_file = true\n',
        encoding="utf-8",
    )
    loaded = load_config(config_path=cfg)
    assert loaded.identity.startswith("Jane Doe")
    assert loaded.targets == ["0000320193"]
    assert loaded.combined_file is True
    assert loaded.filing_request.forms == ["10-K"]
    assert loaded.filing_request.latest_n == 1


def test_load_config_requires_identity() -> None:
    with pytest.raises(ValueError):
        load_config(targets=["AAPL"])


def test_load_config_form_and_filters() -> None:
    loaded = load_config(
        identity="Jane Doe jane@example.com",
        targets=["AAPL"],
        forms=["10-k", "10-q"],
        latest_n=3,
        since="2020-01-01",
        until="2024-12-31",
        years=[2021, 2022],
    )
    assert loaded.filing_request.forms == ["10-K", "10-Q"]
    assert loaded.filing_request.latest_n == 3
    assert loaded.filing_request.since == "2020-01-01"
    assert loaded.filing_request.until == "2024-12-31"
    assert loaded.filing_request.years == [2021, 2022]


def test_load_config_invalid_dates() -> None:
    with pytest.raises(ValueError):
        load_config(
            identity="Jane Doe jane@example.com",
            targets=["AAPL"],
            since="2024-01-01",
            until="2023-01-01",
        )


def test_refresh_disables_resume() -> None:
    loaded = load_config(
        identity="Jane Doe jane@example.com",
        targets=["AAPL"],
        refresh=True,
        resume=True,
    )
    assert loaded.run_options.refresh is True
    assert loaded.run_options.resume is False
