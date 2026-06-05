from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from audio_analyser.s3_uri import parse_s3_uri


SUPPORTED_CONTENT_TYPES = {"audio/wav", "audio/x-wav"}
MAX_DURATION_MS = 15_000


class AnalyseAudioRequest(BaseModel):
    session_id: str = Field(alias="sessionId")
    audio_uri: str = Field(alias="audioUri")
    content_type: str = Field(alias="contentType")
    duration_ms: int = Field(alias="durationMs")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("session_id", "audio_uri", "content_type")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("must be non-blank")
        return value

    @field_validator("audio_uri")
    @classmethod
    def require_s3_uri(cls, value: str) -> str:
        parse_s3_uri(value)
        return value

    @field_validator("duration_ms")
    @classmethod
    def require_supported_duration(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("must be an integer")
        if value <= 0 or value > MAX_DURATION_MS:
            raise ValueError("must be between 1 and 15000")
        return value


class SourceMetadata(BaseModel):
    audio_uri: str = Field(alias="audioUri")
    content_type: str = Field(alias="contentType")
    duration_ms: int = Field(alias="durationMs")

    model_config = ConfigDict(populate_by_name=True)


class NoteEvent(BaseModel):
    start_ms: int = Field(alias="startMs")
    end_ms: int = Field(alias="endMs")
    duration_ms: int = Field(alias="durationMs")
    pitch_midi: int = Field(alias="pitchMidi")
    pitch_name: str = Field(alias="pitchName")
    frequency_hz: float = Field(alias="frequencyHz")
    confidence: float | None = None

    model_config = ConfigDict(populate_by_name=True)


class MidiMetadata(BaseModel):
    available: bool
    note_count: int = Field(alias="noteCount")

    model_config = ConfigDict(populate_by_name=True)


class ConfidenceMetadata(BaseModel):
    overall: float | None


class WarningMessage(BaseModel):
    code: str
    message: str


class AnalysisMetadata(BaseModel):
    model_name: str = Field(alias="modelName")
    model_version: str | None = Field(alias="modelVersion")
    service_version: str = Field(alias="serviceVersion")
    started_at: str = Field(alias="startedAt")
    completed_at: str = Field(alias="completedAt")
    processing_time_ms: int = Field(alias="processingTimeMs")

    model_config = ConfigDict(populate_by_name=True)


class AnalyseAudioResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    source: SourceMetadata
    notes: list[NoteEvent]
    midi: MidiMetadata
    confidence: ConfidenceMetadata
    warnings: list[WarningMessage]
    analysis: AnalysisMetadata

    model_config = ConfigDict(populate_by_name=True)


class HealthResponse(BaseModel):
    status: str
    service: str


class ErrorBody(BaseModel):
    code: str
    message: str
    session_id: str | None = Field(default=None, alias="sessionId")

    model_config = ConfigDict(populate_by_name=True)


class ErrorResponse(BaseModel):
    error: ErrorBody


def read_session_id_from_body(body: Any) -> str | None:
    if isinstance(body, dict):
        session_id = body.get("sessionId")
        if isinstance(session_id, str) and session_id.strip():
            return session_id
    return None
