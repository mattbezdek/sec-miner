from __future__ import annotations

import re

from edgar import Company, find_company

from sec10k_fetcher.models import ResolvedTarget

CIK_PATTERN = re.compile(r"^\d{1,10}$")


def normalize_cik(value: str) -> str:
    return value.zfill(10)


def is_cik(value: str) -> bool:
    return bool(CIK_PATTERN.match(value.strip()))


def resolve_target(target: str) -> ResolvedTarget:
    cleaned = target.strip()
    if not cleaned:
        raise ValueError("Target cannot be empty.")

    if is_cik(cleaned):
        company = Company(normalize_cik(cleaned))
        return ResolvedTarget(
            raw_input=target,
            cik=normalize_cik(str(company.cik)),
            company_name=company.name,
            ticker=(company.tickers[0] if getattr(company, "tickers", None) else None),
            resolution_method="cik",
        )

    warnings: list[str] = []
    search_results = find_company(cleaned, top_n=5)
    candidates_df = getattr(search_results, "results", None)
    if candidates_df is not None and not candidates_df.empty:
        first = candidates_df.iloc[0]
        selected_cik = normalize_cik(str(int(first["cik"])))
        selected_company = str(first.get("company", "")).strip() or cleaned
        selected_ticker = str(first.get("ticker", "")).strip() or None
        if len(candidates_df) > 1:
            warnings.append(
                f"Input '{cleaned}' matched multiple companies. Auto-selected best match "
                f"'{selected_company}' ({selected_cik})."
            )
        return ResolvedTarget(
            raw_input=target,
            cik=selected_cik,
            company_name=selected_company,
            ticker=selected_ticker,
            resolution_method="search",
            warnings=warnings,
        )

    # Final fallback attempts direct lookup as ticker or exact company id.
    company = Company(cleaned)
    return ResolvedTarget(
        raw_input=target,
        cik=normalize_cik(str(company.cik)),
        company_name=company.name,
        ticker=(company.tickers[0] if getattr(company, "tickers", None) else None),
        resolution_method="direct",
    )
