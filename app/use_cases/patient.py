import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.patient import (
    PaginatedPatients,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient import PatientService


class PatientUseCase:
    def __init__(self, service: PatientService) -> None:
        self._service = service

    async def get_by_id(self, session: AsyncSession, patient_id: uuid.UUID) -> PatientResponse:
        return await self._service.get_by_id(session, patient_id)

    async def get_all(
        self,
        session: AsyncSession,
        page: int,
        per_page: int,
        sort_by: str,
        order: str,
        search: str | None,
    ) -> PaginatedPatients:
        items, total = await self._service.get_all(session, page, per_page, sort_by, order, search)
        return PaginatedPatients(items=items, total=total, page=page, per_page=per_page)

    async def create(self, session: AsyncSession, data: PatientCreate) -> PatientResponse:
        return await self._service.create(session, data)

    async def update(
        self, session: AsyncSession, patient_id: uuid.UUID, data: PatientUpdate
    ) -> PatientResponse:
        return await self._service.update(session, patient_id, data)

    async def delete(self, session: AsyncSession, patient_id: uuid.UUID) -> None:
        return await self._service.delete(session, patient_id)
