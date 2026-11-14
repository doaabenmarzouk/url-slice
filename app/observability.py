import os
import sys
import time

from fastapi import FastAPI, Request
from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_fastapi_instrumentator import Instrumentator

SKIP = ("/healthz", "/ready", "/metrics")


def setup_logging():
    """Logs JSON sur stdout."""
    logger.remove()
    logger.add(sys.stdout, serialize=True, level="INFO")


def setup_tracing():
    """Traces OpenTelemetry : console + Jaeger si OTEL_EXPORTER_OTLP_ENDPOINT existe."""
    provider = TracerProvider(resource=Resource.create({"service.name": "url-slice"}))
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint + "/v1/traces"))
        )
    trace.set_tracer_provider(provider)


def setup_observability(app: FastAPI):
    """À appeler une fois, juste après la création de l'app."""
    setup_logging()
    setup_tracing()

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled error on {}", request.url.path)
            raise
        if request.url.path not in SKIP:
            ctx = trace.get_current_span().get_span_context()
            logger.bind(
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
                trace_id=format(ctx.trace_id, "032x"),
            ).info("request")
        return response

    FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz,ready,metrics")
    Instrumentator(excluded_handlers=list(SKIP)).instrument(app).expose(
        app, include_in_schema=False
    )