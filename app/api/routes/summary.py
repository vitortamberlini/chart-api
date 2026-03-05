import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_summary_use_case
from app.schemas.summary import SummaryResponse
from app.use_cases.summary import SummaryUseCase

router = APIRouter(tags=["summary"])


@router.get("/patients/{patient_id}/summary", response_model=SummaryResponse)
async def get_summary(
    patient_id: uuid.UUID,
    audience: str = Query("clinician", pattern="^(clinician|family)$"),
    verbosity: str = Query("standard", pattern="^(brief|standard|detailed)$"),
    session: AsyncSession = Depends(get_db_session),
    use_case: SummaryUseCase = Depends(get_summary_use_case),
) -> SummaryResponse:
    return await use_case.generate(session, patient_id, audience, verbosity)
