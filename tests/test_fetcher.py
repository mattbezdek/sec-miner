from __future__ import annotations

from dataclasses import dataclass

from sec10k_fetcher.fetcher import _filter_and_sort_filings
from sec10k_fetcher.models import FilingRequest


@dataclass
class DummyFiling:
    filing_date: str
    accession_no: str


def test_filter_and_sort_filings_applies_date_filters_and_latest_n() -> None:
    filings = [
        DummyFiling(filing_date="2022-02-01", accession_no="a"),
        DummyFiling(filing_date="2024-01-01", accession_no="c"),
        DummyFiling(filing_date="2023-06-15", accession_no="b"),
    ]
    request = FilingRequest(
        forms=["10-K"],
        latest_n=2,
        since="2023-01-01",
        until="2024-12-31",
        years=[],
    )
    selected = _filter_and_sort_filings(filings, request)
    assert [item.accession_no for item in selected] == ["c", "b"]


def test_filter_and_sort_filings_applies_year_filter() -> None:
    filings = [
        DummyFiling(filing_date="2021-12-31", accession_no="a"),
        DummyFiling(filing_date="2022-12-31", accession_no="b"),
        DummyFiling(filing_date="2023-12-31", accession_no="c"),
    ]
    request = FilingRequest(forms=["10-K"], latest_n=3, years=[2022])
    selected = _filter_and_sort_filings(filings, request)
    assert [item.accession_no for item in selected] == ["b"]
