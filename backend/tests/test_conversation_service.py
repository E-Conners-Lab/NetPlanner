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
