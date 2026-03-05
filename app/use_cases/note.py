import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.note import NoteCreate, NoteResponse
from app.services.llm import LLMService
from app.services.note import NoteService
from app.services.patient import PatientService


class NoteUseCase:
    def __init__(
        self,
        patient_service: PatientService,
        note_service: NoteService,
        llm_service: LLMService,
    ) -> None:
        self._patient_service = patient_service
        self._note_service = note_service
        self._llm_service = llm_service

    async def create(
        self,
        session: AsyncSession,
        patient_id: uuid.UUID,
        data: NoteCreate,
        source_filename: str | None = None,
    ) -> NoteResponse:
        await self._patient_service.get_by_id(session, patient_id)
        note = await self._note_service.create(session, patient_id, data, source_filename)
        note_type = await self._llm_service.classify_note(note.content)
        await self._note_service.update_note_type(session, note.id, note_type)
        return note.model_copy(update={"note_type": note_type})

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
