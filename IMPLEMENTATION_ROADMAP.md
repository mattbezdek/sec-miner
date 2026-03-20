# SEC-miner Implementation Roadmap

## Purpose

This roadmap translates the current product direction into an execution plan with clear phases, deliverables, dependencies, acceptance criteria, and testing strategy.

The plan prioritizes:

1. Expanding filing coverage beyond only latest 10-K.
2. Improving repeat-run efficiency (incremental/resume behavior).
3. Increasing throughput safely (bounded concurrency + rate awareness).
4. Producing analyst- and LLM-friendly outputs.
5. Improving reliability, observability, and user experience.

---

## Implementation Status (Updated Mar 20, 2026)

### Completed in this iteration

- **Phase 0 (mostly complete):**
  - Added domain abstractions `FilingRequest` and `RunOptions`.
  - Refactored orchestration to consume request/options objects.
  - Added architecture documentation in `docs/architecture.md`.
  - Expanded tests across config, fetch filtering, and pipeline cache behavior.
- **Phase 1 (complete):**
  - Added CLI support for `--form`, `--latest-n`, `--since`, `--until`, and `--year`.
  - Added TOML/config support and validation for the same options.
  - Reworked fetch path to select/filter multiple filings deterministically.
  - Extended manifest and output metadata to include form/request details.
- **Phase 2 (complete):**
  - Added JSON-backed local cache (`cache.py`) with schema versioning.
  - Implemented resume/skip behavior in pipeline with `skipped_cached` status.
  - Added CLI/config support for `--resume`, `--refresh`, and `--cache-dir`.
  - Added cache lifecycle test coverage (first run fetches, second run skips).

### Deferred to later phases

- Parallel processing (`--max-workers`) from Phase 3.
- Section-aware/chunk output modes from Phase 4.
- GUI progress/cancel/preset upgrades from Phase 5.

---

## Current Baseline

SEC-miner currently provides:

- Target resolution (CIK/ticker/name with best-match warning behavior).
- Fetch latest 10-K per target.
- HTML to markdown conversion.
- Per-company or combined markdown output.
- Optional JSON manifest.
- CLI + tkinter GUI.

Key constraints in current architecture:

- Filing type is fixed (`10-K`).
- Selection is fixed (`latest()` only).
- Pipeline is sequential.
- No persisted cache/state for incremental runs.
- Limited test surface around resolver/fetch/pipeline behavior.

---

## Guiding Principles

- Preserve simplicity for new users (safe defaults, optional advanced flags).
- Keep SEC-friendly behavior (explicit identity, controlled request rates).
- Maintain deterministic outputs for reproducibility.
- Add features in vertical slices (CLI + core + tests + docs in each phase).
- Avoid breaking current workflows; introduce backward-compatible defaults.

---

## Phase 0: Foundation and Design Alignment (3-4 days)

### Goals

- Lock scope, interfaces, and success metrics before larger feature work.
- Reduce rework by introducing a few internal abstractions early.

### Deliverables

- Architectural note (`docs/architecture.md`) for fetch/write pipeline boundaries.
- Configuration schema update plan for new options.
- Error taxonomy draft (recoverable vs non-recoverable failures).
- Expanded tests for existing baseline behavior before refactors.

### Implementation Tasks

- Introduce internal domain concepts:
  - `FilingRequest` (form, date filters, selection settings).
  - `RunOptions` (resume/cache/concurrency/report toggles).
- Refactor pipeline signatures to accept richer request/options objects.
- Add fixture-based tests that pin current output formatting and manifest shape.

### Acceptance Criteria

- Existing CLI invocations still produce identical outputs.
- Test suite includes baseline regression checks for:
  - config loading precedence,
  - writer file naming/collision behavior,
  - pipeline summary counts.

---

## Phase 1: Multi-Form + Filing Selection Controls (1-1.5 weeks)

### Goals

- Support broader SEC use cases and basic historical retrieval.

### Scope

