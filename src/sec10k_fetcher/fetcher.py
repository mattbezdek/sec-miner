from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, TypeVar

from edgar import Company, set_identity

from sec10k_fetcher.models import FilingRequest
from sec10k_fetcher.rate_limit import RateLimiter
from sec10k_fetcher.resolver import resolve_target


@dataclass
class FilingCandidate:
    target: str
    resolved_cik: str
    company_name: str
    ticker: str | None
    form: str
    accession_no: str
    filing_date: str
    source_url: str
    filing_ref: Any
    warning: str | None = None


@dataclass
class FetchedFiling:
    target: str
    resolved_cik: str
    company_name: str
    ticker: str | None
    form: str
    accession_no: str
    filing_date: str
    source_url: str
    html_content: str
    warning: str | None = None


def configure_identity(identity: str, api_token: str | None = None) -> None:
    set_identity(identity)
    if api_token:
        # Optional token support for environments that consume this variable.
        os.environ["SEC_API_TOKEN"] = api_token


def _parse_filing_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value if not isinstance(value, datetime) else value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _iter_filings(filings: Any) -> list[Any]:
    try:
        return list(filings)
    except TypeError as exc:
        raise RuntimeError("Unable to iterate filings collection from edgartools.") from exc


def _filter_and_sort_filings(filings: list[Any], request: FilingRequest) -> list[Any]:
    since_date = date.fromisoformat(request.since) if request.since else None
    until_date = date.fromisoformat(request.until) if request.until else None
    years = set(request.years)

    selected: list[tuple[date | None, str, Any]] = []
    for filing in filings:
        filing_date = _parse_filing_date(getattr(filing, "filing_date", None))
        if since_date and (filing_date is None or filing_date < since_date):
            continue
        if until_date and (filing_date is None or filing_date > until_date):
            continue
        if years and (filing_date is None or filing_date.year not in years):
            continue
        accession = str(getattr(filing, "accession_no", "")) or ""
        selected.append((filing_date, accession, filing))

    selected.sort(
        key=lambda entry: (
            entry[0] if entry[0] is not None else date.min,
            entry[1],
        ),
        reverse=True,
    )
    return [item[2] for item in selected[: request.latest_n]]


T = TypeVar("T")


def _with_retries(operation: str, retries: int, action: Callable[[], T]) -> T:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return action()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries:
                backoff_seconds = attempt * 1.5
                time.sleep(backoff_seconds)
            else:
                break
    assert last_error is not None
    raise RuntimeError(f"{operation}: {last_error}") from last_error


def fetch_filing_candidates(
    target: str,
    limiter: RateLimiter,
    request: FilingRequest,
    retries: int = 3,
) -> list[FilingCandidate]:
    resolved = resolve_target(target)
    warning = "; ".join(resolved.warnings) if resolved.warnings else None
    company = _with_retries(
        operation=f"Failed to resolve company for '{target}'",
        retries=retries,
        action=lambda: Company(resolved.cik),
    )
    candidates: list[FilingCandidate] = []

    for form in request.forms:
        def load_form_filings() -> list[Any]:
            limiter.wait()
            filings = company.get_filings(form=form)
            return _iter_filings(filings)

        all_filings = _with_retries(
            operation=f"Failed to load {form} filings for '{target}'",
            retries=retries,
            action=load_form_filings,
        )
        chosen = _filter_and_sort_filings(all_filings, request)
        for filing in chosen:
            filing_date = str(getattr(filing, "filing_date", ""))
            accession_no = str(getattr(filing, "accession_no", ""))
            source_url = str(getattr(filing, "url", "")) or str(getattr(filing, "homepage_url", ""))
            candidates.append(
                FilingCandidate(
                    target=target,
                    resolved_cik=resolved.cik,
                    company_name=resolved.company_name,
                    ticker=resolved.ticker,
                    form=form,
                    accession_no=accession_no,
                    filing_date=filing_date,
                    source_url=source_url,
                    filing_ref=filing,
                    warning=warning,
                )
            )

    if not candidates:
        forms = ", ".join(request.forms)
        raise RuntimeError(f"No {forms} filings matched selection criteria for {resolved.company_name}.")
    return candidates


def materialize_filing(
    candidate: FilingCandidate,
    limiter: RateLimiter,
    retries: int = 3,
) -> FetchedFiling:
    def load_html() -> str:
        limiter.wait()
        return str(candidate.filing_ref.html())

    html_content = _with_retries(
        operation=(
            f"Failed to fetch filing HTML for '{candidate.target}'"
            f" ({candidate.form} {candidate.accession_no})"
        ),
        retries=retries,
        action=load_html,
    )
    return FetchedFiling(
        target=candidate.target,
        resolved_cik=candidate.resolved_cik,
        company_name=candidate.company_name,
        ticker=candidate.ticker,
        form=candidate.form,
        accession_no=candidate.accession_no,
        filing_date=candidate.filing_date,
        source_url=candidate.source_url,
        html_content=html_content,
        warning=candidate.warning,
    )
