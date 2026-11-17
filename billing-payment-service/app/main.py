import logging
import time

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import Base, engine
from app.logging_config import setup_logging
from app.routers import accounts, payments

setup_logging()
logger = logging.getLogger(settings.service_name)

app = FastAPI(
    title="Billing & Payment Service",
    description="Управление лицевыми счетами, счетами-фактурами и платежами в экосистеме «Умный город»",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Для учебного проекта таблицы создаются напрямую; в проде — через Alembic-миграции.
    Base.metadata.create_all(bind=engine)
    logger.info("%s запущен, таблицы БД проверены/созданы", settings.service_name)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1f ms)",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Ошибка валидации на %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Ошибка валидации входных данных", "errors": exc.errors()},
    )


@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Ошибка БД на %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервиса при работе с базой данных"},
    )


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "service": settings.service_name}


app.include_router(accounts.router)
app.include_router(payments.router)