- CLI options:
  - `--form` (repeatable single values) and/or `--forms` (comma-delimited).
  - `--latest-n`.
  - `--since` / `--until` (ISO date).
  - `--year` (single or repeatable).
- Config file parity for all options.
- Manifest updates to include selected `form` and selection metadata.

### Implementation Tasks

- Update `AppConfig` to include form and filing selection options.
- Extend fetcher methods to retrieve and filter filings, not only `.latest()`.
- Introduce deterministic selection ordering:
  - newest first by filing date,
  - stable tie-breakers by accession.
- Output naming strategy updated for form type and multi-filing runs.
- Add validation rules:
  - disallow contradictory combinations (`--year` with out-of-range explicit dates unless explicitly documented),
  - `latest_n >= 1`,
  - recognized form strings.

### Testing

- Unit tests for config parsing/validation combinations.
- Fetcher tests with mocked filings list:
  - correct filter behavior by date/year/form,
  - correct top-N selection.
- Writer tests for multi-filing naming and deterministic ordering.
- CLI smoke tests for representative invocations.

### Acceptance Criteria

- User can fetch, for each target:
  - latest 1+ filing(s),
  - different SEC form(s),
  - date-bounded filing set.
- Manifest clearly indicates what was requested and what was returned.

---

## Phase 2: Incremental/Resume Runs with Local Cache (1 week)

### Goals

- Prevent duplicate work across repeated runs.
- Make scheduled batch execution practical.

### Scope

- New options:
  - `--resume` (default `true` or explicit flag; decision in design review),
  - `--refresh` to bypass cache.
  - optional `--cache-dir`.
- Persist previously successful `(target, cik, form, accession)` metadata.
- Skip already-downloaded filings unless refresh requested.

### Implementation Tasks

- Add lightweight cache store (JSON index initially; later pluggable backend).
- Define cache key schema and versioned cache file format.
- Integrate skip logic in pipeline before conversion/write.
- Log explicit skip reason in run output and manifest.

### Testing

- Cache lifecycle tests:
  - initial miss -> fetch + cache write,
  - second run -> skip,
  - refresh -> refetch.
- Corrupt cache handling test (graceful fallback + warning).

### Acceptance Criteria

- Re-running same targets/forms avoids redundant fetch/convert/write.
- Manifest differentiates `success`, `failed`, and `skipped_cached`.
- Cache corruption never crashes entire run.

---

## Phase 3: Parallel Processing with Safe Throttling (1 week)

### Goals

- Improve throughput for large target lists while respecting endpoint limits.

### Scope

- New option: `--max-workers` (default conservative, e.g., 3-5).
- Shared rate-limit strategy across workers.
- Thread-safe logging and summary aggregation.

### Implementation Tasks

- Convert sequential loop into bounded worker pool execution.
- Implement shared limiter policy:
  - global request pacing,
  - jitter preserved,
  - per-worker backoff on transient failures.
- Ensure output writing remains collision-safe and deterministic.

### Testing

- Concurrency tests (mocked fetch latency/failures):
  - no deadlocks,
  - expected completion counts,
  - proper retry behavior.
- Deterministic summary tests regardless of execution interleaving.

### Acceptance Criteria

- Batch runtime improves materially on 20+ targets.
- No increase in failure rate under normal conditions.
- Logs remain readable and summary remains accurate.

---

## Phase 4: Section-Aware and RAG-Friendly Output Modes (1-1.5 weeks)

### Goals

- Reduce token cost and make outputs immediately ingestible for retrieval workflows.

### Scope

- New option: `--sections` (common aliases: `business`, `risk_factors`, `mda`, `financials`).
- New output modes:
  - `markdown_full` (existing),
  - `markdown_sections`,
  - `jsonl_chunks`.
- Chunk metadata fields:
  - company, cik, ticker, form, accession, filing_date, section, chunk_id.

### Implementation Tasks

- Add section mapping/normalization layer.
- Build chunker with stable chunk IDs and configurable chunk size/overlap.
- Extend writer to emit JSONL and optional sidecar metadata.

