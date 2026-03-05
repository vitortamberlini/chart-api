from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.notes import router as notes_router
from app.api.routes.patients import router as patients_router
from app.api.routes.summary import router as summary_router
from app.core.dependencies import get_db_session
from app.middleware.logging import LoggingMiddleware

app = FastAPI(title="Healthcare Data Processing API", version="0.1.0")

app.add_middleware(LoggingMiddleware)
app.include_router(patients_router)
app.include_router(notes_router)
app.include_router(summary_router)


@app.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
