from audio_analyser.basic_pitch_wrapper import TranscriptionResult, TranscribedNote
from audio_analyser.app import create_app
from audio_analyser.config import Settings
from audio_analyser.errors import (
    AudioObjectNotFoundError,
    StorageReadFailedError,
    TranscriptionFailedError,
    UnreadableAudioError,
)


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "audio-analyser"}


def test_analyse_audio_returns_normalized_response(client, fake_storage):
    response = client.post("/v1/analyse-audio", json=valid_request())

    assert response.status_code == 200
    body = response.json()
    assert fake_storage.requested_uri == "s3://riffle-local/recordings/session-1/prepared-audio.wav"
    assert body["sessionId"] == "session-1"
    assert body["source"] == {
        "audioUri": "s3://riffle-local/recordings/session-1/prepared-audio.wav",
        "contentType": "audio/wav",
        "durationMs": 5320,
    }
    assert body["notes"] == [
        {
            "startMs": 100,
            "endMs": 250,
            "durationMs": 150,
            "pitchMidi": 64,
            "pitchName": "E4",
            "frequencyHz": 329.63,
            "confidence": 0.9,
        },
        {
            "startMs": 400,
            "endMs": 500,
            "durationMs": 100,
            "pitchMidi": 67,
            "pitchName": "G4",
            "frequencyHz": 392.0,
            "confidence": 0.8,
        },
    ]
    assert body["midi"] == {"available": True, "noteCount": 2}
    assert body["confidence"] == {"overall": 0.85}
    assert body["warnings"] == []
    assert body["analysis"]["modelName"] == "basic-pitch"
    assert body["analysis"]["modelVersion"] is None
    assert body["analysis"]["serviceVersion"] == "test"
    assert body["analysis"]["processingTimeMs"] >= 0


def test_missing_required_field_returns_invalid_request(client):
    request = valid_request()
    del request["audioUri"]

    response = client.post("/v1/analyse-audio", json=request)

    assert_error(response, 400, "INVALID_REQUEST", "session-1")


def test_missing_session_id_returns_invalid_request(client):
    request = valid_request()
    del request["sessionId"]

    response = client.post("/v1/analyse-audio", json=request)

    assert_error(response, 400, "INVALID_REQUEST")


def test_missing_content_type_returns_invalid_request(client):
    request = valid_request()
    del request["contentType"]

    response = client.post("/v1/analyse-audio", json=request)

    assert_error(response, 400, "INVALID_REQUEST", "session-1")


def test_missing_duration_ms_returns_invalid_request(client):
    request = valid_request()
    del request["durationMs"]

    response = client.post("/v1/analyse-audio", json=request)

    assert_error(response, 400, "INVALID_REQUEST", "session-1")


def test_non_integer_duration_ms_returns_invalid_request(client):
    response = client.post("/v1/analyse-audio", json=valid_request(durationMs="short"))

    assert_error(response, 400, "INVALID_REQUEST", "session-1")


def test_blank_session_id_returns_invalid_request(client):
    request = valid_request(sessionId=" ")

    response = client.post("/v1/analyse-audio", json=request)

    assert_error(response, 400, "INVALID_REQUEST", None)


def test_invalid_audio_uri_returns_invalid_request(client):
    response = client.post("/v1/analyse-audio", json=valid_request(audioUri="http://example.com/audio.wav"))

    assert_error(response, 400, "INVALID_REQUEST", "session-1")


def test_s3_uri_without_bucket_returns_invalid_request(client):
    response = client.post("/v1/analyse-audio", json=valid_request(audioUri="s3:///recordings/audio.wav"))

    assert_error(response, 400, "INVALID_REQUEST", "session-1")


def test_s3_uri_without_object_key_returns_invalid_request(client):
    response = client.post("/v1/analyse-audio", json=valid_request(audioUri="s3://riffle-local"))

    assert_error(response, 400, "INVALID_REQUEST", "session-1")


