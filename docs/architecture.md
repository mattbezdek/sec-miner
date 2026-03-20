# SEC-miner Architecture (Phase 0-6)

## Pipeline Boundaries

The runtime flow is intentionally separated into five layers:

1. **Input and config** (`cli.py`, `config.py`): parse CLI/TOML/env and build `AppConfig`.
2. **Resolution and selection** (`resolver.py`, `fetcher.py`): resolve targets and select filing candidates.
3. **Materialization and conversion** (`fetcher.py`, `converter.py`): fetch filing HTML and convert to markdown.
4. **Output and persistence** (`writer.py`, `cache.py`): write markdown/manifest and persist cache keys.
5. **Orchestration** (`pipeline.py`): coordinate retries, skip behavior, and run summary.

## New Domain Objects

- `FilingRequest`: request-time controls for forms, top-N, date windows, and year filters.
- `RunOptions`: runtime behavior controls for resume/refresh and cache path.
- `FilingCandidate`: metadata-first selection object before HTML materialization.

These abstractions let the pipeline skip cached filings before expensive conversion.

## Error Handling Strategy

- Target-level exceptions are captured in pipeline and recorded as failed results.
- Fetch/materialization steps use bounded retry with backoff.
- Cache read corruption falls back to empty cache (non-fatal) to preserve run continuity.

## Caching Strategy (Phase 2)

- Local JSON cache lives at `run_options.cache_dir/filings_cache.json`.
- Key format: `cik|form|accession|filing_date`.
- Cache entries are added only after a successful filing materialization/conversion path.
- `--refresh` bypasses cache reads and forces fresh fetch behavior.

## Determinism Guarantees

- Filing candidate selection is sorted by filing date descending with accession tie-breaker.
- Output filenames include form and accession identifiers.
- Manifest includes request metadata and per-result status (`success`, `failed`, `skipped_cached`).
