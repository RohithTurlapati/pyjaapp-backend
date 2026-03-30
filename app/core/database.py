from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# In production this might come from RDS dynamically, so ensure correct format
# e.g., using postgresql+asyncpg instead of raw postgresql format.
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Supabase enforces SSL for its connection pooler
if (
    ("supabase.com" in db_url or "pooler.supabase" in db_url)
    and "ssl=" not in db_url
    and "sslmode=" not in db_url
):
    joiner = "&" if "?" in db_url else "?"
    db_url += f"{joiner}ssl=require"


engine = create_async_engine(
    db_url, echo=False, poolclass=NullPool, connect_args={"statement_cache_size": 0}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
