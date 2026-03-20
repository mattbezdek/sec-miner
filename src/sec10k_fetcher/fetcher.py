from __future__ import annotations

import os
import time
from dataclasses import dataclass

from edgar import Company, set_identity

from sec10k_fetcher.rate_limit import RateLimiter
from sec10k_fetcher.resolver import resolve_target


@dataclass
class FetchedFiling:
    target: str
    resolved_cik: str
    company_name: str
    ticker: str | None
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


def fetch_latest_10k(
    target: str,
    limiter: RateLimiter,
    retries: int = 3,
) -> FetchedFiling:
    resolved = resolve_target(target)
    warning = "; ".join(resolved.warnings) if resolved.warnings else None

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            limiter.wait()
            company = Company(resolved.cik)
            filings = company.get_filings(form="10-K")
            filing = filings.latest()
            if filing is None:
                raise RuntimeError(f"No 10-K filings available for {resolved.company_name}.")

            html_content = filing.html()
            filing_date = str(getattr(filing, "filing_date", ""))
            accession_no = str(getattr(filing, "accession_no", ""))
            source_url = str(getattr(filing, "url", "")) or str(getattr(filing, "homepage_url", ""))

            return FetchedFiling(
                target=target,
                resolved_cik=resolved.cik,
                company_name=resolved.company_name,
                ticker=resolved.ticker,
                accession_no=accession_no,
                filing_date=filing_date,
                source_url=source_url,
                html_content=html_content,
                warning=warning,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries:
                backoff_seconds = attempt * 1.5
                time.sleep(backoff_seconds)
            else:
                break

    assert last_error is not None
    raise RuntimeError(f"Failed to fetch latest 10-K for '{target}': {last_error}") from last_error
