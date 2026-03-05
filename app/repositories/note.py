import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Note
from app.schemas.note import NoteCreate, NoteResponse


class NoteRepository:
    async def create(
        self,
        session: AsyncSession,
        patient_id: uuid.UUID,
        data: NoteCreate,
        source_filename: str | None = None,
    ) -> NoteResponse:
        note = Note(
            id=uuid.uuid4(),
            patient_id=patient_id,
            content=data.content,
            taken_at=data.taken_at,
            source_filename=source_filename,
        )
        session.add(note)
        await session.commit()
        await session.refresh(note)
        return NoteResponse.model_validate(note)

    async def get_by_patient(
        self, session: AsyncSession, patient_id: uuid.UUID
    ) -> list[NoteResponse]:
        result = await session.execute(
            select(Note)
            .where(
                Note.patient_id == patient_id,
                Note.deleted_at.is_(None),
            )
            .order_by(Note.taken_at.asc())
        )
        return [NoteResponse.model_validate(note) for note in result.scalars().all()]

    async def get_by_id(
        self, session: AsyncSession, note_id: uuid.UUID
    ) -> NoteResponse | None:
        result = await session.execute(
            select(Note).where(
                Note.id == note_id,
                Note.deleted_at.is_(None)
            )
        )
        row = result.scalar_one_or_none()
        return NoteResponse.model_validate(row) if row else None

    async def delete(self, session: AsyncSession, note_id: uuid.UUID) -> bool:
        result = await session.execute(
            select(Note).where(
                Note.id == note_id,
                Note.deleted_at.is_(None),
            )
        )
        note = result.scalar_one_or_none()
        if not note:
            return False
        note.deleted_at = datetime.now(timezone.utc)
        await session.commit()
        return True

    async def update_note_type(
        self, session: AsyncSession, note_id: uuid.UUID, note_type: str
    ) -> None:
        result = await session.execute(
            select(Note).where(Note.id == note_id)
        )
        note = result.scalar_one_or_none()
        if note:
            note.note_type = note_type
            await session.commit()
