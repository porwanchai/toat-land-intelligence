FROM python:3.10-slim

# ติดตั้งเครื่องมือคอมไพล์พื้นฐานที่จำเป็นและปลอดภัย
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

# กำหนดตัวแปรระบบเพื่อให้ Python ค้นหาโฟลเดอร์ภายในโปรเจกต์เจอ 100%
ENV PYTHONPATH=/app

# สั่งรันระบบผ่านคำสั่งมาตรฐานที่ทำงานร่วมกับระบบสภาพแวดล้อมได้ดีที่สุด
CMD ["python", "app/main.py"]
