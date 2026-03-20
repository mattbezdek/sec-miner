from __future__ import annotations

from pathlib import Path

import typer

from sec10k_fetcher.config import load_config
from sec10k_fetcher.pipeline import run_pipeline, write_default_config
from sec10k_fetcher.resolver import resolve_target

app = typer.Typer(help="SEC-miner: fetch SEC filings and export markdown/chunks.")


def _load_targets(target: list[str], targets_file: Path | None) -> list[str]:
    merged = list(target)
    if targets_file and targets_file.exists():
        lines = targets_file.read_text(encoding="utf-8").splitlines()
        merged.extend([line.strip() for line in lines if line.strip()])
    return merged


@app.command()
def run(
    identity: str = typer.Option("", help="SEC identity: 'Name email@example.com'."),
    api_token: str = typer.Option("", help="Optional API token for EDGAR Next environments."),
    target: list[str] = typer.Option(
        None,
        "--target",
        "-t",
        help="CIK, ticker, or company name. Repeat for multiple targets.",
    ),
    targets_file: Path | None = typer.Option(
        None, help="Optional file with one target (CIK/name/ticker) per line."
    ),
    output_dir: Path = typer.Option(Path("output"), help="Output directory."),
    include_manifest: bool = typer.Option(False, help="Include JSON metadata manifest."),
    combined_file: bool = typer.Option(True, help="Write a combined markdown file."),
    rate_limit_rps: float = typer.Option(
        2.0, help="Practical request rate limit (requests per second)."
    ),
    form: list[str] = typer.Option(
        None,
        "--form",
        help="SEC form to fetch (repeatable). Defaults to 10-K.",
    ),
    latest_n: int = typer.Option(1, help="Number of most-recent filings per target/form."),
    since: str = typer.Option("", help="Only include filings on/after this ISO date (YYYY-MM-DD)."),
    until: str = typer.Option("", help="Only include filings on/before this ISO date (YYYY-MM-DD)."),
    year: list[int] = typer.Option(
        None,
        "--year",
        help="Only include filings whose filing date is in this year (repeatable).",
    ),
    section: list[str] = typer.Option(
        None,
        "--section",
        help="Section selector (repeatable): business, risk_factors, mda, financials.",
    ),
    resume: bool = typer.Option(
        True, "--resume/--no-resume", help="Reuse local cache to skip previously downloaded filings."
    ),
    refresh: bool = typer.Option(False, help="Bypass cache and re-fetch filings."),
    cache_dir: Path = typer.Option(Path(".sec_miner_cache"), help="Cache directory."),
    max_workers: int = typer.Option(1, help="Number of targets to process concurrently."),
    output_mode: str = typer.Option(
        "markdown_full",
        help="Output mode: markdown_full, markdown_sections, jsonl_chunks.",
    ),
    chunk_size: int = typer.Option(1400, help="Chunk size for jsonl_chunks output mode."),
    chunk_overlap: int = typer.Option(200, help="Chunk overlap for jsonl_chunks output mode."),
    report_format: str = typer.Option("none", help="Run report format: none, markdown, html."),
    report_file: str = typer.Option("", help="Optional run report filename."),
    config: Path | None = typer.Option(None, help="Path to config.toml."),
) -> None:
    targets = _load_targets(target or [], targets_file)
    app_config = load_config(
        config_path=config,
        identity=identity or None,
        api_token=api_token or None,
        targets=targets,
        output_dir=str(output_dir),
        combined_file=combined_file,
        include_manifest=include_manifest,
        rate_limit_rps=rate_limit_rps,
        forms=form or None,
        latest_n=latest_n,
        since=since or None,
        until=until or None,
        years=year or None,
        sections=section or None,
        resume=resume,
        refresh=refresh,
        cache_dir=str(cache_dir),
        max_workers=max_workers,
        output_mode=output_mode,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        report_format=report_format,
        report_file=report_file or None,
    )
    summary = run_pipeline(app_config, logger=typer.echo)
    if summary.failure_count:
        raise typer.Exit(code=1)


@app.command()
def init_config(path: Path = typer.Option(Path("config.toml"), help="Path to create config file.")) -> None:
    write_default_config(path)
    typer.echo(f"Wrote default config file: {path}")


@app.command()
def resolve(
    target: list[str] = typer.Option(
        None,
        "--target",
        "-t",
        help="CIK, ticker, or company name. Repeat for multiple targets.",
    ),
    targets_file: Path | None = typer.Option(
        None, help="Optional file with one target (CIK/name/ticker) per line."
    ),
) -> None:
    targets = _load_targets(target or [], targets_file)
    if not targets:
        raise typer.BadParameter("Provide at least one --target or --targets-file.")
    for item in targets:
        resolved = resolve_target(item)
        typer.echo(f"Input: {item}")
        typer.echo(f"  Company: {resolved.company_name}")
        typer.echo(f"  CIK: {resolved.cik}")
        typer.echo(f"  Ticker: {resolved.ticker or ''}")
        typer.echo(f"  Method: {resolved.resolution_method}")
        for warning in resolved.warnings:
            typer.echo(f"  Warning: {warning}")
