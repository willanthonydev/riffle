import pytest
from fastapi.testclient import TestClient

from audio_analyser.app import create_app
from audio_analyser.config import Settings
from fakes import FakeStorage, FakeTranscriber


@pytest.fixture
def fake_storage():
    return FakeStorage()


@pytest.fixture
def fake_transcriber():
    return FakeTranscriber()


@pytest.fixture
def client(fake_storage, fake_transcriber):
    app = create_app(
        settings=Settings(service_version="test"),
        storage=fake_storage,
        transcriber=fake_transcriber,
    )
    return TestClient(app)
