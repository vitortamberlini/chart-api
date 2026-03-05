from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NoteCreate(BaseModel):
    content: str
    taken_at: datetime


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    content: str
    note_type: str | None
    source_filename: str | None
    taken_at: datetime
    created_at: datetime
    deleted_at: datetime | None
