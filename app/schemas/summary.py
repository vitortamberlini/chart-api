from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.patient import PatientResponse


class PatientSummaryInfo(BaseModel):
    id: UUID
    name: str
    dob: str
    mrn: str


class SummaryResponse(BaseModel):
    patient: PatientResponse
    summary: str
    key_diagnoses: list[str]
    current_medications: list[str]
    note_count: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
