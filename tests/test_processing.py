from __future__ import annotations

from sec10k_fetcher.processing import chunk_text, extract_sections, normalize_sections


def test_extract_sections_from_markdown() -> None:
    markdown = """# Annual Report
## Item 1. Business
Business content
## Item 1A. Risk Factors
Risk content
## Item 7. Management's Discussion and Analysis
MDA content
"""
    extracted = extract_sections(markdown, ["business", "risk_factors"])
    assert "business" in extracted
    assert "risk_factors" in extracted
    assert "Business content" in extracted["business"]


def test_chunk_text_stable_ids() -> None:
    text = "a" * 2600
    chunks = chunk_text("risk_factors", text, chunk_size=1000, chunk_overlap=100)
    assert len(chunks) >= 2
    assert chunks[0].chunk_id == "risk_factors_0001"
    assert chunks[1].chunk_id == "risk_factors_0002"


def test_normalize_sections_deduplicates_aliases() -> None:
    normalized = normalize_sections(["Risk Factors", "item 1a", "mda"])
    assert normalized == ["risk_factors", "mda"]
