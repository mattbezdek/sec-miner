from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sec10k_fetcher.fetcher import FetchedFiling
from sec10k_fetcher.models import RunSummary
from sec10k_fetcher.writer import write_markdown_output, write_run_report


def test_write_markdown_output_creates_file(tmp_path: Path) -> None:
    filing = FetchedFiling(
        target="AAPL",
        resolved_cik="0000320193",
        company_name="Apple Inc.",
        ticker="AAPL",
        form="10-K",
        accession_no="0000320193-25-000079",
        filing_date="2025-10-31",
        source_url="https://example.com",
        html_content="<html></html>",
    )
    output = write_markdown_output(
        output_dir=tmp_path,
        filing=filing,
        full_markdown="# Full 10-K content\nBusiness text",
    )
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "Full 10-K content" in text
    assert "Business text" in text


def test_write_run_report_markdown(tmp_path: Path) -> None:
    summary = RunSummary(started_at=datetime.utcnow())
    report = write_run_report(tmp_path, summary, "markdown", report_file="run_report")
    assert report.exists()
    assert report.suffix == ".md"
