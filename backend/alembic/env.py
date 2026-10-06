"""
Alembic migration environment.
Uses asyncio + aiomysql for online migrations (same driver as the app).
Synchronous (offline) mode uses the pymysql URL from settings.
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Load app config and models ────────────────────────────────────────────────
from app.core.config import settings
import app.db.base  # noqa: F401 — registers all model mappers with Base.metadata
from app.db.base_class import Base

# Alembic Config object
config = context.config

# Wire in Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata


# ── URL helpers ───────────────────────────────────────────────────────────────

def _sync_url() -> str:
    """Return the synchronous pymysql URL (used for offline mode)."""
    return settings.DATABASE_URL


def _async_url() -> str:
    """Return the async aiomysql URL (used for online mode)."""
    return settings.async_database_url


# ── Offline mode ──────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Generate SQL scripts without a live DB connection."""
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online (async) mode ───────────────────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _async_url()

    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

