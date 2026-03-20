from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from sec10k_fetcher.fetcher import FetchedFiling
from sec10k_fetcher.models import RunSummary
from sec10k_fetcher.processing import Chunk


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


def write_sections_markdown_output(
    output_dir: Path,
    filing: FetchedFiling,
    sections: dict[str, str],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _next_available_path(output_dir / f"{_filename_base(filing)}_sections.md")
    parts = [render_company_markdown(filing, "")]
    for section, content in sections.items():
        parts.append(f"\n## Section: {section}\n\n{content}\n")
    output_path.write_text("".join(parts), encoding="utf-8")
    return output_path


def write_chunks_jsonl_output(
    output_dir: Path,
    filing: FetchedFiling,
    chunks: list[Chunk],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _next_available_path(output_dir / f"{_filename_base(filing)}_chunks.jsonl")
    lines = []
    for chunk in chunks:
        payload = {
            "company_name": filing.company_name,
            "cik": filing.resolved_cik,
            "ticker": filing.ticker,
            "form": filing.form,
            "accession_no": filing.accession_no,
            "filing_date": filing.filing_date,
            "source_url": filing.source_url,
            "section": chunk.section,
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
        }
        lines.append(json.dumps(payload, ensure_ascii=False))
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output_path


def render_company_markdown(filing: FetchedFiling, full_markdown: str) -> str:
    return (
        f"# {filing.company_name} {filing.form}\n\n"
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
    combined_path = _next_available_path(output_dir / f"combined_filing_output_{timestamp}.md")
    parts = ["# Combined Filing Output\n"]
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
            "sections": summary.filing_request.sections if summary.filing_request else [],
        },
        "run_options": {
            "max_workers": summary.run_options.max_workers if summary.run_options else 1,
            "output_mode": summary.run_options.output_mode if summary.run_options else "markdown_full",
            "chunk_size": summary.run_options.chunk_size if summary.run_options else 1400,
            "chunk_overlap": summary.run_options.chunk_overlap if summary.run_options else 200,
            "report_format": summary.run_options.report_format if summary.run_options else "none",
            "cancelled": summary.cancelled,
        },
        "results": [result.to_manifest_dict() for result in summary.results],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def write_run_report(
    output_dir: Path,
    summary: RunSummary,
    report_format: str,
    report_file: str | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ext = "md" if report_format == "markdown" else "html"
    if report_file:
        preferred = output_dir / report_file
        if preferred.suffix != f".{ext}":
            preferred = preferred.with_suffix(f".{ext}")
        report_path = _next_available_path(preferred)
    else:
        report_path = _next_available_path(output_dir / f"run_report_{timestamp}.{ext}")
    if report_format == "markdown":
        content = [
            "# SEC-miner Run Report\n\n",
            f"- Started: {summary.started_at.isoformat()}\n",
            f"- Finished: {summary.finished_at.isoformat() if summary.finished_at else ''}\n",
            f"- Total: {summary.total}\n",
            f"- Success: {summary.success_count}\n",
            f"- Skipped: {summary.skipped_count}\n",
            f"- Failed: {summary.failure_count}\n\n",
            "## Results\n\n",
        ]
        for result in summary.results:
            content.append(
                "- "
                f"[{result.status}] {result.raw_input} "
                f"{result.form or ''} {result.accession_no or ''} "
                f"{'-> ' + result.output_file if result.output_file else ''}\n"
            )
        report_path.write_text("".join(content), encoding="utf-8")
    else:
        rows = []
        for result in summary.results:
            rows.append(
                "<tr>"
                f"<td>{result.status}</td>"
                f"<td>{result.raw_input}</td>"
                f"<td>{result.form or ''}</td>"
                f"<td>{result.accession_no or ''}</td>"
                f"<td>{result.output_file or ''}</td>"
                f"<td>{result.error or ''}</td>"
                "</tr>"
            )
        html = (
            "<html><head><meta charset='utf-8'><title>SEC-miner Run Report</title></head><body>"
            "<h1>SEC-miner Run Report</h1>"
            f"<p>Total: {summary.total} | Success: {summary.success_count} | "
            f"Skipped: {summary.skipped_count} | Failed: {summary.failure_count}</p>"
            "<table border='1' cellspacing='0' cellpadding='4'>"
            "<thead><tr><th>Status</th><th>Target</th><th>Form</th><th>Accession</th>"
            "<th>Output</th><th>Error</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></body></html>"
        )
        report_path.write_text(html, encoding="utf-8")
    return report_path
