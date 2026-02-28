import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from core.config import settings
from db.base import Base
from db import init_models  # ensure models are imported for autogenerate


# -----------------------------------------------------
# Alembic Config
# -----------------------------------------------------

config = context.config

# Override DB URL from application settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Setup Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


# -----------------------------------------------------
# Offline Migrations
# -----------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# -----------------------------------------------------
# Online Migrations (Async)
# -----------------------------------------------------

def run_migrations_online() -> None:
    """Run migrations in 'online' mode using async engine."""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def do_run_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(run_migrations)

        await connectable.dispose()

    asyncio.run(do_run_migrations())


def run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# -----------------------------------------------------
# Entry Point
# -----------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()