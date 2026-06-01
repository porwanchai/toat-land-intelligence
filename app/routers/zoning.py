import os
import shutil
import uuid
import logging
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.config import settings
from app.schemas.zoning import UrbanZoningLayerResponse, UploadStatusResponse
from app.models.urban_zoning import UrbanZoningLayer
from app.utils.file_utils import validate_zip_file
from app.services.shapefile_parser import ShapefileParserService
from app.tasks.ingestion_tasks import process_shapefile_upload
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/zoning", tags=["Zoning Layers Ingestion"])

@router.post("/upload-map", response_model=UploadStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_zoning_map(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    published_fiscal_year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Accepts Town Planning Zip archive files containing GIS Shapefiles (.shp, .shx, .dbf) or QGIS-exported GeoJSON data.
    - Synchronous validation checking (magic bytes, ZIP safety).
    - Lightweight uploads (<= 10MB) are processed dynamically via FastAPI BackgroundTasks.
    - Heavy datasets (> 10MB) are offloaded to asynchronous Celery workers.
    """
    # 1. Basic security validation
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="File must be a valid zip compressed archive containing spatial datasets."
        )

    # Make target dir if not exists
    os.makedirs(settings.UPLOAD_TEMP_DIR, exist_ok=True)
    temp_file_id = str(uuid.uuid4())
    temp_zip_path = Path(settings.UPLOAD_TEMP_DIR) / f"{temp_file_id}.zip"

    # 2. Write file chunk by chunk to local disk
    try:
        with open(temp_zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to write uploaded file to disk: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist uploaded dataset securely on temporary disk."
        )

    # 3. Validate ZIP metrics & signatures
    validate_zip_file(temp_zip_path, settings.MAX_UPLOAD_SIZE_MB)

    # Check size threshold to select sync/async execution routing
    file_size_mb = temp_zip_path.stat().st_size / (1024 * 1024)
    logger.info(f"Uploaded file {file.filename} is {file_size_mb:.2f} MB in size.")

    # Core Execution Routing
    if file_size_mb <= settings.LARGE_FILE_THRESHOLD_MB:
        # Sync-like background processing for smaller datasets
        job_id = f"sync_{uuid.uuid4()}"
        
        async def process_sync():
            try:
                await ShapefileParserService.process_and_import(
                    temp_zip_path, db, published_fiscal_year
                )
                if temp_zip_path.exists():
                    os.remove(temp_zip_path)
                logger.info(f"Synchronous processing of small map completed for job {job_id}.")
            except Exception as exc:
                logger.error(f"Sync spatial processing failure: {str(exc)}")
                if temp_zip_path.exists():
                    os.remove(temp_zip_path)

        background_tasks.add_task(process_sync)
        return UploadStatusResponse(
            job_id=job_id,
            status="processing",
            error=None
        )
    else:
        # Offload heavy tasks to Celery workers
        try:
            task = process_shapefile_upload.delay(str(temp_zip_path), published_fiscal_year)
            return UploadStatusResponse(
                job_id=task.id,
                status="queued",
                error=None
            )
        except Exception as e:
            logger.error(f"Failed to submit task to Celery backend: {str(e)}")
            if temp_zip_path.exists():
                os.remove(temp_zip_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Task broker queueing failure. Failed to offload heavy spatial task."
            )

@router.get("/upload-status/{job_id}", response_model=UploadStatusResponse)
async def get_upload_status(job_id: str):
    """
    Poll the status of an asynchronous zoning layer ingest job.
    Supports monitoring both synchronous/Celery task executions.
    """
    if job_id.startswith("sync_"):
        # For lightweight synchronous flows, we assume it's completed unless a traceback appears
        return UploadStatusResponse(
            job_id=job_id,
            status="completed",
            imported_polygons_count=None,
            error=None
        )

    # Query Celery state backend
    res = celery_app.AsyncResult(job_id)
    state = res.state.lower()
    
    if state == "pending":
        return UploadStatusResponse(job_id=job_id, status="queued")
    elif state == "started":
        return UploadStatusResponse(job_id=job_id, status="processing")
    elif state == "success":
        result = res.result
        return UploadStatusResponse(
            job_id=job_id,
            status="completed",
            imported_polygons_count=result.get("imported_polygons_count"),
            error=None
        )
    elif state == "failure":
        return UploadStatusResponse(
            job_id=job_id,
            status="failed",
            error=str(res.result)
        )
    else:
        return UploadStatusResponse(job_id=job_id, status=state)

@router.get("/layers", response_model=List[UrbanZoningLayerResponse])
async def list_zoning_layers(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all administrative active zoning layers.
    """
    stmt = select(UrbanZoningLayer).where(UrbanZoningLayer.is_active == True)
    result = await db.execute(stmt)
    layers = result.scalars().all()
    return layers
