from fastapi import FastAPI
from loguru import logger

from app import routes
from app.observability import setup_observability

app = FastAPI(
    title="URL Slice",
    description="A simple and lightweight URL shortening service built with FastAPI.",
    version="1.0.0",
)

# Logs JSON + métriques /metrics + traces (avant les routes)
setup_observability(app)


@app.get("/")
def read_root():
    return {"message": "Welcome to the URL Slice API"}


# Kubernetes health checks (avant le router, qui a une route /{short_url})
@app.get("/healthz", include_in_schema=False)
def health_check():
    return {"status": "healthy"}


@app.get("/ready", include_in_schema=False)
def readiness_check():
    return {"status": "ready"}


# Include application routes (EN DERNIER)
app.include_router(routes.router)


@app.on_event("startup")
def startup_event():
    logger.info("Application started")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("Application shutting down")