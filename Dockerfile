FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

# สั่งรันผ่านพอร์ต 10000 ซึ่งเป็นพอร์ตมาตรฐานสูงสุดของคลาวด์ Render 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
