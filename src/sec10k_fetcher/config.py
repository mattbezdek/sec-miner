from __future__ import annotations

import os
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

from sec10k_fetcher.models import AppConfig, FilingRequest, RunOptions


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
    forms: list[str] | None = None,
    latest_n: int | None = None,
    since: str | None = None,
    until: str | None = None,
    years: list[int] | None = None,
    sections: list[str] | None = None,
    resume: bool | None = None,
    refresh: bool | None = None,
    cache_dir: str | None = None,
    max_workers: int | None = None,
    output_mode: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    report_format: str | None = None,
    report_file: str | None = None,
) -> AppConfig:
    file_cfg = _load_toml_file(config_path)
    env_identity = os.getenv("SEC_IDENTITY", "")
    env_token = os.getenv("SEC_API_TOKEN", "")

    file_forms = file_cfg.get("forms") or file_cfg.get("form") or ["10-K"]
    normalized_forms = [str(item).strip().upper() for item in (forms or list(file_forms)) if str(item).strip()]
    if not normalized_forms:
        normalized_forms = ["10-K"]

    resolved_since = since if since is not None else file_cfg.get("since")
    resolved_until = until if until is not None else file_cfg.get("until")
    resolved_years = years if years is not None else list(file_cfg.get("years", []))
    resolved_latest_n = latest_n if latest_n is not None else int(file_cfg.get("latest_n", 1))
    resolved_sections = [str(item).strip().lower() for item in (sections or file_cfg.get("sections", []))]

    resolved_resume = resume if resume is not None else bool(file_cfg.get("resume", True))
    resolved_refresh = refresh if refresh is not None else bool(file_cfg.get("refresh", False))
    resolved_cache_dir = cache_dir or file_cfg.get("cache_dir", ".sec_miner_cache")
    resolved_max_workers = max_workers if max_workers is not None else int(file_cfg.get("max_workers", 1))
    resolved_output_mode = (
        output_mode if output_mode is not None else str(file_cfg.get("output_mode", "markdown_full"))
    ).strip().lower()
    resolved_chunk_size = chunk_size if chunk_size is not None else int(file_cfg.get("chunk_size", 1400))
    resolved_chunk_overlap = (
        chunk_overlap if chunk_overlap is not None else int(file_cfg.get("chunk_overlap", 200))
    )
    resolved_report_format = (
        report_format if report_format is not None else str(file_cfg.get("report_format", "none"))
    ).strip().lower()
    resolved_report_file = report_file if report_file is not None else file_cfg.get("report_file")

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
        filing_request=FilingRequest(
            forms=normalized_forms,
            latest_n=resolved_latest_n,
            since=resolved_since,
            until=resolved_until,
            years=[int(year) for year in resolved_years],
            sections=resolved_sections,
        ),
        run_options=RunOptions(
            resume=resolved_resume,
            refresh=resolved_refresh,
            cache_dir=Path(resolved_cache_dir),
            max_workers=resolved_max_workers,
            output_mode=resolved_output_mode,
            chunk_size=resolved_chunk_size,
            chunk_overlap=resolved_chunk_overlap,
            report_format=resolved_report_format,
            report_file=str(resolved_report_file) if resolved_report_file else None,
        ),
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
    if config.filing_request.latest_n < 1:
        raise ValueError("latest_n must be at least 1.")
    for form in config.filing_request.forms:
        if not form:
            raise ValueError("forms entries cannot be empty.")
    if config.filing_request.since:
        date.fromisoformat(config.filing_request.since)
    if config.filing_request.until:
        date.fromisoformat(config.filing_request.until)
    if config.filing_request.since and config.filing_request.until:
        if date.fromisoformat(config.filing_request.since) > date.fromisoformat(config.filing_request.until):
            raise ValueError("since cannot be after until.")
    for year in config.filing_request.years:
        if year < 1900 or year > 3000:
            raise ValueError(f"Invalid year in years: {year}")
    if config.run_options.refresh:
        # Refresh mode always bypasses cache reads.
        config.run_options.resume = False
    if config.run_options.max_workers < 1:
        raise ValueError("max_workers must be at least 1.")
    supported_modes = {"markdown_full", "markdown_sections", "jsonl_chunks"}
    if config.run_options.output_mode not in supported_modes:
        raise ValueError(f"output_mode must be one of {sorted(supported_modes)}.")
    if config.run_options.chunk_size < 200:
        raise ValueError("chunk_size must be at least 200.")
    if config.run_options.chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative.")
    if config.run_options.chunk_overlap >= config.run_options.chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")
    supported_report_formats = {"none", "markdown", "html"}
    if config.run_options.report_format not in supported_report_formats:
        raise ValueError(f"report_format must be one of {sorted(supported_report_formats)}.")

    return config
