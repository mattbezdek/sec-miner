from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sec10k_fetcher.fetcher import FilingCandidate


@dataclass
class RunCache:
    cache_dir: Path
    cache_file: Path = field(init=False)
    entries: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.cache_file = self.cache_dir / "filings_cache.json"

    def load(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.cache_file.exists():
            self.entries = set()
            return
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
            items = payload.get("entries", [])
            self.entries = {str(item) for item in items}
        except Exception:  # noqa: BLE001
            # Corrupt cache should not break the run.
            self.entries = set()

    def save(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "entries": sorted(self.entries)}
        self.cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def key_for(self, candidate: FilingCandidate) -> str:
        return (
            f"{candidate.resolved_cik}|{candidate.form}|{candidate.accession_no}"
            f"|{candidate.filing_date}"
        )

    def has(self, candidate: FilingCandidate) -> bool:
        return self.key_for(candidate) in self.entries

    def add(self, candidate: FilingCandidate) -> None:
        self.entries.add(self.key_for(candidate))
