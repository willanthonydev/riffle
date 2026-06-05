from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter
import logging

from audio_analyser.basic_pitch_wrapper import BasicPitchTranscriber, TranscriptionResult, TranscribedNote
from audio_analyser.config import Settings
from audio_analyser.errors import (
    AudioObjectNotFoundError,
    ErrorCode,
    ServiceError,
    StorageReadFailedError,
    TranscriptionFailedError,
    UnreadableAudioError,
)
from audio_analyser.models import (
    AnalyseAudioRequest,
    AnalyseAudioResponse,
    AnalysisMetadata,
    ConfidenceMetadata,
    MidiMetadata,
    NoteEvent,
    SourceMetadata,
    SUPPORTED_CONTENT_TYPES,
    WarningMessage,
)

logger = logging.getLogger(__name__)


class AudioAnalysisService:
    def __init__(self, storage, transcriber: BasicPitchTranscriber, settings: Settings):
        self._storage = storage
        self._transcriber = transcriber
        self._settings = settings

    def analyse(self, request: AnalyseAudioRequest) -> AnalyseAudioResponse:
        if request.content_type not in SUPPORTED_CONTENT_TYPES:
            raise ServiceError(
                code=ErrorCode.UNSUPPORTED_CONTENT_TYPE,
                message="Unsupported audio content type.",
                status_code=415,
                session_id=request.session_id,
            )

        started_at = utc_now()
        started_timer = perf_counter()
        audio_path: Path | None = None

        try:
            logger.info("audio download start", extra={"sessionId": request.session_id})
            audio_bytes = self._storage.read_audio(request.audio_uri)
            logger.info("audio download complete", extra={"sessionId": request.session_id})
            audio_path = self._write_temp_audio(audio_bytes)
            logger.info("basic pitch transcription start", extra={"sessionId": request.session_id})
            transcription = self._transcriber.transcribe(audio_path)
            logger.info("basic pitch transcription complete", extra={"sessionId": request.session_id})
        except AudioObjectNotFoundError as exc:
            raise ServiceError(
                code=ErrorCode.AUDIO_OBJECT_NOT_FOUND,
                message="Prepared audio object was not found.",
                status_code=404,
                session_id=request.session_id,
            ) from exc
        except StorageReadFailedError as exc:
            raise ServiceError(
                code=ErrorCode.STORAGE_READ_FAILED,
                message="Prepared audio could not be read from object storage.",
                status_code=500,
                session_id=request.session_id,
            ) from exc
        except UnreadableAudioError as exc:
            raise ServiceError(
                code=ErrorCode.UNREADABLE_AUDIO,
                message="Prepared audio object could not be decoded.",
                status_code=422,
                session_id=request.session_id,
            ) from exc
        except TranscriptionFailedError as exc:
            raise ServiceError(
                code=ErrorCode.TRANSCRIPTION_FAILED,
                message="Audio transcription failed.",
                status_code=500,
                session_id=request.session_id,
            ) from exc
        finally:
            if audio_path is not None:
                audio_path.unlink(missing_ok=True)

        completed_at = utc_now()
        processing_time_ms = round((perf_counter() - started_timer) * 1000)

        notes = sorted(
            [to_note_event(note) for note in transcription.notes],
            key=lambda note: (note.start_ms, note.pitch_midi),
        )
        overall_confidence = average_confidence(notes)

        return AnalyseAudioResponse(
            sessionId=request.session_id,
            source=SourceMetadata(
                audioUri=request.audio_uri,
                contentType=request.content_type,
                durationMs=request.duration_ms,
            ),
            notes=notes,
            midi=MidiMetadata(available=transcription.midi_available, noteCount=len(notes)),
            confidence=ConfidenceMetadata(overall=overall_confidence),
            warnings=build_warnings(notes, overall_confidence, transcription, self._settings),
            analysis=AnalysisMetadata(
                modelName=transcription.model_name,
                modelVersion=transcription.model_version,
                serviceVersion=self._settings.service_version,
                startedAt=format_timestamp(started_at),
                completedAt=format_timestamp(completed_at),
                processingTimeMs=processing_time_ms,
            ),
        )

    def _write_temp_audio(self, audio_bytes: bytes) -> Path:
        with NamedTemporaryFile(
            mode="wb",
            suffix=".wav",
            dir=self._settings.temp_dir,
            delete=False,
        ) as temp_file:
            temp_file.write(audio_bytes)
            return Path(temp_file.name)


def to_note_event(note: TranscribedNote) -> NoteEvent:
    return NoteEvent(
        startMs=note.start_ms,
        endMs=note.end_ms,
        durationMs=note.end_ms - note.start_ms,
        pitchMidi=note.pitch_midi,
        pitchName=pitch_name(note.pitch_midi),
        frequencyHz=round(frequency_hz(note.pitch_midi), 2),
        confidence=note.confidence,
    )


def pitch_name(midi_note: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = midi_note // 12 - 1
    return f"{names[midi_note % 12]}{octave}"


def frequency_hz(midi_note: int) -> float:
    return 440.0 * (2 ** ((midi_note - 69) / 12))


def average_confidence(notes: list[NoteEvent]) -> float | None:
    values = [note.confidence for note in notes if note.confidence is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def build_warnings(
    notes: list[NoteEvent],
    overall_confidence: float | None,
    transcription: TranscriptionResult,
    settings: Settings,
) -> list[WarningMessage]:
    warnings: list[WarningMessage] = []
    if not notes:
        warnings.append(
            WarningMessage(
                code="NO_NOTES_DETECTED",
                message="Analysis completed but no note events were detected.",
            )
        )
    if not transcription.midi_available:
        warnings.append(
            WarningMessage(
                code="MIDI_METADATA_UNAVAILABLE",
                message="MIDI-derived metadata was not available from transcription.",
            )
        )
    if (
        settings.low_confidence_threshold is not None
        and overall_confidence is not None
        and overall_confidence < settings.low_confidence_threshold
    ):
        warnings.append(
            WarningMessage(
                code="LOW_OVERALL_CONFIDENCE",
                message="Overall transcription confidence is below the configured warning threshold.",
            )
        )
    return warnings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
