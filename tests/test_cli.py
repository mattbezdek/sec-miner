from __future__ import annotations

from typer.testing import CliRunner

from sec10k_fetcher.cli import app
from sec10k_fetcher.models import ResolvedTarget


def test_resolve_command(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(
        "sec10k_fetcher.cli.resolve_target",
        lambda _target: ResolvedTarget(
            raw_input="AAPL",
            cik="0000320193",
            company_name="Apple Inc.",
            ticker="AAPL",
            resolution_method="search",
            warnings=[],
        ),
    )
    result = runner.invoke(app, ["resolve", "--target", "AAPL"])
    assert result.exit_code == 0
    assert "Company: Apple Inc." in result.stdout
    assert "CIK: 0000320193" in result.stdout
