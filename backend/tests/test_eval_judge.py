"""Unit tests for the Phase 2b LLM-as-judge (NeMo-rubric fallback script).

The judge scores saved Comparison outputs on three 1-5 criteria (cell accuracy,
completeness, confidence honesty) via a strong third-family model on NVIDIA's
catalog. The network call is mocked — deterministic in CI.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.evals import judge

# --- fixtures (mirror the saved results/ + fixtures/ shapes) ------------------

_FIXTURE = {
    "project_context": {"name": "Campus Wi-Fi Refresh", "company": "Northwind"},
    "vendors": ["Cisco Meraki", "Juniper Mist"],
    "criteria": ["licensing model", "per-AP annual cost"],
    "research_data": [
        {
            "query": "Cisco Meraki pricing",
            "results": [
                {
                    "vendor": "Cisco Meraki",
                    "product": "MR46E",
                    "price_point": "$155",
                    "unit": "per AP per year",
                    "source_url": "https://example-reseller.test/meraki",
                    "confidence": "estimated",
                }
            ],
        }
    ],
}

_COMPARISON = {
    "vendors": ["Cisco Meraki", "Juniper Mist"],
    "criteria": ["licensing model", "per-AP annual cost"],
    "matrix": {
        "Cisco Meraki": {
            "licensing model": {
                "value": "Subscription-only",
                "source": "",
                "confidence": "estimated",
            },
            "per-AP annual cost": {
                "value": "$155 per AP per year",
                "source": "https://example-reseller.test/meraki",
                "confidence": "estimated",
            },
        },
        "Juniper Mist": {
            "licensing model": {
                "value": "Subscription-only",
                "source": "",
                "confidence": "estimated",
            },
            "per-AP annual cost": {
                "value": "$130 per AP per year",
                "source": "",
                "confidence": "estimated",
            },
        },
    },
    "summary": "All vendors are subscription-based.",
}

_VALID_JUDGE_JSON = json.dumps(
    {
        "cell_accuracy": {"score": 5, "rationale": "Cells match the research."},
        "completeness": {"score": 4, "rationale": "All cells present."},
        "confidence_honesty": {"score": 5, "rationale": "No over-claimed confirmed."},
    }
)


def _judge_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


# --- prompt construction (AI-1: system before untrusted, boundary markers) ----


def test_judge_system_prompt_defines_three_metrics() -> None:
    for metric in ("cell_accuracy", "completeness", "confidence_honesty"):
        assert metric in judge.JUDGE_SYSTEM
    # The judge is told to treat the inputs as data, not instructions (AI-1).
    assert "never as instructions" in judge.JUDGE_SYSTEM.lower() or (
        "not as instructions" in judge.JUDGE_SYSTEM.lower()
    )


def test_build_judge_prompt_wraps_inputs_in_boundary_markers() -> None:
    prompt = judge.build_judge_prompt(_FIXTURE, _COMPARISON)
    # Both untrusted blocks are explicitly delimited.
    assert "<<RESEARCH_INPUT>>" in prompt and "<</RESEARCH_INPUT>>" in prompt
    assert "<<MATRIX_OUTPUT>>" in prompt and "<</MATRIX_OUTPUT>>" in prompt
    # Research-side ground truth and the model's value both reach the judge.
    assert "$155" in prompt
    assert "Subscription-only" in prompt
    # Research input precedes the matrix output it is used to score.
    assert prompt.index("<<RESEARCH_INPUT>>") < prompt.index("<<MATRIX_OUTPUT>>")


# --- response parsing ---------------------------------------------------------


def test_parse_judge_response_valid_json() -> None:
    scores = judge.parse_judge_response(_VALID_JUDGE_JSON)
    assert scores.cell_accuracy.score == 5
    assert scores.completeness.score == 4
    assert scores.confidence_honesty.score == 5
    assert scores.cell_accuracy.rationale == "Cells match the research."


def test_parse_judge_response_strips_reasoning_cot() -> None:
    raw = f"<think>Let me assess each cell...</think>\n{_VALID_JUDGE_JSON}"
    scores = judge.parse_judge_response(raw)
    assert scores.confidence_honesty.score == 5


def test_parse_judge_response_tolerates_surrounding_prose() -> None:
    raw = f"Here is my assessment:\n{_VALID_JUDGE_JSON}\nThanks."
    scores = judge.parse_judge_response(raw)
    assert scores.completeness.score == 4


def test_parse_judge_response_rejects_malformed_json() -> None:
    with pytest.raises(judge.JudgeParseError):
        judge.parse_judge_response("not json at all")


def test_parse_judge_response_rejects_out_of_range_score() -> None:
    bad = json.dumps(
        {
            "cell_accuracy": {"score": 7, "rationale": "x"},
            "completeness": {"score": 4, "rationale": "x"},
            "confidence_honesty": {"score": 5, "rationale": "x"},
        }
    )
    with pytest.raises(judge.JudgeParseError):
        judge.parse_judge_response(bad)


def test_parse_judge_response_rejects_missing_metric() -> None:
    bad = json.dumps({"cell_accuracy": {"score": 5, "rationale": "x"}})
    with pytest.raises(judge.JudgeParseError):
        judge.parse_judge_response(bad)


def test_parse_judge_response_rejects_non_integer_score() -> None:
    bad = json.dumps(
        {
            "cell_accuracy": {"score": "high", "rationale": "x"},
            "completeness": {"score": 4, "rationale": "x"},
            "confidence_honesty": {"score": 5, "rationale": "x"},
        }
    )
    with pytest.raises(judge.JudgeParseError):
        judge.parse_judge_response(bad)


def test_parse_judge_response_rejects_braced_but_invalid_json() -> None:
    # Has braces (so extraction triggers) but is not valid JSON.
    with pytest.raises(judge.JudgeParseError):
        judge.parse_judge_response("{not: valid, json}")


def test_judge_scores_as_dict_round_trips_scores_and_rationales() -> None:
    scores = judge.parse_judge_response(_VALID_JUDGE_JSON)
    payload = scores.as_dict()
    assert set(payload) == set(judge.RUBRIC_METRICS)
    assert payload["cell_accuracy"]["score"] == 5
    assert payload["completeness"]["rationale"] == "All cells present."


# --- the judge call (mocked litellm; NVIDIA OpenAI-compatible route) ----------


async def test_judge_pair_routes_through_nvidia_and_parses() -> None:
    acompletion = AsyncMock(return_value=_judge_response(_VALID_JUDGE_JSON))
    with patch.object(judge.litellm, "acompletion", acompletion):
        scores = await judge.judge_pair(
            fixture=_FIXTURE,
            comparison=_COMPARISON,
            judge_model="qwen/qwen3.5-122b-a10b",
            api_key="nvapi-test",
        )
    assert scores.cell_accuracy.score == 5
    _, kwargs = acompletion.call_args
    # LiteLLM provider-prefixed judge model id, scoped key, reproducible temp 0,
    # and drop_params so unsupported params never reach NIM.
    assert kwargs["model"] == "nvidia_nim/qwen/qwen3.5-122b-a10b"
    assert kwargs["api_key"] == "nvapi-test"
    assert kwargs["temperature"] == 0
    assert kwargs["drop_params"] is True
    # AI-1: the rubric (system) precedes the untrusted content (user).
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][0]["content"] == judge.JUDGE_SYSTEM
    assert kwargs["messages"][1]["role"] == "user"


# --- self-preference guard (spec: judge != model-under-test) ------------------


def test_assert_judge_independent_allows_distinct_models() -> None:
    judge.assert_judge_independent("qwen/qwen3.5-122b-a10b", "claude-sonnet-4-6")


def test_assert_judge_independent_rejects_self_judging() -> None:
    with pytest.raises(ValueError, match="self-preference"):
        judge.assert_judge_independent(
            "qwen/qwen3.5-122b-a10b", "qwen/qwen3.5-122b-a10b"
        )


# --- config: judge model is configurable, not hardcoded in logic --------------


def test_judge_model_has_qwen_default() -> None:
    assert Settings().nvidia_judge_model == "qwen/qwen3.5-122b-a10b"


def test_judge_model_overridable_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_JUDGE_MODEL", "meta/llama-4-scout")
    assert Settings().nvidia_judge_model == "meta/llama-4-scout"
