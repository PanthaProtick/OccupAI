from __future__ import annotations

import logging
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import Settings
from backend.models import (
    CollectionMeta,
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    HistoryMeta,
    HistoryMetric,
    HistoryRange,
    HistoryResponse,
    OccupancyListResponse,
    OccupancyResponse,
    RoomResponse,
    RoomsResponse,
)
from backend.database import create_database_engine, make_session_factory
from backend.ingestion import ModelServerIngestionAdapter, ModelServerIngestionService, SerializedDatabaseWriter
from backend.maintenance import DatabaseMaintenanceService
from backend.repositories import DatabaseOccupancyRepository, MockOccupancyRepository, OccupancyRepository


logger = logging.getLogger(__name__)


def _log(event: str, level: int = logging.INFO, **fields: Any) -> None:
    logger.log(level, json.dumps({"event": event, **fields}, sort_keys=True, default=str))


def _error(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    payload = ErrorResponse(error=ErrorBody(code=code, message=message, details=details or {}))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers={"X-OccupAI-Error-Envelope": "1"},
    )


def _build_repository(settings: Settings) -> OccupancyRepository:
    if settings.data_source == "mock":
        return MockOccupancyRepository(settings.mock_data_dir)
    if settings.data_source == "database":
        engine = create_database_engine(settings.database_url, settings.sqlite_busy_timeout_ms)
        required = {
            "rooms", "cameras", "camera_states", "occupancy_samples",
            "occupancy_buckets_5m", "ingestion_receipts",
        }
        try:
            missing = required - set(inspect(engine).get_table_names())
        except Exception as exc:
            engine.dispose()
            raise RuntimeError("Database is unavailable; verify DATABASE_URL and permissions") from exc
        if missing:
            engine.dispose()
            raise RuntimeError(f"Database schema is not migrated; missing tables: {', '.join(sorted(missing))}")
        repository = DatabaseOccupancyRepository(make_session_factory(engine))
        repository.engine = engine
        return repository
    raise RuntimeError(f"Unsupported DATA_SOURCE={settings.data_source!r}")


