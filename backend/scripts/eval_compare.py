#!/usr/bin/env python
"""Phase 2a — run the Comparison agent on a fixture, per provider.

Research data is supplied from the fixture (no live web search), so the matrix
reflects the *model's reasoning alone* — making Claude vs Nemotron apples-to-
apples. Used to validate the live NVIDIA path and to capture side-by-side output
for the writeup.

Run from the backend/ directory:

    uv run python scripts/eval_compare.py                  # both providers
    uv run python scripts/eval_compare.py --fixture campus-wifi
    PROVIDER=nvidia_nim uv run python scripts/eval_compare.py --single

Results are written to docs/evals/results/<fixture>__<provider>.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Make the `app` package importable when run as a plain script (pytest sets this
# via pythonpath, but `python scripts/...` does not).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_REPO = Path(__file__).resolve().parents[2]
_FIXTURES = _REPO / "docs" / "evals" / "fixtures"
_RESULTS = _REPO / "docs" / "evals" / "results"
_RUN_TIMEOUT_S = 150

_BADGE = {
    "confirmed": "[confirmed]",
    "estimated": "[estimated]",
    "unavailable": "[unavailable]",
}


def _load_fixture(name: str) -> dict:
    path = _FIXTURES / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"Fixture not found: {path}")
    return json.loads(path.read_text())


async def _run_provider(provider: str, fixture: dict) -> tuple[str, object]:
    """Run the Comparison agent under one provider; return (model_id, result)."""
    os.environ["PROVIDER"] = provider

    # Re-resolve settings for this provider (the accessor is process-cached).
    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    model = (
        settings.nvidia_model if provider == "nvidia_nim" else settings.comparison_model
    )

    from app.agents.comparison import run_comparison_agent
    from app.schemas.project import ProjectContext
    from app.schemas.research import ResearchItem, ResearchResult

    ctx = ProjectContext(**fixture["project_context"])
    research = [
        ResearchResult(
            query=r["query"],
            results=[ResearchItem(**item) for item in r["results"]],
        )
        for r in fixture["research_data"]
    ]
    result = await asyncio.wait_for(
        run_comparison_agent(
            vendors=fixture["vendors"],
            criteria=fixture["criteria"],
            research_data=research,
            project_context=ctx,
        ),
        timeout=_RUN_TIMEOUT_S,
    )
    return model, result


def _print_matrix(provider: str, model: str, result: object) -> None:
    print()
    print("=" * 78)
    print(f"  PROVIDER: {provider}    MODEL: {model}")
    print("=" * 78)
    for vendor in result.vendors:  # type: ignore[attr-defined]
        print(f"\n  {vendor}")
        for criterion in result.criteria:  # type: ignore[attr-defined]
            cell = result.matrix[vendor][criterion]  # type: ignore[attr-defined]
            badge = _BADGE.get(cell.confidence, cell.confidence)
            src = f"  ({cell.source})" if cell.source else ""
            print(f"    - {criterion}: {cell.value} {badge}{src}")
    print(f"\n  Summary: {result.summary}")  # type: ignore[attr-defined]


def _save(fixture_name: str, provider: str, model: str, result: object) -> Path:
    _RESULTS.mkdir(parents=True, exist_ok=True)
    out = _RESULTS / f"{fixture_name}__{provider}.json"
    payload = {
        "fixture": fixture_name,
        "provider": provider,
        "model": model,
        "result": result.model_dump(),  # type: ignore[attr-defined]
    }
    out.write_text(json.dumps(payload, indent=2))
    return out


async def _main_async(args: argparse.Namespace) -> None:
    fixture = _load_fixture(args.fixture)
    providers = (
        [os.environ.get("PROVIDER", "anthropic")]
        if args.single
        else ["anthropic", "nvidia_nim"]
    )
    for provider in providers:
        try:
            model, result = await _run_provider(provider, fixture)
        except Exception as exc:  # noqa: BLE001 — surface, don't crash the run
            print(f"\n  [{provider}] run failed: {exc!r}")
            continue
        _print_matrix(provider, model, result)
        saved = _save(args.fixture, provider, model, result)
        print(f"  saved → {saved.relative_to(_REPO)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Comparison agent per provider."
    )
    parser.add_argument(
        "--fixture", default="campus-wifi", help="fixture name (no .json)"
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="run only the provider in $PROVIDER (default: both)",
    )
    asyncio.run(_main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
