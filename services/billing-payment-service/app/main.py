import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .database import engine
from .logging_config import setup_logging
from .routers import accounts, payments

setup_logging()
log = logging.getLogger("billing")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Billing & Payment Service started")
    yield


app = FastAPI(
    title="Billing & Payment Service",
    description="Лицевые счета, счета-фактуры и платежи «Умного города».",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("Unhandled error: %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Internal server error"}, status.HTTP_500_INTERNAL_SERVER_ERROR)
    log.info(
        "%s %s -> %s (%.1f ms)",
        request.method, request.url.path, response.status_code, (time.perf_counter() - started) * 1000,
    )
    return response


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError):
    log.exception("Database error: %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Database error"}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/health", tags=["system"])
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        log.exception("Health check failed")
        return JSONResponse({"status": "unavailable"}, status.HTTP_503_SERVICE_UNAVAILABLE)
    return {"status": "ok"}


app.include_router(accounts.router)
app.include_router(payments.router)
