## SEC-miner

Lightweight Python package to fetch SEC filings for multiple companies and export
LLM-friendly markdown and chunked JSONL.

- Default extraction: full 10-K (configurable forms)
- Flexible inputs: CIKs, tickers, or ambiguous company names (best-match + warning)
- Optional JSON manifest, run reports, and combined markdown output
- Section-aware output and JSONL chunking mode for RAG pipelines
- Incremental resume cache to skip previously downloaded filings
- Bounded concurrency (`--max-workers`) with shared rate limiting
- Continue-on-failure batch execution with end-of-run summary
- Simple GUI (`tkinter`) for non-CLI users

The SEC requires an identity string in the format `Name email@example.com` for requests.
An API key/token is optional and typically only needed if you encounter access restrictions.
This library was coded with GPT-5.3 Codex.

## Install and Use

These steps assume the user already downloaded/cloned this repo.

### Recommended (with `uv`)

1) Install `uv` (one time):

- macOS (Homebrew):

```bash
brew install uv
```

- Any OS with Python:

```bash
python -m pip install --user uv
```

2) Enter the project folder:

```bash
cd sec
```

3) Create environment and install dependencies:

```bash
python -m uv sync --python 3.11
```

4) Start the GUI (easiest for non-CLI users):

- macOS/Linux:

```bash
.venv/bin/sec-miner-gui
```

- Windows PowerShell:

```powershell
.venv\Scripts\sec-miner-gui.exe
```

### Fallback (without `uv`)

If someone cannot install `uv`, they can still run with `venv` + `pip`:

```bash
python -m venv .venv
```

Activate the environment:

- macOS/Linux:

```bash
source .venv/bin/activate
```

- Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the package:

```bash
python -m pip install -U pip
pip install .
```

Run:

- GUI:

```bash
sec-miner-gui
```

- CLI help:

```bash
sec-miner --help
```

## Quick Start (CLI)

```bash
.venv/bin/sec-miner run \
  --identity "Your Name your.email@example.com" \
  --target 0000320193 \
  --target amazon \
  --form 10-K \
  --latest-n 1 \
  --output-dir output \
  --include-manifest
```

### Advanced CLI Options

- `--form`: Repeatable form selector (for example, `--form 10-K --form 10-Q`).
- `--latest-n`: Number of most recent filings per target and form.
- `--since` / `--until`: ISO date filters (`YYYY-MM-DD`).
- `--year`: Repeatable year filter.
- `--resume` / `--no-resume`: Toggle cache-based skip behavior.
- `--refresh`: Force re-fetch and bypass cache.
- `--cache-dir`: Override cache location (default `.sec_miner_cache`).
- `--max-workers`: Process targets concurrently.
- `--section`: Repeatable section selector (`business`, `risk_factors`, `mda`, `financials`).
- `--output-mode`: `markdown_full`, `markdown_sections`, or `jsonl_chunks`.
- `--chunk-size` / `--chunk-overlap`: Chunk controls for `jsonl_chunks`.
- `--report-format`: `none`, `markdown`, or `html`.
- `resolve` subcommand: preview company resolution before running full extraction.

## GUI

```bash
.venv/bin/sec-miner-gui
```

SEC identity format example:

```text
Jane Doe jane.doe@example.com
```

Paste one target per line, choose output options, and click **Run**.

### GUI Field Guide

- **SEC Identity (required)**: Your contact identity in `Name email@example.com` format. SEC requires this.
- **Optional API Token**: Leave blank in most cases. Only add if you encounter access restrictions.
- **Targets**: One per line (CIK, ticker, or company name), for example `0000320193`, `AAPL`, or `Apple`.
- **Output Directory**: Folder where markdown files are written.
- **Rate Limit (req/sec)**: Controls request pace to be polite to SEC endpoints (default `2.0`).
- **Include JSON manifest**: Adds a machine-readable summary file for success/failure and output paths.
- **Write combined markdown file**: Produces one merged markdown file across all successful companies.
  When enabled, SEC-miner skips writing per-company markdown files.
- **Run**: Starts processing in the background.
- **Cancel**: Stops the run safely.
- **Save Preset / Load Preset**: Reuse common GUI settings.
- **Open Output Folder**: Opens your output path in Finder.
- **Progress / Summary**: Live status messages and final success/failure counts.

## Config (TOML)

Generate starter config:

```bash
.venv/bin/sec-miner init-config --path config.toml
```

Then run with:

```bash
.venv/bin/sec-miner run --config config.toml
```

Precedence is:
CLI/GUI inputs > TOML > environment variables.

`init-config` now includes filing selection and cache options:

- `forms`, `latest_n`, `since`, `until`, `years`, `sections`
- `resume`, `refresh`, `cache_dir`, `max_workers`
- `output_mode`, `chunk_size`, `chunk_overlap`
- `report_format`, `report_file`

Environment fallback:
- `SEC_IDENTITY`
- `SEC_API_TOKEN`
