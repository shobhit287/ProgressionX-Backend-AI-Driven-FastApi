from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={
        "statement_cache_size": 0, 
        # "ssl": True                
    },
    pool_pre_ping=True,          
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)