from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from app.models.base import Base

class UrbanZoningLayer(Base):
    __tablename__ = "urban_zoning_layers"

    id: Mapped[int] = mapped_column(primary_key=True)
    zoning_color_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    zone_type_name: Mapped[str] = mapped_column(String(255), nullable=False)
    far_limit: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    osr_limit: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    construction_restrictions_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Store geometry as WGS84 (SRID: 4326) MultiPolygon for seamless Mapbox/Leaflet rendering
    # spatial_index=True automatically maps to GIST index
    geom = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=True), 
        nullable=False
    )
    
    source_filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(default=func.now())
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    version_number: Mapped[int] = mapped_column(default=1)