def create_app(
    settings: Settings | None = None,
    repository: OccupancyRepository | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
    active_repository = repository or _build_repository(active_settings)
    ingestion_service: ModelServerIngestionService | None = None
    maintenance_service: DatabaseMaintenanceService | None = None
    if active_settings.ingestion_enabled:
        session_factory = getattr(active_repository, "session_factory", None)
        if session_factory is None:
            raise RuntimeError("Ingestion requires DatabaseOccupancyRepository")
        writer = SerializedDatabaseWriter(session_factory, active_settings.raw_sample_interval_seconds)
        adapter = ModelServerIngestionAdapter(
            active_settings.model_server_url, writer, active_settings.model_server_timeout_seconds,
        )
        ingestion_service = ModelServerIngestionService(
            adapter, writer, active_settings.live_camera_ids,
            active_settings.model_server_poll_interval_seconds,
        )
    if active_settings.maintenance_enabled:
        session_factory = getattr(active_repository, "session_factory", None)
        if session_factory is None:
            raise RuntimeError("Maintenance requires DatabaseOccupancyRepository")
        expected_samples = round(300 / active_settings.raw_sample_interval_seconds)
        maintenance_service = DatabaseMaintenanceService(
            session_factory,
            active_settings.raw_sample_retention_days,
            active_settings.aggregate_retention_days,
            active_settings.retention_batch_size,
            expected_samples,
            active_settings.maintenance_interval_seconds,
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        _log("backend_startup", **active_settings.safe_summary())
        if ingestion_service:
            ingestion_service.start()
        if maintenance_service:
            maintenance_service.start()
        yield
        if maintenance_service:
            maintenance_service.stop()
        if ingestion_service:
            ingestion_service.stop()
        close = getattr(active_repository, "close", None)
        if close:
            close()
        engine = getattr(active_repository, "engine", None)
        if engine:
            engine.dispose()

    app = FastAPI(
        title="OccupAI Product API",
        version="0.1.0",
        description="Stable frontend-facing occupancy API with a replaceable data repository.",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.repository = active_repository
    app.state.ingestion_service = ingestion_service
    app.state.maintenance_service = maintenance_service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.frontend_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(json.dumps({"event": "request_failed", "request_id": request_id,
                                         "method": request.method, "path": request.url.path}, sort_keys=True))
            response = _error(500, "internal_error", "The server could not complete the request")
        if response.status_code >= 400 and response.headers.get("X-OccupAI-Error-Envelope") != "1":
            defaults = {
                400: ("bad_request", "The request could not be accepted"),
                404: ("not_found", "The requested resource was not found"),
                405: ("method_not_allowed", "The HTTP method is not allowed for this resource"),
            }
            code, message = defaults.get(
                response.status_code, ("http_error", "The request could not be completed")
            )
            response = _error(response.status_code, code, message)
        if "X-OccupAI-Error-Envelope" in response.headers:
            del response.headers["X-OccupAI-Error-Envelope"]
        response.headers["X-Request-ID"] = request_id
        if request.url.path == "/api/rooms":
            response.headers["Cache-Control"] = "public, max-age=300"
        elif request.url.path.startswith("/api/occupancy"):
            response.headers["Cache-Control"] = "no-store"
        _log("request", request_id=request_id, method=request.method, path=request.url.path,
             status=response.status_code, duration_ms=round((time.perf_counter() - started) * 1000, 2))
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(400, "invalid_request", "Request validation failed", {"errors": exc.errors()})

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        return _error(exc.status_code, detail.get("code", "http_error"), detail.get("message", "Request failed"))

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        defaults = {
            404: ("not_found", "The requested resource was not found"),
            405: ("method_not_allowed", "The HTTP method is not allowed for this resource"),
        }
        code, message = defaults.get(exc.status_code, ("http_error", "Request failed"))
        return _error(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error", exc_info=exc)
        return _error(500, "internal_error", "The server could not complete the request")

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(data_source=active_settings.data_source)

    @app.get("/ready", response_model=HealthResponse, tags=["system"])
    def ready() -> HealthResponse:
        try:
            active_repository.list_rooms()
            if ingestion_service and ingestion_service.last_error:
                raise RuntimeError("model-server ingestion dependency is unavailable")
        except Exception as exc:
            _log("readiness_failed", logging.WARNING, data_source=active_settings.data_source,
                 error_type=type(exc).__name__)
            raise HTTPException(503, detail={"code": "not_ready", "message": "A required dependency is unavailable"})
        return HealthResponse(data_source=active_settings.data_source)

    @app.get("/api/rooms", response_model=RoomsResponse, tags=["rooms"])
    def list_rooms() -> RoomsResponse:
        rooms = active_repository.list_rooms()
        return RoomsResponse(
            data=rooms,
            meta=CollectionMeta(count=len(rooms), generated_at=active_repository.generated_at),
        )

    @app.get(
        "/api/rooms/{room_id}",
        response_model=RoomResponse,
        responses={404: {"model": ErrorResponse}},
        tags=["rooms"],
    )
    def get_room(room_id: str) -> RoomResponse:
        room = active_repository.get_room(room_id)
        if room is None:
            raise HTTPException(404, detail={"code": "room_not_found", "message": f"Unknown room: {room_id}"})
        return RoomResponse(data=room)

    @app.get("/api/occupancy", response_model=OccupancyListResponse, tags=["occupancy"])
    def list_occupancy() -> OccupancyListResponse:
        values = active_repository.list_occupancy()
        return OccupancyListResponse(
            data=values,
            meta=CollectionMeta(count=len(values), generated_at=active_repository.generated_at),
        )

    @app.get(
        "/api/occupancy/{camera_id}",
        response_model=OccupancyResponse,
        responses={404: {"model": ErrorResponse}},
        tags=["occupancy"],
    )
    def get_occupancy(camera_id: str) -> OccupancyResponse:
        value = active_repository.get_occupancy(camera_id)
        if value is None:
            raise HTTPException(
                404,
                detail={"code": "camera_not_found", "message": f"Unknown camera: {camera_id}"},
            )
        return OccupancyResponse(data=value)

    @app.get(
        "/api/history",
        response_model=HistoryResponse,
        responses={404: {"model": ErrorResponse}},
        tags=["history"],
    )
    def get_history(
        room_id: str = Query(description="Canonical room identifier", pattern=r"^room_[a-z0-9_]+$"),
        history_range: HistoryRange = Query(
            alias="range",
            description="Aggregation bucket across retained history: hourly, daily, or one weekly bucket",
        ),
        metric: HistoryMetric = Query(description="Value represented by each history point"),
    ) -> HistoryResponse:
        points = active_repository.get_history(room_id, history_range, metric)
        if points is None:
            raise HTTPException(404, detail={"code": "room_not_found", "message": f"Unknown room: {room_id}"})
        return HistoryResponse(
            data=points,
            meta=HistoryMeta(
                room_id=room_id,
                range=history_range,
                metric=metric,
                count=len(points),
                generated_at=getattr(active_repository, "history_generated_at", None),
            ),
        )

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        invalid_request = {
            "description": "Invalid request parameters",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
        }
        for path in schema.get("paths", {}).values():
            for operation in path.values():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue
                if "422" in operation["responses"]:
                    operation["responses"].pop("422")
                    operation["responses"]["400"] = invalid_request
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    return app


app = create_app()
