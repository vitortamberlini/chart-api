from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.db import create_session_factory
from app.repositories.patient import PatientRepository
from app.services.patient import PatientService
from app.use_cases.patient import PatientUseCase


def get_session_factory(
    settings: Settings = Depends(get_settings),
) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(settings)


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


def get_patient_repository() -> PatientRepository:
    return PatientRepository()


def get_patient_service(
    repository: PatientRepository = Depends(get_patient_repository),
) -> PatientService:
    return PatientService(repository)


def get_patient_use_case(
    service: PatientService = Depends(get_patient_service),
) -> PatientUseCase:
    return PatientUseCase(service)
