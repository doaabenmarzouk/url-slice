FROM python:3.10-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.10-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Correctif Debian (alerte apt) : mise à jour des paquets système
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY app/ ./app/

# Correctif setuptools/wheel (copies internes vulnérables), inutiles à l'exécution
RUN pip uninstall -y setuptools wheel

RUN useradd -m appuser && mkdir -p logs && chown appuser logs
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python -c 'from app import models, database; database.Base.metadata.create_all(database.engine)' && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]