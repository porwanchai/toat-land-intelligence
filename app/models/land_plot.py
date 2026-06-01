from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.models.base import Base

class LandPlot(Base):
    __tablename__ = "land_plots"

    id: Mapped[int] = mapped_column(primary_key=True)
    plot_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Standard WGS84 boundary polygon for input plots
    geom = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True), 
        nullable=False
    )
    
    # Store dimensions
    total_area_sqm: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    address_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="plots")
    audit_logs = relationship("SpatialAuditLog", back_populates="plot")
