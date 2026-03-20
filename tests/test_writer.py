from __future__ import annotations

from pathlib import Path

from sec10k_fetcher.fetcher import FetchedFiling
from sec10k_fetcher.writer import write_markdown_output


def test_write_markdown_output_creates_file(tmp_path: Path) -> None:
    filing = FetchedFiling(
        target="AAPL",
        resolved_cik="0000320193",
        company_name="Apple Inc.",
        ticker="AAPL",
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
