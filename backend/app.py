from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

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
from backend.repositories import MockOccupancyRepository, OccupancyRepository


logger = logging.getLogger(__name__)


def _error(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    payload = ErrorResponse(error=ErrorBody(code=code, message=message, details=details or {}))
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def _build_repository(settings: Settings) -> OccupancyRepository:
    if settings.data_source == "mock":
        return MockOccupancyRepository(settings.mock_data_dir)
    raise RuntimeError(
        f"Unsupported DATA_SOURCE={settings.data_source!r}. Only 'mock' is implemented; "
        "the model-server adapter is a later milestone."
    )


def create_app(
    settings: Settings | None = None,
    repository: OccupancyRepository | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
    active_repository = repository or _build_repository(active_settings)

    app = FastAPI(
        title="OccupAI Product API",
        version="0.1.0",
        description="Stable frontend-facing occupancy API with a replaceable data repository.",
    )
    app.state.settings = active_settings
    app.state.repository = active_repository
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.frontend_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(400, "invalid_request", "Request validation failed", {"errors": exc.errors()})

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        return _error(exc.status_code, detail.get("code", "http_error"), detail.get("message", "Request failed"))

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error", exc_info=exc)
        return _error(500, "internal_error", "The server could not complete the request")

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
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
