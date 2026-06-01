FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies needed for PostgreSQL, GDAL, Shapely, WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgdal-dev \
    gdal-bin \
    python3-gdal \
    libmagic1 \
    netcat-openbsd \
    # WeasyPrint PDF dependencies (Pango, Cairo, etc.)
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    shared-mime-info \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Fonts
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create temporary upload directory
RUN mkdir -p /app/uploads && chmod 777 /app/uploads

# Copy application files
COPY . .

# Run start command dynamically binding to production port
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
