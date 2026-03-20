from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from sec10k_fetcher.models import AppConfig


def _load_toml_file(config_path: Path | None) -> dict[str, Any]:
    if not config_path:
        return {}
    if not config_path.exists():
        return {}
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def load_config(
    config_path: Path | None = None,
    identity: str | None = None,
    api_token: str | None = None,
    targets: list[str] | None = None,
    output_dir: str | None = None,
    combined_file: bool | None = None,
    include_manifest: bool | None = None,
    rate_limit_rps: float | None = None,
) -> AppConfig:
    file_cfg = _load_toml_file(config_path)
    env_identity = os.getenv("SEC_IDENTITY", "")
    env_token = os.getenv("SEC_API_TOKEN", "")

    config = AppConfig(
        identity=identity or file_cfg.get("identity") or env_identity,
        api_token=api_token or file_cfg.get("api_token") or env_token,
        targets=targets or list(file_cfg.get("targets", [])),
        output_dir=Path(output_dir or file_cfg.get("output_dir", "output")),
        combined_file=(
            combined_file if combined_file is not None else bool(file_cfg.get("combined_file", True))
        ),
        include_manifest=(
            include_manifest
            if include_manifest is not None
            else bool(file_cfg.get("include_manifest", False))
        ),
        rate_limit_rps=float(rate_limit_rps or file_cfg.get("rate_limit_rps", 2.0)),
    )

    if not config.identity:
        raise ValueError(
            "SEC identity is required. Provide --identity, config.toml identity, "
            "or SEC_IDENTITY environment variable."
        )
    if not config.targets:
        raise ValueError("At least one target is required (CIK, ticker, or company name).")
    if config.rate_limit_rps <= 0:
        raise ValueError("rate_limit_rps must be greater than 0.")

    return config
