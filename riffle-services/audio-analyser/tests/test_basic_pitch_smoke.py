import math
import os
import wave

import pytest

from audio_analyser.basic_pitch_wrapper import BasicPitchTranscriber


pytestmark = pytest.mark.basic_pitch


@pytest.mark.skipif(os.getenv("RUN_BASIC_PITCH_SMOKE") != "1", reason="requires Basic Pitch runtime")
def test_basic_pitch_smoke_with_short_wav(tmp_path):
    audio_path = tmp_path / "tone.wav"
    write_sine_wave(audio_path)

    result = BasicPitchTranscriber().transcribe(audio_path)

    assert result.model_name == "basic-pitch"
    assert isinstance(result.notes, list)


def write_sine_wave(path):
    sample_rate = 16_000
    duration_seconds = 1
    frequency = 329.63
    frame_count = sample_rate * duration_seconds

    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for frame in range(frame_count):
            sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * frame / sample_rate))
            wav_file.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))

