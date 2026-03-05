import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.note import NoteRepository
from app.schemas.note import NoteCreate, NoteResponse


class NoteService:
    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository

    async def create(
        self,
        session: AsyncSession,
        patient_id: uuid.UUID,
        data: NoteCreate,
        source_filename: str | None = None,
    ) -> NoteResponse:
        return await self._repo.create(session, patient_id, data, source_filename)

    async def get_by_patient(
        self, session: AsyncSession, patient_id: uuid.UUID
    ) -> list[NoteResponse]:
        return await self._repo.get_by_patient(session, patient_id)

    async def delete(self, session: AsyncSession, note_id: uuid.UUID) -> None:
        deleted = await self._repo.delete(session, note_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
