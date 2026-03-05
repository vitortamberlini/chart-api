import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.summary import SummaryResponse
from app.services.llm import LLMService
from app.services.note import NoteService
from app.services.patient import PatientService


class SummaryUseCase:
    def __init__(
        self,
        patient_service: PatientService,
        note_service: NoteService,
        llm_service: LLMService,
    ) -> None:
        self._patient_service = patient_service
        self._note_service = note_service
        self._llm_service = llm_service

    async def generate(
        self,
        session: AsyncSession,
        patient_id: uuid.UUID,
        audience: str,
        verbosity: str,
    ) -> SummaryResponse:
        patient = await self._patient_service.get_by_id(session, patient_id)
        notes = await self._note_service.get_by_patient(session, patient_id)
        return await self._llm_service.generate_summary(patient, notes, audience, verbosity)
