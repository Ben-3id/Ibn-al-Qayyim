FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a directory for sqlite volume
# Fly/Render options: we will mount a volume to /data
ENV DATA_DIR=/data
# Render requires an exposed port for Web Services
EXPOSE 8080

CMD ["python", "main.py"]
