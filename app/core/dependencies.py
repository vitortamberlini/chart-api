from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.db import create_session_factory


def get_session_factory(
    settings: Settings = Depends(get_settings),
) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(settings)


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
