from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class ZoningChangeHistory(Base):
    __tablename__ = "zoning_change_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    layer_id: Mapped[int] = mapped_column(ForeignKey("urban_zoning_layers.id"), nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "created", "updated", "deleted"
    
    # Old vs New Values for comparison tracking
    old_far_limit: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    new_far_limit: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    old_osr_limit: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    new_osr_limit: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    
    old_zone_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    new_zone_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    changed_at: Mapped[datetime] = mapped_column(default=func.now())
    changed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    change_notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relationships
    layer = relationship("UrbanZoningLayer")
