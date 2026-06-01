FROM python:3.10-slim

WORKDIR /app

# คัดลอกและติดตั้งไลบรารีชุดเบาพิเศษ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกไฟล์ทั้งหมดเข้าสู่ตู้ระบบ
COPY . .

# สั่งให้ระบบค้นหาโฟลเดอร์ย่อย 'app' เจออย่างถูกต้องสากล
ENV PYTHONPATH=/app

# สั่งสตาร์ทเครื่องผ่าน Uvicorn แบบดั้งเดิม
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
