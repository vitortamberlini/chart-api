import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.note import NoteCreate, NoteResponse
from app.services.note import NoteService
from app.services.patient import PatientService


class NoteUseCase:
    def __init__(
        self,
        patient_service: PatientService,
        note_service: NoteService,
    ) -> None:
        self._patient_service = patient_service
        self._note_service = note_service

    async def create(
        self,
        session: AsyncSession,
        patient_id: uuid.UUID,
        data: NoteCreate,
        source_filename: str | None = None,
    ) -> NoteResponse:
        await self._patient_service.get_by_id(session, patient_id)
        return await self._note_service.create(session, patient_id, data, source_filename)

    async def get_by_patient(
        self,
        session: AsyncSession,
        patient_id: uuid.UUID,
    ) -> list[NoteResponse]:
        await self._patient_service.get_by_id(session, patient_id)
        return await self._note_service.get_by_patient(session, patient_id)

    async def delete(
        self,
        session: AsyncSession,
        patient_id: uuid.UUID,
        note_id: uuid.UUID,
    ) -> None:
        await self._patient_service.get_by_id(session, patient_id)
        await self._note_service.delete(session, note_id)
