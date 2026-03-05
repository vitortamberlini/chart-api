import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.dependencies import get_db_session, get_note_use_case
from app.schemas.note import NoteCreate, NoteResponse
from app.use_cases.note import NoteUseCase

router = APIRouter(prefix="/patients/{patient_id}/notes", tags=["notes"])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    patient_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    use_case: NoteUseCase = Depends(get_note_use_case),
) -> NoteResponse:
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if file is None:
            raise HTTPException(status_code=422, detail="'file' field is required for multipart upload")
        content = (await file.read()).decode("utf-8")
        raw_taken_at = form.get("taken_at") or request.query_params.get("taken_at")
        taken_at = datetime.fromisoformat(raw_taken_at) if raw_taken_at else datetime.now(timezone.utc)
        note_data = NoteCreate(content=content, taken_at=taken_at)
        return await use_case.create(session, patient_id, note_data, source_filename=file.filename)

    body = await request.json()
    note_data = NoteCreate(**body)
    return await use_case.create(session, patient_id, note_data)


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    patient_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    use_case: NoteUseCase = Depends(get_note_use_case),
) -> list[NoteResponse]:
    return await use_case.get_by_patient(session, patient_id)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    patient_id: uuid.UUID,
    note_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    use_case: NoteUseCase = Depends(get_note_use_case),
) -> None:
    await use_case.delete(session, patient_id, note_id)
