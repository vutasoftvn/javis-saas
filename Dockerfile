FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app/ ./app/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head 2>/dev/null || true; uvicorn app.main:app --host 0.0.0.0 --port 8000"]

