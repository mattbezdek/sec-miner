from __future__ import annotations

from pathlib import Path

import typer

from sec10k_fetcher.config import load_config
from sec10k_fetcher.pipeline import run_pipeline, write_default_config

app = typer.Typer(help="SEC-miner: fetch 10-K filings and export markdown.")


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
    )
    summary = run_pipeline(app_config, logger=typer.echo)
    if summary.failure_count:
        raise typer.Exit(code=1)


@app.command()
def init_config(path: Path = typer.Option(Path("config.toml"), help="Path to create config file.")) -> None:
    write_default_config(path)
    typer.echo(f"Wrote default config file: {path}")
