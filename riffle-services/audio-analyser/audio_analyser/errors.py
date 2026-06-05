from dataclasses import dataclass
from enum import Enum


class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_CONTENT_TYPE = "UNSUPPORTED_CONTENT_TYPE"
    AUDIO_OBJECT_NOT_FOUND = "AUDIO_OBJECT_NOT_FOUND"
    UNREADABLE_AUDIO = "UNREADABLE_AUDIO"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    STORAGE_READ_FAILED = "STORAGE_READ_FAILED"


@dataclass
class ServiceError(Exception):
    code: ErrorCode
    message: str
    status_code: int
    session_id: str | None = None


class AudioObjectNotFoundError(Exception):
    pass


class StorageReadFailedError(Exception):
    pass


class UnreadableAudioError(Exception):
    pass


class TranscriptionFailedError(Exception):
    pass
