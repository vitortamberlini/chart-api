import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.patient import PatientRepository
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate


class PatientService:
    def __init__(self, repository: PatientRepository) -> None:
        self._repo = repository

    async def get_by_id(
        self,
        session: AsyncSession,
        patient_id: uuid.UUID,
    ) -> PatientResponse:
        patient = await self._repo.get_by_id(session, patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
        return patient

    async def get_all(
        self,
        session: AsyncSession,
        page: int,
        per_page: int,
        sort_by: str,
        order: str,
        search: str | None,
    ) -> tuple[list[PatientResponse], int]:
        return await self._repo.get_all(session, page, per_page, sort_by, order, search)

    async def create(self, session: AsyncSession, data: PatientCreate) -> PatientResponse:
        return await self._repo.create(session, data)

    async def update(
        self,
        session: AsyncSession,
        patient_id: uuid.UUID,
        data: PatientUpdate,
    ) -> PatientResponse:
        patient = await self._repo.update(session, patient_id, data)
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
        return patient

    async def delete(self, session: AsyncSession, patient_id: uuid.UUID) -> None:
        deleted = await self._repo.delete(session, patient_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
