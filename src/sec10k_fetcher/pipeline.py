from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable

from sec10k_fetcher.cache import RunCache
from sec10k_fetcher.converter import convert_to_full_markdown
from sec10k_fetcher.errors import classify_error
from sec10k_fetcher.fetcher import configure_identity, fetch_filing_candidates, materialize_filing
from sec10k_fetcher.models import AppConfig, FilingOutput, RunSummary
from sec10k_fetcher.processing import chunk_text, extract_sections, normalize_sections
from sec10k_fetcher.rate_limit import RateLimiter
from sec10k_fetcher.writer import (
    render_company_markdown,
    write_combined_markdown,
    write_chunks_jsonl_output,
    write_manifest,
    write_markdown_output,
    write_run_report,
    write_sections_markdown_output,
)

Logger = Callable[[str], None]


def _process_single_target(
    target: str,
    config: AppConfig,
    limiter: RateLimiter,
    cache: RunCache,
    cache_lock: threading.Lock,
    cancel_event: threading.Event,
    log: Logger,
) -> tuple[list[FilingOutput], list[str]]:
    results: list[FilingOutput] = []
    combined_documents: list[str] = []
    try:
        if cancel_event.is_set():
            return results, combined_documents

        log(f"Processing: {target}")
        candidates = fetch_filing_candidates(target=target, limiter=limiter, request=config.filing_request)
        wanted_sections = normalize_sections(config.filing_request.sections)

        for candidate in candidates:
            if cancel_event.is_set():
                break
            with cache_lock:
                cached = config.run_options.resume and not config.run_options.refresh and cache.has(candidate)
            if cached:
                results.append(
                    FilingOutput(
                        raw_input=target,
                        cik=candidate.resolved_cik,
                        company_name=candidate.company_name,
                        ticker=candidate.ticker,
                        form=candidate.form,
                        filing_date=candidate.filing_date,
                        accession_no=candidate.accession_no,
                        source_url=candidate.source_url,
                        output_file=None,
                        success=True,
                        status="skipped_cached",
                        warning=candidate.warning,
                    )
                )
                log(f"Skipped cached: {candidate.company_name} {candidate.form} {candidate.accession_no}")
                continue

            filing = materialize_filing(candidate, limiter=limiter)
            full_markdown = convert_to_full_markdown(filing.html_content)
            sections = extract_sections(full_markdown, wanted_sections)
            output_path: Path | None = None

            if config.run_options.output_mode == "markdown_sections":
                output_path = write_sections_markdown_output(
                    output_dir=config.output_dir,
                    filing=filing,
                    sections=sections,
                )
            elif config.run_options.output_mode == "jsonl_chunks":
                chunks = []
                for section_name, section_text in sections.items():
                    chunks.extend(
                        chunk_text(
                            section=section_name,
                            text=section_text,
                            chunk_size=config.run_options.chunk_size,
                            chunk_overlap=config.run_options.chunk_overlap,
                        )
                    )
                output_path = write_chunks_jsonl_output(config.output_dir, filing, chunks)
            elif config.combined_file:
                combined_documents.append(render_company_markdown(filing, full_markdown))
            else:
                output_path = write_markdown_output(
                    output_dir=config.output_dir,
                    filing=filing,
                    full_markdown=full_markdown,
                )

            if config.run_options.resume and not config.run_options.refresh:
                with cache_lock:
                    cache.add(candidate)

            results.append(
                FilingOutput(
                    raw_input=target,
                    cik=filing.resolved_cik,
                    company_name=filing.company_name,
                    ticker=filing.ticker,
                    form=filing.form,
                    filing_date=filing.filing_date,
                    accession_no=filing.accession_no,
                    source_url=filing.source_url,
                    output_file=str(output_path) if output_path else None,
                    success=True,
                    status="success",
                    warning=filing.warning,
                )
            )
            if output_path:
                log(f"Saved: {output_path}")
            else:
                log(f"Prepared for combined output: {filing.company_name} {filing.form} {filing.accession_no}")

        return results, combined_documents
    finally:
        log(f"Target complete: {target}")


def run_pipeline(
    config: AppConfig,
    logger: Logger | None = None,
    cancel_event: threading.Event | None = None,
) -> RunSummary:
    log = logger or (lambda _: None)
    stop_event = cancel_event or threading.Event()

    configure_identity(config.identity, config.api_token or None)
    limiter = RateLimiter(config.rate_limit_rps)
    summary = RunSummary(
        started_at=datetime.utcnow(),
        filing_request=config.filing_request,
        run_options=config.run_options,
    )
    combined_documents: list[str] = []
    cache = RunCache(config.run_options.cache_dir)
    cache_lock = threading.Lock()
    if config.run_options.resume and not config.run_options.refresh:
        cache.load()

    with ThreadPoolExecutor(max_workers=config.run_options.max_workers) as executor:
        future_map = {
            executor.submit(
                _process_single_target,
                target,
                config,
                limiter,
                cache,
                cache_lock,
                stop_event,
                log,
            ): target
            for target in config.targets
        }
        for future in as_completed(future_map):
            target = future_map[future]
            try:
                target_results, target_combined_docs = future.result()
                summary.results.extend(target_results)
                combined_documents.extend(target_combined_docs)
            except Exception as exc:  # noqa: BLE001
                summary.results.append(
                    FilingOutput(
                        raw_input=target,
                        cik=None,
                        company_name=None,
                        ticker=None,
                        form=None,
                        filing_date=None,
                        accession_no=None,
                        source_url=None,
                        output_file=None,
                        success=False,
                        status=classify_error(exc),
                        error=str(exc),
                    )
                )
                log(f"Failed: {target} -> {exc}")

    summary.finished_at = datetime.utcnow()
    summary.cancelled = stop_event.is_set()

    if config.combined_file and config.run_options.output_mode == "markdown_full":
        combined_path = write_combined_markdown(config.output_dir, summary, documents=combined_documents)
        log(f"Combined file saved: {combined_path}")
    if config.run_options.resume and not config.run_options.refresh:
        cache.save()
    if config.include_manifest:
        manifest_path = write_manifest(config.output_dir, summary)
        log(f"Manifest saved: {manifest_path}")
    if config.run_options.report_format != "none":
        report_path = write_run_report(
            config.output_dir,
            summary,
            config.run_options.report_format,
            report_file=config.run_options.report_file,
        )
        log(f"Run report saved: {report_path}")

    log(
        "Completed run: "
        f"{summary.success_count} succeeded, {summary.failure_count} failed, "
        f"{summary.skipped_count} skipped, total {summary.total}."
    )
    return summary


def write_default_config(path: Path) -> None:
    content = """identity = "Your Name your.email@example.com"
api_token = ""
targets = ["0000320193", "amazon", "TSLA"]
output_dir = "output"
combined_file = true
include_manifest = false
rate_limit_rps = 2.0
forms = ["10-K"]
latest_n = 1
since = ""
until = ""
years = []
sections = []
resume = true
refresh = false
cache_dir = ".sec_miner_cache"
max_workers = 1
output_mode = "markdown_full"
chunk_size = 1400
chunk_overlap = 200
report_format = "none"
report_file = ""
"""
    path.write_text(content, encoding="utf-8")
