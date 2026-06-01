from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Unified Declarative Base for SQLAlchemy Models.
    Allows easy metadata collection for Alembic autogenerate migrations.
    """
    pass
