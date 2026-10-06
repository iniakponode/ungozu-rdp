"""
Alembic entry point for model discovery.
Import Base and every model here so that Base.metadata contains all tables.
Never put business logic here.
"""
from app.db.base_class import Base  # noqa: F401 — re-exported for Alembic
import app.models  # noqa: F401 — side-effect: registers all mappers
