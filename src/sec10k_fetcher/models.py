from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AppConfig:
    identity: str = ""
    api_token: str = ""
    targets: list[str] = field(default_factory=list)
    output_dir: Path = Path("output")
    combined_file: bool = True
    include_manifest: bool = False
    rate_limit_rps: float = 2.0
    filing_request: "FilingRequest" = field(default_factory=lambda: FilingRequest())
    run_options: "RunOptions" = field(default_factory=lambda: RunOptions())


@dataclass
class FilingRequest:
    forms: list[str] = field(default_factory=lambda: ["10-K"])
    latest_n: int = 1
    since: str | None = None
    until: str | None = None
    years: list[int] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)


@dataclass
class RunOptions:
    resume: bool = True
    refresh: bool = False
    cache_dir: Path = Path(".sec_miner_cache")
    max_workers: int = 1
    output_mode: str = "markdown_full"
    chunk_size: int = 1400
    chunk_overlap: int = 200
    report_format: str = "none"
    report_file: str | None = None


@dataclass
class ResolvedTarget:
    raw_input: str
    cik: str
    company_name: str
    ticker: str | None
    resolution_method: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class FilingOutput:
    raw_input: str
    cik: str | None
    company_name: str | None
    ticker: str | None
    form: str | None
    filing_date: str | None
    accession_no: str | None
    source_url: str | None
    output_file: str | None
    success: bool
    status: str = "success"
    warning: str | None = None
    error: str | None = None
    report_file: str | None = None

    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "raw_input": self.raw_input,
            "cik": self.cik,
            "company_name": self.company_name,
            "ticker": self.ticker,
            "form": self.form,
            "filing_date": self.filing_date,
            "accession_no": self.accession_no,
            "source_url": self.source_url,
            "output_file": self.output_file,
            "success": self.success,
            "status": self.status,
            "warning": self.warning,
            "error": self.error,
            "report_file": self.report_file,
        }


@dataclass
class RunSummary:
    started_at: datetime
    finished_at: datetime | None = None
    results: list[FilingOutput] = field(default_factory=list)
    filing_request: FilingRequest | None = None
    run_options: RunOptions | None = None
    cancelled: bool = False

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success_count(self) -> int:
        return sum(1 for result in self.results if result.success)

    @property
    def failure_count(self) -> int:
        return self.total - self.success_count

    @property
    def skipped_count(self) -> int:
        return sum(1 for result in self.results if result.status == "skipped_cached")
