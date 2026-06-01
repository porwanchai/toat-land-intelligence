# TOAT Land Intelligence & Spatial Analysis System — Backend

A production-grade Python FastAPI backend serving as the highly precise geospatial engine for the **TOAT Land Intelligence & Spatial Analysis System**. 

The system replaces hardcoded planning assumptions with live, high-precision PostGIS spatial intersections, mathematical zoning capacity modeling, and AI-driven urban development evaluation utilizing the Google Gemini API.

---

## 🛠 Technology Stack
- **FastAPI 0.115+** — Asynchronous web framework.
- **PostgreSQL 16 + PostGIS 3.4** — Spatial database engine.
- **SQLAlchemy 2.0 (Async) + GeoAlchemy2** — Spatial Object Relational Mapping.
- **GeoPandas 1.x + Shapely 2.x** — Geospatial ETL and projection transformations.
- **Google Gemini API (google-genai SDK)** — High-precision AI analysis reports.
- **Celery 5.x + Redis 7** — Asynchronous background queueing for heavy Shapefile parsing.
- **WeasyPrint** — Elegant HTML-to-PDF compilation supporting Thai typography.
- **Alembic** — Spatial database migration management.

---

## 🏗 System Architecture

The backend consists of **7 core modules**:
1. **Data Ingestion Pipeline** — Accept official Ministerial Zoning Zip files, reprojects dataset coordinates using GeoPandas, and bulk inserts features as PostGIS geometries.
2. **Precision Geospatial Analysis Engine** — Intersection plot boundaries sent from frontend, computing zone coverages and exact areas using PostGIS `ST_Intersects`.
3. **AI Zoning Impact Analyzer** — Prompts Google Gemini to produce structured feasibility analysis briefs using Pydantic JSON schemas.
4. **FAR/OSR Construction Calculator** — Computes structural gross floor area capacities.
5. **Setback & Road Buffer Analyzer** — Deduce inward construction setbacks and buildable polygon boundaries using PostGIS `ST_Buffer` difference.
6. **Historical Zoning Change Tracker** — Timeline difference tracking of administrative changes over different fiscal years.
7. **PDF Report Generator** — Synthesis of calculations compiled into printable styled reports.

---

## 🚀 Quick Start Guide

### 1. Setup Environment
Copy the environment template and customize your settings (ensure you add your Gemini API Key):
```bash
cp .env.example .env
```

### 2. Startup Containers
Spin up the PostgreSQL/PostGIS database, Redis broker, FastAPI application server, Celery worker, and Celery Flower monitoring dashboard via Docker Compose:
```bash
docker-compose up --build -d
```

Verify service health:
```bash
curl http://localhost:8000/health
```
Should return: `{"status":"healthy","database":"connected",...}`

### 3. Run Migrations
Generate all PostGIS-enabled database tables and spatial indexes inside the container:
```bash
docker-compose exec api alembic upgrade head
```

---

## 📍 API Reference Endpoint Testing

Explore full interactive Swagger UI documentation at: `http://localhost:8000/docs`

### 1. Data Ingestion
Upload town zoning maps containing official Shapefiles (`.shp`, `.dbf`, `.shx`) or GeoJSON zip archives:
```bash
curl -X POST "http://localhost:8000/api/v1/zoning/upload-map" \
  -F "file=@bangkok_zoning_layers.zip" \
  -F "published_fiscal_year=2569"
```
*If map zip file > 10MB, the system returns a background `job_id` supporting status polling.*

### 2. Plot Creation
Register a target land plot boundary coordinates:
```bash
curl -X POST "http://localhost:8000/api/v1/plots/" \
  -H "Content-Type: application/json" \
  -d '{
    "plot_name": "Sukhumvit Plot 21",
    "address_text": "Asoke, Bangkok",
    "boundary": [
      [13.7381, 100.5601],
      [13.7385, 100.5601],
      [13.7385, 100.5605],
      [13.7381, 100.5605]
    ]
  }'
```

### 3. Precision Spatial Audit
Trigger Automated PostGIS intersections:
```bash
curl -X POST "http://localhost:8000/api/v1/plots/spatial-audit/1"
```

### 4. AI Zoning Assessment
Request structured feasibility briefs from Google Gemini:
```bash
curl -X POST "http://localhost:8000/api/v1/ai/analyze-zoning-impact" \
  -H "Content-Type: application/json" \
  -d '{
    "plot_id": 1,
    "proposed_development_type": "Luxury High-rise Hotel"
  }'
```

### 5. PDF Feasibility Report
Download elegant A4 styled print summaries:
```bash
open "http://localhost:8000/api/v1/reports/generate/1?proposed_development_type=Luxury+Hotel"
```
