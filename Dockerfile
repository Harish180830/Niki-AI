# FastAPI backend image (includes Tesseract for OCR of scanned PDFs / images)
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py core.py doc_utils.py prompts.py ./

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:api --host 0.0.0.0 --port ${PORT}"]
