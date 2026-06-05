from audio_analyser.basic_pitch_wrapper import TranscriptionResult, TranscribedNote


class FakeStorage:
    def __init__(self, audio_bytes: bytes = b"riffle-audio"):
        self.audio_bytes = audio_bytes
        self.requested_uri = None
        self.error = None

    def read_audio(self, audio_uri: str) -> bytes:
        self.requested_uri = audio_uri
        if self.error is not None:
            raise self.error
        return self.audio_bytes


class FakeTranscriber:
    def __init__(self):
        self.error = None
        self.result = TranscriptionResult(
            notes=[
                TranscribedNote(start_ms=400, end_ms=500, pitch_midi=67, confidence=0.8),
                TranscribedNote(start_ms=100, end_ms=250, pitch_midi=64, confidence=0.9),
            ],
            midi_available=True,
            model_name="basic-pitch",
            model_version=None,
        )

    def transcribe(self, audio_path):
        if self.error is not None:
            raise self.error
        assert audio_path.exists()
        return self.result
