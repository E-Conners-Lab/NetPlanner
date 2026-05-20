"""Integration tests for the conversation persistence service (PIS-25)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.services import conversation_service


async def _make_project(db: AsyncSession) -> Project:
    project = Project(name="Advisor Test Project")
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def test_create_conversation(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)

    conversation = await conversation_service.create_conversation(
        db_session, project.id, title="Vendor justification"
    )

    assert conversation.id
    assert conversation.project_id == project.id
    assert conversation.title == "Vendor justification"


async def test_get_conversation_found_and_missing(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    created = await conversation_service.create_conversation(db_session, project.id)

    fetched = await conversation_service.get_conversation(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id

    assert await conversation_service.get_conversation(db_session, "missing") is None


async def test_add_and_list_messages_in_order(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    conversation = await conversation_service.create_conversation(
        db_session, project.id
    )

    await conversation_service.add_message(
        db_session, conversation.id, "user", "How do I justify MIST to my CFO?"
    )
    await conversation_service.add_message(
        db_session, conversation.id, "assistant", "Frame it as a 5-year TCO..."
    )

    messages = await conversation_service.list_messages(db_session, conversation.id)
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content.startswith("How do I justify")


async def test_list_messages_empty_for_new_conversation(
    db_session: AsyncSession,
) -> None:
    project = await _make_project(db_session)
    conversation = await conversation_service.create_conversation(
        db_session, project.id
    )

    assert await conversation_service.list_messages(db_session, conversation.id) == []


async def test_list_conversations(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    await conversation_service.create_conversation(db_session, project.id, "First")
    await conversation_service.create_conversation(db_session, project.id, "Second")

    conversations = await conversation_service.list_conversations(
        db_session, project.id
    )
    assert {c.title for c in conversations} == {"First", "Second"}


def test_derive_title_short_message_returned_as_is() -> None:
    assert (
        conversation_service.derive_title_from_message("What's the 5-year TCO?")
        == "What's the 5-year TCO?"
    )


def test_derive_title_first_sentence_when_within_budget() -> None:
    msg = "Compare Cisco and Arista. Then walk me through the TCO."
    assert (
        conversation_service.derive_title_from_message(msg)
        == "Compare Cisco and Arista"
    )


def test_derive_title_truncates_long_message_at_word_boundary() -> None:
    msg = (
        "Walk me through a refresh plan for a manufacturing access "
        "layer with three sites and a strict budget ceiling"
    )
    title = conversation_service.derive_title_from_message(msg)
    assert len(title) <= 61  # 60 chars + ellipsis
    assert title.endswith("…")
    # Truncates on a word boundary — does not slice a word in half.
    assert not title.replace("…", "").endswith(" ")
    assert title.replace("…", "").split(" ")[-1] in msg.split(" ")


def test_derive_title_empty_message_falls_back() -> None:
    assert (
        conversation_service.derive_title_from_message("   ") == "Untitled conversation"
    )