### Testing

- Section extraction tests on representative filing fixtures.
- Chunk stability tests (same input -> same chunk IDs).
- Output contract tests for JSONL schema.

### Acceptance Criteria

- User can request only specific sections when available.
- JSONL output is directly consumable by vector ingestion pipelines.

---

## Phase 5: UX and Reporting Improvements (4-6 days)

### Goals

- Improve non-CLI user productivity and run observability.

### Scope

- GUI:
  - progress bar + processed/total counters,
  - cancel support,
  - save/load run presets,
  - open output directory button.
- CLI:
  - `resolve` subcommand to preview target mapping before full run.
- Optional run report:
  - markdown or HTML summary for business users.

### Implementation Tasks

- Add cancellable execution token checked by pipeline.
- Add GUI state management for run lifecycle (idle/running/cancelled/complete).
- Implement `sec-miner resolve` with ambiguity details and selected candidate.

### Testing

- CLI tests for resolve command behavior.
- GUI manual test checklist plus minimal unit coverage around config/preset serialization.

### Acceptance Criteria

- GUI user can cancel long runs safely.
- Analysts can review run outcomes without opening raw manifest JSON.
- Users can verify name resolution before running full extraction.

---

## Phase 6: Reliability and Developer Quality (ongoing, start after Phase 1)

### Goals

- Sustain velocity while reducing regression risk.

### Scope

- Test suite expansion and CI quality gates.
- Better exception classification and user-facing error messages.
- Optional telemetry/logging mode (local structured logs, no remote requirement).

### Implementation Tasks

- Add integration tests with mocked `edgar` and `sec2md` boundaries.
- Add coverage threshold target (e.g., 80% on core modules).
- Add lint/type checks in CI (`ruff`, `mypy`, `pytest`).

### Acceptance Criteria

- CI blocks merges on lint/type/test failures.
- Critical code paths (resolver/fetch/pipeline/writer/config) are thoroughly covered.

---

## Suggested Milestone Plan (8-10 weeks total)

- **Milestone A (Week 1):** Phase 0 complete, baseline tests expanded.
- **Milestone B (Weeks 2-3):** Phase 1 complete (forms + selection).
- **Milestone C (Week 4):** Phase 2 complete (incremental/resume cache).
- **Milestone D (Week 5):** Phase 3 complete (concurrency).
- **Milestone E (Weeks 6-7):** Phase 4 complete (section/chunk outputs).
- **Milestone F (Week 8):** Phase 5 complete (UX/reporting).
- **Hardening Buffer (Weeks 9-10):** Phase 6 depth work + bugfixes + docs polish.

---

## Technical Dependencies and Risks

### Dependencies

- `edgartools` behavior for filing discovery/filtering across forms.
- `sec2md` conversion quality/stability across varied filing HTML.
- Cross-platform GUI behavior (`tkinter`) for cancellation and responsiveness.

### Major Risks

- API/HTML variability causing section extraction inconsistency.
- Concurrency introducing nondeterminism or race conditions in writes/logging.
- Cache invalidation complexity when options change between runs.

### Mitigations

- Introduce contract tests with representative fixture corpus.
- Keep deterministic ordering and stable naming as explicit requirements.
- Version cache schema and include option fingerprint in cache key.

---

## Definition of Done (per feature)

A feature is considered complete only when:

- CLI and config support are both implemented.
- GUI parity is provided where applicable.
- Unit/integration tests cover success + failure paths.
- Manifest/report outputs include new fields as needed.
- README includes usage examples and migration notes.

---

## Immediate Next Sprint Proposal

If you want to start now with maximal value/effort ratio:

1. Execute **Phase 0** quickly (focus on internal abstractions and tests).
2. Implement **Phase 1** first with `--form`, `--latest-n`, and `--since`.
3. Follow immediately with **Phase 2** cache/resume to make recurring usage efficient.

This sequence unlocks the biggest functional gain with manageable implementation risk.
