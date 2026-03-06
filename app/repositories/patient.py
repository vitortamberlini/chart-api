import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Patient
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate


class PatientRepository:
    async def get_by_id(self, session: AsyncSession, id: uuid.UUID) -> PatientResponse | None:
        result = await session.execute(
            select(Patient).where(
                Patient.id == id,
                Patient.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        return PatientResponse.model_validate(row) if row else None

    async def get_all(
        self,
        session: AsyncSession,
        page: int,
        per_page: int,
        sort_by: str,
        order: str,
        search: str | None,
    ) -> tuple[list[PatientResponse], int]:
        query = select(Patient).where(Patient.deleted_at.is_(None))

        if search:
            query = query.where(Patient.name.ilike(f"%{search}%"))

        count_result = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        sort_col = getattr(Patient, sort_by, Patient.name)
        query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await session.execute(query)
        rows = result.scalars().all()
        return [PatientResponse.model_validate(r) for r in rows], total

    async def create(self, session: AsyncSession, data: PatientCreate) -> PatientResponse:
        patient = Patient(
            id=uuid.uuid4(),
            name=data.name,
            dob=data.dob,
            mrn=f"MRN-{uuid.uuid4().hex[:6].upper()}",
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        return PatientResponse.model_validate(patient)

    async def update(
        self, session: AsyncSession, id: uuid.UUID, data: PatientUpdate
    ) -> PatientResponse | None:
        result = await session.execute(
            select(Patient).where(
                Patient.id == id,
                Patient.deleted_at.is_(None),
            )
        )
        patient = result.scalar_one_or_none()
        if not patient:
            return None

        if data.name is not None:
            patient.name = data.name
        if data.dob is not None:
            patient.dob = data.dob
        patient.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(patient)
        return PatientResponse.model_validate(patient)

    async def delete(self, session: AsyncSession, id: uuid.UUID) -> bool:
        result = await session.execute(
            select(Patient).where(
                Patient.id == id,
                Patient.deleted_at.is_(None),
            )
        )
        patient = result.scalar_one_or_none()
        if not patient:
            return False

        patient.deleted_at = datetime.now(timezone.utc)
        await session.commit()
        return True
