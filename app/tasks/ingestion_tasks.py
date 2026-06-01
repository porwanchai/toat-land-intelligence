import os
import asyncio
import logging
from pathlib import Path
from celery import shared_task
from app.database import async_session_factory
from app.services.shapefile_parser import ShapefileParserService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_shapefile_upload(self, file_path_str: str, published_fiscal_year: int) -> dict:
    """
    Background worker task to extract, parse, reproject and upload Shapefile/GeoJSON GIS layers asynchronously.
    """
    logger.info(f"Background shapefile processing started for: {file_path_str}")
    file_path = Path(file_path_str)

    if not file_path.exists():
        logger.error(f"Upload file {file_path_str} was not found.")
        return {"status": "failed", "error": "File not found on local disk storage."}

    # Setup standard event loop for running database transactions inside sync Celery context
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def run_import():
        async with async_session_factory() as session:
            try:
                records_count = await ShapefileParserService.process_and_import(
                    file_path, session, published_fiscal_year
                )
                return records_count
            except Exception as e:
                logger.error(f"Import process failed: {str(e)}")
                raise e

    try:
        inserted = loop.run_until_complete(run_import())
        
        # Cleanup temporary uploaded zip file from disk
        if file_path.exists():
            os.remove(file_path)
            
        return {
            "status": "completed",
            "imported_polygons_count": inserted,
            "filename": file_path.name
        }
        
    except Exception as exc:
        logger.exception("Error processing zoning layer upload.")
        # Retries task on transient failures
        try:
            self.retry(exc=exc)
        except Exception as retry_exc:
            return {
                "status": "failed",
                "error": str(exc),
                "retry_limit_reached": True
            }
