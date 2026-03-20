from __future__ import annotations


def classify_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "rate" in text or "timeout" in text or "temporar" in text:
        return "transient_fetch_error"
    if "no " in text and "filing" in text:
        return "no_matching_filings"
    if "identity" in text:
        return "configuration_error"
    return "pipeline_error"
