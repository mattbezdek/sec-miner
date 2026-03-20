from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from sec10k_fetcher.fetcher import FetchedFiling
from sec10k_fetcher.models import RunSummary


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())
    return slug.strip("_").lower() or "company"


def _filename_base(filing: FetchedFiling) -> str:
    label = filing.ticker or filing.company_name or filing.resolved_cik
    date = filing.filing_date or datetime.utcnow().strftime("%Y-%m-%d")
    accession = _safe_slug(filing.accession_no or "latest")
    form = _safe_slug(filing.form or "filing")
    return f"{_safe_slug(label)}_{date}_{accession}_{form}"


def _next_available_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2
    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def write_markdown_output(
    output_dir: Path,
    filing: FetchedFiling,
    full_markdown: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _next_available_path(output_dir / f"{_filename_base(filing)}.md")
    markdown = render_company_markdown(filing, full_markdown)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def render_company_markdown(filing: FetchedFiling, full_markdown: str) -> str:
    return (
        f"# {filing.company_name} 10-K\n\n"
        f"- CIK: {filing.resolved_cik}\n"
        f"- Form: {filing.form}\n"
        f"- Filing date: {filing.filing_date}\n"
        f"- Accession: {filing.accession_no}\n"
        f"- Source: {filing.source_url}\n\n"
        f"{full_markdown}\n"
    )


def write_combined_markdown(
    output_dir: Path,
    summary: RunSummary,
    documents: list[str] | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    combined_path = _next_available_path(output_dir / f"combined_10k_output_{timestamp}.md")
    parts = ["# Combined 10-K Output\n"]
    if documents is not None:
        for content in documents:
            parts.append(f"\n---\n\n{content}\n")
    else:
        for result in summary.results:
            if not result.success or not result.output_file:
                continue
            content = Path(result.output_file).read_text(encoding="utf-8")
            parts.append(f"\n---\n\n{content}\n")
    combined_path.write_text("".join(parts), encoding="utf-8")
    return combined_path


def write_manifest(output_dir: Path, summary: RunSummary) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    manifest_path = _next_available_path(output_dir / f"manifest_{timestamp}.json")
    payload = {
        "started_at": summary.started_at.isoformat(),
        "finished_at": summary.finished_at.isoformat() if summary.finished_at else None,
        "total": summary.total,
        "success_count": summary.success_count,
        "failure_count": summary.failure_count,
        "skipped_count": summary.skipped_count,
        "filing_request": {
            "forms": summary.filing_request.forms if summary.filing_request else [],
            "latest_n": summary.filing_request.latest_n if summary.filing_request else 1,
            "since": summary.filing_request.since if summary.filing_request else None,
            "until": summary.filing_request.until if summary.filing_request else None,
            "years": summary.filing_request.years if summary.filing_request else [],
        },
        "results": [result.to_manifest_dict() for result in summary.results],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path
