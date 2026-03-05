import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.dependencies import get_db_session, get_patient_use_case
from app.schemas.patient import (
    PaginatedPatients,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.use_cases.patient import PatientUseCase

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=PaginatedPatients)
async def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("name", pattern="^(name|created_at|dob)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> PaginatedPatients:
    return await use_case.get_all(session, page, per_page, sort_by, order, search)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> PatientResponse:
    return await use_case.get_by_id(session, patient_id)


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    data: PatientCreate,
    session: AsyncSession = Depends(get_db_session),
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> PatientResponse:
    return await use_case.create(session, data)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: uuid.UUID,
    data: PatientUpdate,
    session: AsyncSession = Depends(get_db_session),
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> PatientResponse:
    return await use_case.update(session, patient_id, data)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> None:
    await use_case.delete(session, patient_id)
