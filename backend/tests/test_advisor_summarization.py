"""PIS-16 — advisor history summarization tests."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.user import User
from app.services import conversation_service


async def test_no_summary_below_threshold(
    db_session: AsyncSession, auth_user: User
) -> None:
    project = Project(name="Short", owner_id=auth_user.id)
    db_session.add(project)
    await db_session.commit()

    conversation = await conversation_service.create_conversation(
        db_session, project.id
    )
    for i in range(5):
        await conversation_service.add_message(
            db_session, conversation.id, "user", f"q{i}"
        )

    await conversation_service.maybe_summarize_history(db_session, conversation.id)
    conv = await conversation_service.get_conversation(db_session, conversation.id)
    assert conv is not None
    assert conv.summary is None
    # Nothing was trimmed.
    messages = await conversation_service.list_messages(db_session, conversation.id)
    assert len(messages) == 5


async def test_summary_created_and_oldest_trimmed_at_threshold(
    db_session: AsyncSession, auth_user: User
) -> None:
    project = Project(name="Long", owner_id=auth_user.id)
    db_session.add(project)
    await db_session.commit()

    conversation = await conversation_service.create_conversation(
        db_session, project.id
    )
    for i in range(15):
        await conversation_service.add_message(
            db_session, conversation.id, "user", f"q{i:02d}"
        )

    await conversation_service.maybe_summarize_history(db_session, conversation.id)
    conv = await conversation_service.get_conversation(db_session, conversation.id)
    assert conv is not None
    assert conv.summary is not None
    # The 10 oldest messages survive in the summary, not as rows.
    messages = await conversation_service.list_messages(db_session, conversation.id)
    assert len(messages) == 5
    # The summary references at least one of the trimmed messages.
    assert "q00" in conv.summary
    assert "q09" in conv.summary
    # The most-recent ones stay live.
    assert "q14" not in conv.summary
