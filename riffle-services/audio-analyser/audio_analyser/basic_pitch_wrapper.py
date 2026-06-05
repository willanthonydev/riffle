from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from audio_analyser.errors import TranscriptionFailedError, UnreadableAudioError


@dataclass(frozen=True)
class TranscribedNote:
    start_ms: int
    end_ms: int
    pitch_midi: int
    confidence: float | None


@dataclass(frozen=True)
class TranscriptionResult:
    notes: list[TranscribedNote]
    midi_available: bool
    model_name: str
    model_version: str | None


class BasicPitchTranscriber:
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        try:
            from basic_pitch.inference import predict
        except Exception as exc:  # pragma: no cover - depends on optional runtime package
            raise TranscriptionFailedError("Basic Pitch is not available") from exc

        try:
            _model_output, midi_data, note_events = predict(str(audio_path))
        except (ValueError, OSError) as exc:
            raise UnreadableAudioError("Audio could not be decoded") from exc
        except Exception as exc:
            raise TranscriptionFailedError("Basic Pitch transcription failed") from exc

        return TranscriptionResult(
            notes=normalize_note_events(note_events),
            midi_available=midi_data is not None,
            model_name="basic-pitch",
            model_version=get_basic_pitch_version(),
        )


def get_basic_pitch_version() -> str | None:
    try:
        return metadata.version("basic-pitch")
    except metadata.PackageNotFoundError:
        return None


def normalize_note_events(note_events: Any) -> list[TranscribedNote]:
    notes = [_normalize_note_event(event) for event in note_events or []]
    notes = [note for note in notes if note is not None and note.end_ms >= note.start_ms]
    return sorted(notes, key=lambda note: (note.start_ms, note.pitch_midi))


def _normalize_note_event(event: Any) -> TranscribedNote | None:
    if isinstance(event, dict):
        start = _first_present(event, "start_time_s", "start", "start_time", "onset")
        end = _first_present(event, "end_time_s", "end", "end_time", "offset")
        pitch = _first_present(event, "pitch_midi", "pitch", "midi", "note")
        confidence = _first_present(event, "confidence", "probability", "amplitude")
        return _build_note(start, end, pitch, confidence)

    if isinstance(event, (list, tuple)) and len(event) >= 3:
        confidence = event[3] if len(event) >= 4 else None
        return _build_note(event[0], event[1], event[2], confidence)

    return None


def _first_present(values: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in values:
            return values[key]
    return None


def _build_note(start_seconds: Any, end_seconds: Any, pitch: Any, confidence: Any) -> TranscribedNote | None:
    if start_seconds is None or end_seconds is None or pitch is None:
        return None

    try:
        start_ms = round(float(start_seconds) * 1000)
        end_ms = round(float(end_seconds) * 1000)
        pitch_midi = int(round(float(pitch)))
    except (TypeError, ValueError):
        return None

    return TranscribedNote(
        start_ms=start_ms,
        end_ms=end_ms,
        pitch_midi=pitch_midi,
        confidence=_normalize_confidence(confidence),
    )


def _normalize_confidence(value: Any) -> float | None:
    if value is None:
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if 0 <= confidence <= 1:
        return confidence
    return None

