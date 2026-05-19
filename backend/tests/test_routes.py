"""Automated eval / route tests for FastAPI routes (PID Domain 2, PIS-09).

Eval 4 — edge case: incomplete TCO input must not generate a model (Phase 3).
Eval 7 — edge case: vague advisor input must request project context first.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Message


@pytest.mark.skip(reason="Eval 4 — incomplete TCO input: logic implemented in Phase 3")
def test_eval4_incomplete_tco_input_is_rejected() -> None:
    """PID Eval 4 — incomplete input edge case.

    Input: TCO form submitted with a device count but no hardware cost.

    Expected: the system prompts for the missing data and does NOT generate a
    model. Pass condition: zero TCO output produced; an error prompt is shown.
    Zero-tolerance: financial inputs are never silently assumed (PIS-04/PIS-10).
    """
    raise AssertionError("not implemented")


async def test_eval7_vague_advisor_input_requires_context(client: AsyncClient) -> None:
    """PID Eval 7 — vague advisor input edge case.

    Input: "what should I buy?" against a project with no context set.

    Expected: the system requests project context before answering — no
    generic vendor recommendation, and no model call is made.
    """
    project = (await client.post("/api/projects", json={"name": "Bare Project"})).json()

    resp = await client.post(
        f"/api/projects/{project['id']}/advisor",
        json={"message": "what should I buy?"},
    )

    assert resp.status_code == 200
    body = resp.text.lower()
    # The response asks for project context...
    assert "more about this project" in body
    # ...and does not name a vendor or give a recommendation.
    assert "cisco" not in body and "juniper" not in body


async def test_advisor_streams_response_and_persists(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A project with context streams an answer and persists both messages."""

    async def _fake_turn(history: object, context: object):
        yield "Frame it as "
        yield "a 5-year TCO."

    monkeypatch.setattr("app.routes.advisor.stream_advisor_turn", _fake_turn)

    project = (
        await client.post(
            "/api/projects",
            json={
                "name": "Campus Refresh",
                "description": "Replace 200 access points.",
                "existing_infra": "200 legacy APs on a Cisco WLC.",
            },
        )
    ).json()

    resp = await client.post(
        f"/api/projects/{project['id']}/advisor",
        json={"message": "How do I justify this to my CFO?"},
    )

    assert resp.status_code == 200
    body = resp.text
    # Both streamed tokens and a terminating done event are present.
    assert "Frame it as " in body
    assert "a 5-year TCO." in body
    assert '"type": "done"' in body

    # The user message and the assistant reply were both persisted (PIS-25).
    rows = (await db_session.execute(select(Message))).scalars().all()
    assert {m.role for m in rows} == {"user", "assistant"}
