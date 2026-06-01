from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Text, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class SpatialAuditLog(Base):
    __tablename__ = "spatial_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    plot_id: Mapped[int] = mapped_column(ForeignKey("land_plots.id"), nullable=False)
    audit_date: Mapped[datetime] = mapped_column(default=func.now())
    
    # Store JSON audit execution details
    intersection_results: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Metrics
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    audited_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Relationships
    plot = relationship("LandPlot", back_populates="audit_logs")
    audited_by = relationship("User")
