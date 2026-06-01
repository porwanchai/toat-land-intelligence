from celery import Celery
from app.config import settings

# Initialize Celery app mapping brokers and backends to Redis database connections
celery_app = Celery(
    "toat_spatial_worker",
    broker=settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Standard Configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Bangkok",
    enable_utc=True,
    worker_concurrency=2,     # Limit resource contention with heavy CPU-bound GDAL tasks
    task_track_started=True,
)

# Discover tasks
celery_app.autodiscover_tasks(["app.tasks"])
