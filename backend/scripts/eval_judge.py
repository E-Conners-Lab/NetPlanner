#!/usr/bin/env python
"""Phase 2b — score saved Comparison outputs with an LLM-as-judge.

The spec-blessed fallback for NVIDIA NeMo Evaluator (SPEC §8): the identical
three-criterion rubric (cell accuracy, completeness, confidence honesty), run via
a thin script against a strong third-family judge on NVIDIA's catalog instead of
standing up the NeMo Evaluator microservice. Rubric + fixtures are unchanged, so
scores stay comparable to a microservice run.

The judge reads the same fixture (ground-truth research input) and each saved
``results/<fixture>__<provider>.json`` pair produced by ``eval_compare.py``, then
writes ``results/<fixture>__<provider>__judge.json`` and prints a scorecard.

Run from the backend/ directory (needs NVIDIA_API_KEY in backend/.env):

    uv run python scripts/eval_judge.py                  # score every saved pair
    uv run python scripts/eval_judge.py --fixture campus-wifi
    uv run python scripts/eval_judge.py --judge-model qwen/qwen3.5-122b-a10b
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Make the `app` package importable when run as a plain script (pytest sets this
# via pythonpath, but `python scripts/...` does not). Mirrors eval_compare.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_REPO = Path(__file__).resolve().parents[2]
_FIXTURES = _REPO / "docs" / "evals" / "fixtures"
_RESULTS = _REPO / "docs" / "evals" / "results"
_JUDGE_TIMEOUT_S = 120


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Not found: {path}")
    return json.loads(path.read_text())


def _saved_pairs(fixture_name: str) -> list[Path]:
    """Every results/<fixture>__<provider>.json (excluding judge outputs)."""
    return sorted(
        p
        for p in _RESULTS.glob(f"{fixture_name}__*.json")
        if not p.name.endswith("__judge.json")
    )


async def _judge_one(
    pair_path: Path, fixture: dict, judge_model: str, api_key: str
) -> dict | None:
    from app.evals.judge import assert_judge_independent, judge_pair

    pair = _load_json(pair_path)
    model_under_test = pair.get("model", "")
    assert_judge_independent(judge_model, model_under_test)

    scores = await asyncio.wait_for(
        judge_pair(
            fixture=fixture,
            comparison=pair["result"],
            judge_model=judge_model,
            api_key=api_key,
        ),
        timeout=_JUDGE_TIMEOUT_S,
    )
    return {
        "fixture": pair.get("fixture"),
        "provider": pair.get("provider"),
        "model": model_under_test,
        "judge_model": judge_model,
        "scores": scores.as_dict(),
    }


def _save(verdict: dict) -> Path:
    out = _RESULTS / f"{verdict['fixture']}__{verdict['provider']}__judge.json"
    out.write_text(json.dumps(verdict, indent=2))
    return out


def _print_scorecard(verdicts: list[dict]) -> None:
    from app.evals.judge import RUBRIC_METRICS

    print()
    print("=" * 78)
    print(f"  LLM-as-judge scorecard  (judge: {verdicts[0]['judge_model']})")
    print("=" * 78)
    header = f"  {'model':<40}" + "".join(
        f"{m.split('_')[0]:>14}" for m in RUBRIC_METRICS
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for v in verdicts:
        row = f"  {v['model']:<40}"
        row += "".join(f"{v['scores'][m]['score']:>14}" for m in RUBRIC_METRICS)
        print(row)


async def _main_async(args: argparse.Namespace) -> None:
    from app.config import get_settings

    settings = get_settings()
    api_key = settings.require_nvidia_api_key()
    judge_model = args.judge_model or settings.nvidia_judge_model

    fixture = _load_json(_FIXTURES / f"{args.fixture}.json")
    pairs = _saved_pairs(args.fixture)
    if not pairs:
        raise SystemExit(
            f"No saved pairs for {args.fixture!r}. Run eval_compare.py first."
        )

    verdicts: list[dict] = []
    for pair_path in pairs:
        try:
            verdict = await _judge_one(pair_path, fixture, judge_model, api_key)
        except Exception as exc:  # noqa: BLE001 — surface, don't crash the batch
            print(f"\n  [{pair_path.name}] judge failed: {exc!r}")
            continue
        if verdict is None:
            continue
        saved = _save(verdict)
        print(f"  judged {verdict['model']} → {saved.relative_to(_REPO)}")
        verdicts.append(verdict)

    if verdicts:
        _print_scorecard(verdicts)


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-as-judge over saved pairs.")
    parser.add_argument(
        "--fixture", default="campus-wifi", help="fixture name (no .json)"
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="override the judge model id (default: settings.nvidia_judge_model)",
    )
    asyncio.run(_main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
