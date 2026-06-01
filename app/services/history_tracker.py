import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.urban_zoning import UrbanZoningLayer
from app.models.zoning_history import ZoningChangeHistory

logger = logging.getLogger(__name__)

class ZoningHistoryTrackerService:
    @staticmethod
    async def log_zoning_change(
        db: AsyncSession,
        layer_id: int,
        change_type: str,  # "created", "updated", "deleted"
        old_layer: Optional[UrbanZoningLayer],
        new_layer: Optional[UrbanZoningLayer],
        fiscal_year: int,
        changed_by: Optional[str] = "admin",
        change_notes: Optional[str] = None
    ) -> ZoningChangeHistory:
        """
        Calculates differences and registers detailed audit tracking metrics into zoning change history.
        """
        history_record = ZoningChangeHistory(
            layer_id=layer_id,
            change_type=change_type,
            
            old_far_limit=old_layer.far_limit if old_layer else None,
            new_far_limit=new_layer.far_limit if new_layer else None,
            
            old_osr_limit=old_layer.osr_limit if old_layer else None,
            new_osr_limit=new_layer.osr_limit if new_layer else None,
            
            old_zone_type=old_layer.zone_type_name if old_layer else None,
            new_zone_type=new_layer.zone_type_name if new_layer else None,
            
            changed_by=changed_by,
            fiscal_year=fiscal_year,
            change_notes=change_notes or f"Zoning layer {change_type} operation."
        )

        db.add(history_record)
        await db.commit()
        return history_record

    @staticmethod
    async def get_plot_historical_timeline(db: AsyncSession, plot_id: int) -> List[dict]:
        """
        Performs multi-year snapshot analysis of a specific plot.
        Queries the database to compare zoning changes historically affecting that plot.
        """
        # Fetch the plot geometry
        wkt_query = text("SELECT ST_AsText(geom) FROM land_plots WHERE id = :plot_id;")
        wkt_res = await db.execute(wkt_query, {"plot_id": plot_id})
        plot_wkt = wkt_res.scalar()
        if not plot_wkt:
            return []

        # Find all historical zoning layers (including de-active ones) intersecting the plot boundary,
        # sorted chronologically by published_fiscal_year.
        query = text("""
            SELECT 
                h.id,
                h.change_type,
                h.old_far_limit,
                h.new_far_limit,
                h.old_osr_limit,
                h.new_osr_limit,
                h.old_zone_type,
                h.new_zone_type,
                h.changed_at,
                h.fiscal_year,
                h.change_notes,
                uzl.zoning_color_code
            FROM zoning_change_history h
            JOIN urban_zoning_layers uzl ON h.layer_id = uzl.id
            WHERE ST_Intersects(
                uzl.geom,
                ST_GeomFromText(:plot_wkt, 4326)
            )
            ORDER BY h.changed_at DESC;
        """)

        result = await db.execute(query, {"plot_wkt": plot_wkt})
        rows = result.fetchall()

        timeline = []
        for r in rows:
            timeline.append({
                "history_id": r.id,
                "zoning_color_code": r.zoning_color_code,
                "change_type": r.change_type,
                "old_far": float(r.old_far_limit) if r.old_far_limit is not None else None,
                "new_far": float(r.new_far_limit) if r.new_far_limit is not None else None,
                "old_osr": float(r.old_osr_limit) if r.old_osr_limit is not None else None,
                "new_osr": float(r.new_osr_limit) if r.new_osr_limit is not None else None,
                "old_zone_type": r.old_zone_type,
                "new_zone_type": r.new_zone_type,
                "changed_at": r.changed_at.isoformat(),
                "fiscal_year": r.fiscal_year,
                "change_notes": r.change_notes
            })
        return timeline
