FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY data-demo ./data-demo
COPY alembic.ini .
COPY migrations ./migrations

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "python -m app.services.migrate && python -m app.services.seed && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
