import pytest_asyncio

from app.core.config import get_settings
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.core.dependencies import get_db_session, get_llm_service
from app.db.models import Note, Patient  # noqa: F401 — register models with Base
from app.main import app
from app.schemas.patient import PatientResponse
from app.schemas.summary import SummaryResponse

_db_base = get_settings().DATABASE_URL.rsplit("/", 1)[0]
TEST_DB_URL = f"{_db_base}/chartapi_test"
ADMIN_DB_URL = f"{_db_base}/postgres"


class MockLLMService:
    async def classify_note(self, content: str) -> str:
        return "follow_up"

    async def generate_summary(
        self,
        patient: PatientResponse,
        notes: list,
        audience: str,
        verbosity: str,
    ) -> SummaryResponse:
        return SummaryResponse(
            patient=patient,
            summary="Mock clinical summary.",
            key_diagnoses=["Diagnosis A", "Diagnosis B"],
            current_medications=["Med A 10mg"],
            note_count=len(notes),
        )


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    admin_engine = create_async_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'chartapi_test'")
        )
        if not result.fetchone():
            await conn.execute(text("CREATE DATABASE chartapi_test"))
    await admin_engine.dispose()

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine):
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_db() -> AsyncSession:
        async with test_session_factory() as session:
            yield session

    def override_llm() -> MockLLMService:
        return MockLLMService()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_llm_service] = override_llm

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    async with test_session_factory() as session:
        await session.execute(text("DELETE FROM notes"))
        await session.execute(text("DELETE FROM patients"))
        await session.commit()

    app.dependency_overrides.clear()
