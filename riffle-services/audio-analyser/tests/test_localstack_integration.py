import io
import math
import os
import wave

import pytest
from fastapi.testclient import TestClient

from audio_analyser.basic_pitch_wrapper import TranscriptionResult, TranscribedNote
from audio_analyser.app import create_app
from audio_analyser.config import Settings
from audio_analyser.storage import S3AudioStorage


pytestmark = pytest.mark.integration


class FakeTranscriber:
    def transcribe(self, audio_path):
        assert audio_path.exists()
        return TranscriptionResult(
            notes=[TranscribedNote(start_ms=100, end_ms=200, pitch_midi=64, confidence=0.9)],
            midi_available=True,
            model_name="basic-pitch",
            model_version=None,
        )


@pytest.mark.skipif(os.getenv("RUN_LOCALSTACK_TESTS") != "1", reason="requires LocalStack")
def test_analyse_audio_with_localstack_s3_object():
    import boto3

    endpoint_url = os.getenv("LOCALSTACK_ENDPOINT_URL", "http://localhost:4566")
    bucket = os.getenv("LOCALSTACK_TEST_BUCKET", "riffle-audio-analyser-test")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "test")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
    key = "recordings/session-1/prepared-audio.wav"

    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    ensure_bucket(s3_client, bucket)
    s3_client.put_object(Bucket=bucket, Key=key, Body=tiny_wav_bytes(), ContentType="audio/wav")

    settings = Settings(
        s3_endpoint_url=endpoint_url,
        s3_region=region,
        s3_access_key=access_key,
        s3_secret_key=secret_key,
        service_version="test",
    )
    app = create_app(settings=settings, storage=S3AudioStorage(settings), transcriber=FakeTranscriber())
    client = TestClient(app)

    response = client.post(
        "/v1/analyse-audio",
        json={
            "sessionId": "session-1",
            "audioUri": f"s3://{bucket}/{key}",
            "contentType": "audio/wav",
            "durationMs": 1000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"sessionId", "source", "notes", "midi", "confidence", "warnings", "analysis"}
    assert body["notes"] == [
        {
            "startMs": 100,
            "endMs": 200,
            "durationMs": 100,
            "pitchMidi": 64,
            "pitchName": "E4",
            "frequencyHz": 329.63,
            "confidence": 0.9,
        }
    ]


def ensure_bucket(s3_client, bucket: str) -> None:
    try:
        s3_client.create_bucket(Bucket=bucket)
    except Exception:
        pass


def tiny_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    sample_rate = 16000
    frame_count = sample_rate // 10

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for frame in range(frame_count):
            sample = int(32767 * 0.1 * math.sin(2 * math.pi * 329.63 * frame / sample_rate))
            wav_file.writeframesraw(sample.to_bytes(2, "little", signed=True))

    return buffer.getvalue()
