from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from sec10k_fetcher.converter import convert_to_full_markdown
from sec10k_fetcher.fetcher import configure_identity, fetch_latest_10k
from sec10k_fetcher.models import AppConfig, FilingOutput, RunSummary
from sec10k_fetcher.rate_limit import RateLimiter
from sec10k_fetcher.writer import (
    render_company_markdown,
    write_combined_markdown,
    write_manifest,
    write_markdown_output,
)

Logger = Callable[[str], None]


def run_pipeline(config: AppConfig, logger: Logger | None = None) -> RunSummary:
    log = logger or (lambda _: None)

    configure_identity(config.identity, config.api_token or None)
    limiter = RateLimiter(config.rate_limit_rps)
    summary = RunSummary(started_at=datetime.utcnow())
    combined_documents: list[str] = []

    for target in config.targets:
        log(f"Processing: {target}")
        try:
            filing = fetch_latest_10k(target, limiter=limiter)
            full_markdown = convert_to_full_markdown(filing.html_content)
            if config.combined_file:
                company_markdown = render_company_markdown(filing, full_markdown)
                combined_documents.append(company_markdown)
                output_path = None
            else:
                output_path = write_markdown_output(
                    output_dir=config.output_dir,
                    filing=filing,
                    full_markdown=full_markdown,
                )

            summary.results.append(
                FilingOutput(
                    raw_input=target,
                    cik=filing.resolved_cik,
                    company_name=filing.company_name,
                    ticker=filing.ticker,
                    filing_date=filing.filing_date,
                    accession_no=filing.accession_no,
                    source_url=filing.source_url,
                    output_file=str(output_path) if output_path else None,
                    success=True,
                    warning=filing.warning,
                )
            )
            if output_path:
                log(f"Saved: {output_path}")
            else:
                log(f"Prepared for combined output: {filing.company_name}")
        except Exception as exc:  # noqa: BLE001
            summary.results.append(
                FilingOutput(
                    raw_input=target,
                    cik=None,
                    company_name=None,
                    ticker=None,
                    filing_date=None,
                    accession_no=None,
                    source_url=None,
                    output_file=None,
                    success=False,
                    error=str(exc),
                )
            )
            log(f"Failed: {target} -> {exc}")

    summary.finished_at = datetime.utcnow()

    if config.combined_file:
        combined_path = write_combined_markdown(config.output_dir, summary, documents=combined_documents)
        log(f"Combined file saved: {combined_path}")
    if config.include_manifest:
        manifest_path = write_manifest(config.output_dir, summary)
        log(f"Manifest saved: {manifest_path}")

    log(
        "Completed run: "
        f"{summary.success_count} succeeded, {summary.failure_count} failed, total {summary.total}."
    )
    return summary


def write_default_config(path: Path) -> None:
    content = """identity = "Your Name your.email@example.com"
api_token = ""
targets = ["0000320193", "amazon", "TSLA"]
output_dir = "output"
combined_file = true
include_manifest = false
rate_limit_rps = 2.0
"""
    path.write_text(content, encoding="utf-8")
