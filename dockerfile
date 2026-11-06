FROM python:3.10-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.10-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/
RUN useradd -m appuser && mkdir -p logs && chown appuser logs
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python -c 'from app import models, database; database.Base.metadata.create_all(database.engine)' && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]