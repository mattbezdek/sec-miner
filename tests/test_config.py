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


def test_load_config_requires_identity() -> None:
    with pytest.raises(ValueError):
        load_config(targets=["AAPL"])
