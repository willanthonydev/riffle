import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from audio_analyser.basic_pitch_wrapper import BasicPitchTranscriber
from audio_analyser.config import Settings
from audio_analyser.errors import ErrorCode, ServiceError
from audio_analyser.models import (
    AnalyseAudioRequest,
    AnalyseAudioResponse,
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    read_session_id_from_body,
)
from audio_analyser.service import AudioAnalysisService
from audio_analyser.storage import S3AudioStorage

logger = logging.getLogger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    storage: Any | None = None,
    transcriber: Any | None = None,
) -> FastAPI:
    settings = settings or Settings()
    storage = storage or S3AudioStorage(settings)
    transcriber = transcriber or BasicPitchTranscriber()

    app = FastAPI(title="Riffle Audio Analyser")
    app.state.analysis_service = AudioAnalysisService(storage, transcriber, settings)

    @app.exception_handler(ServiceError)
    async def service_error_handler(_request: Request, exc: ServiceError) -> JSONResponse:
        logger.info("audio-analyser request failed", extra={"sessionId": exc.session_id, "errorCode": exc.code})
        return error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            session_id=exc.session_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, _exc: RequestValidationError) -> JSONResponse:
        session_id = await extract_session_id(request)
        return error_response(
            status_code=400,
            code=ErrorCode.INVALID_REQUEST,
            message="Invalid analyse-audio request.",
            session_id=session_id,
        )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="audio-analyser")

    @app.post("/v1/analyse-audio", response_model=AnalyseAudioResponse)
    def analyse_audio(request: AnalyseAudioRequest) -> AnalyseAudioResponse:
        logger.info("audio analysis request received", extra={"sessionId": request.session_id})
        return app.state.analysis_service.analyse(request)

    return app


def error_response(
    *,
    status_code: int,
    code: ErrorCode,
    message: str,
    session_id: str | None,
) -> JSONResponse:
    response = ErrorResponse(error=ErrorBody(code=code.value, message=message, sessionId=session_id))
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(by_alias=True, exclude_none=True),
    )


async def extract_session_id(request: Request) -> str | None:
    try:
        body = await request.json()
    except Exception:
        return None
    return read_session_id_from_body(body)
