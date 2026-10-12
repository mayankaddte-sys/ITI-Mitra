FROM python:3.11-slim
WORKDIR /app
# Optional OCR for scanned / legacy-font Hindi PDFs (remove if not needed)
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-ocr.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ocr.txt
COPY . .
EXPOSE 8000
# Mount a persistent volume at /app/vector_db and /app/uploads, otherwise they are lost on redeploy.
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