def test_unsupported_content_type_returns_415(client):
    response = client.post("/v1/analyse-audio", json=valid_request(contentType="audio/flac"))

    assert_error(
        response,
        415,
        "UNSUPPORTED_CONTENT_TYPE",
        session_id="session-1",
        message="Unsupported audio content type.",
    )


def test_zero_duration_returns_invalid_request(client):
    response = client.post("/v1/analyse-audio", json=valid_request(durationMs=0))

    assert_error(response, 400, "INVALID_REQUEST", "session-1")


def test_duration_above_15_seconds_returns_invalid_request(client):
    response = client.post("/v1/analyse-audio", json=valid_request(durationMs=15001))

    assert_error(response, 400, "INVALID_REQUEST", "session-1")


def test_missing_s3_object_maps_to_audio_object_not_found(client, fake_storage):
    fake_storage.error = AudioObjectNotFoundError()

    response = client.post("/v1/analyse-audio", json=valid_request())

    assert_error(
        response,
        404,
        "AUDIO_OBJECT_NOT_FOUND",
        session_id="session-1",
        message="Prepared audio object was not found.",
    )


def test_unreadable_audio_maps_to_unreadable_audio(client, fake_transcriber):
    fake_transcriber.error = UnreadableAudioError()

    response = client.post("/v1/analyse-audio", json=valid_request())

    assert_error(
        response,
        422,
        "UNREADABLE_AUDIO",
        session_id="session-1",
        message="Prepared audio object could not be decoded.",
    )


def test_storage_read_failure_maps_to_storage_read_failed(client, fake_storage):
    fake_storage.error = StorageReadFailedError()

    response = client.post("/v1/analyse-audio", json=valid_request())

    assert_error(
        response,
        500,
        "STORAGE_READ_FAILED",
        session_id="session-1",
        message="Prepared audio could not be read from object storage.",
    )


def test_basic_pitch_failure_maps_to_transcription_failed(client, fake_transcriber):
    fake_transcriber.error = TranscriptionFailedError()

    response = client.post("/v1/analyse-audio", json=valid_request())

    assert_error(
        response,
        500,
        "TRANSCRIPTION_FAILED",
        session_id="session-1",
        message="Audio transcription failed.",
    )


def test_no_notes_warning(client, fake_transcriber):
    fake_transcriber.result = TranscriptionResult(
        notes=[],
        midi_available=True,
        model_name="basic-pitch",
        model_version=None,
    )

    response = client.post("/v1/analyse-audio", json=valid_request())

    assert response.status_code == 200
    assert response.json()["warnings"] == [
        {
            "code": "NO_NOTES_DETECTED",
            "message": "Analysis completed but no note events were detected.",
        }
    ]


def test_low_confidence_warning(fake_storage, fake_transcriber):
    from fastapi.testclient import TestClient

    fake_transcriber.result = TranscriptionResult(
        notes=[TranscribedNote(start_ms=100, end_ms=200, pitch_midi=64, confidence=0.1)],
        midi_available=True,
        model_name="basic-pitch",
        model_version=None,
    )
    app = create_app(
        settings=Settings(service_version="test", low_confidence_threshold=0.5),
        storage=fake_storage,
        transcriber=fake_transcriber,
    )
    client = TestClient(app)

    response = client.post("/v1/analyse-audio", json=valid_request())

    assert response.status_code == 200
    assert response.json()["warnings"] == [
        {
            "code": "LOW_OVERALL_CONFIDENCE",
            "message": "Overall transcription confidence is below the configured warning threshold.",
        }
    ]


def valid_request(**overrides):
    request = {
        "sessionId": "session-1",
        "audioUri": "s3://riffle-local/recordings/session-1/prepared-audio.wav",
        "contentType": "audio/wav",
        "durationMs": 5320,
    }
    request.update(overrides)
    return request


def assert_error(response, status_code, code, session_id=None, message=None):
    if message is None:
        message = response.json()["error"]["message"]
    assert response.status_code == status_code
    assert response.json() == {
        "error": {
            "code": code,
            "message": message,
            **({"sessionId": session_id} if session_id is not None else {}),
        }
    }
