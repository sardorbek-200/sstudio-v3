from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from shared.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI Depends uchun DB sessiyasi provayderi"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    """Asinxron konteks menejeri uchun DB sessiyasi"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db_schemas():
    """PostgreSQL dagi auth, quizer, shop, admin schemalari mavjudligini kafolatlaydi"""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS quizer;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS shop;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS admin;"))

