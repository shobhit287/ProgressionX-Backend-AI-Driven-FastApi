#warning use it only on dev environment

import asyncio

from db.database import engine
from db.base import Base
import db.init_models  # ensure models are registered

async def init_db(drop: bool = False):
    async with engine.begin() as conn:
        if drop:
            await conn.run_sync(Base.metadata.drop_all)

        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())