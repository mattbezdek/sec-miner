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
    filing_date: str | None
    accession_no: str | None
    source_url: str | None
    output_file: str | None
    success: bool
    warning: str | None = None
    error: str | None = None

    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "raw_input": self.raw_input,
            "cik": self.cik,
            "company_name": self.company_name,
            "ticker": self.ticker,
            "filing_date": self.filing_date,
            "accession_no": self.accession_no,
            "source_url": self.source_url,
            "output_file": self.output_file,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
        }


@dataclass
class RunSummary:
    started_at: datetime
    finished_at: datetime | None = None
    results: list[FilingOutput] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success_count(self) -> int:
        return sum(1 for result in self.results if result.success)

    @property
    def failure_count(self) -> int:
        return self.total - self.success_count
