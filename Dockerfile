FROM python:3.10-slim

# ติดตั้งเครื่องมือพื้นฐานที่จำเป็นและปลอดภัยสำหรับระบบคลาวด์ฟรี
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# คัดลอกและติดตั้งไลบรารีระบบคำนวณและ AI
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# สั่งรันระบบ FastAPI เข้าสู่พอร์ตออนไลน์
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
