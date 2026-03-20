from __future__ import annotations

from pathlib import Path

from sec10k_fetcher.fetcher import FilingCandidate, FetchedFiling
from sec10k_fetcher.models import AppConfig, FilingRequest, RunOptions
from sec10k_fetcher.pipeline import run_pipeline


class DummyFilingRef:
    def html(self) -> str:
        return "<html></html>"


def _build_candidate() -> FilingCandidate:
    return FilingCandidate(
        target="AAPL",
        resolved_cik="0000320193",
        company_name="Apple Inc.",
        ticker="AAPL",
        form="10-K",
        accession_no="0000320193-25-000079",
        filing_date="2025-10-31",
        source_url="https://example.com",
        filing_ref=DummyFilingRef(),
    )


def _build_fetched() -> FetchedFiling:
    return FetchedFiling(
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


def test_pipeline_skips_cached_filing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sec10k_fetcher.pipeline.configure_identity", lambda *_: None)
    monkeypatch.setattr(
        "sec10k_fetcher.pipeline.fetch_filing_candidates",
        lambda **_: [_build_candidate()],
    )
    monkeypatch.setattr(
        "sec10k_fetcher.pipeline.materialize_filing",
        lambda *_args, **_kwargs: _build_fetched(),
    )
    monkeypatch.setattr("sec10k_fetcher.pipeline.convert_to_full_markdown", lambda _html: "md")
    monkeypatch.setattr("sec10k_fetcher.pipeline.write_markdown_output", lambda **_: tmp_path / "out.md")
    monkeypatch.setattr("sec10k_fetcher.pipeline.write_combined_markdown", lambda *_args, **_kwargs: tmp_path / "combined.md")
    monkeypatch.setattr("sec10k_fetcher.pipeline.write_manifest", lambda *_args, **_kwargs: tmp_path / "manifest.json")

    config = AppConfig(
        identity="Jane Doe jane@example.com",
        targets=["AAPL"],
        output_dir=tmp_path,
        include_manifest=False,
        combined_file=False,
        filing_request=FilingRequest(forms=["10-K"], latest_n=1),
        run_options=RunOptions(resume=True, refresh=False, cache_dir=tmp_path / "cache"),
    )
    first = run_pipeline(config)
    assert first.success_count == 1
    second = run_pipeline(config)
    assert second.skipped_count == 1
    assert any(result.status == "skipped_cached" for result in second.results)
