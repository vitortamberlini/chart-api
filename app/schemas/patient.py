from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    name: str
    dob: date


class PatientUpdate(BaseModel):
    name: str | None = None
    dob: date | None = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    dob: date
    mrn: str
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class PaginatedPatients(BaseModel):
    items: list[PatientResponse]
    total: int
    page: int
    per_page: int
