import pytest

from audio_analyser.s3_uri import parse_s3_uri


def test_parse_s3_uri():
    location = parse_s3_uri("s3://riffle-local/recordings/session-1/prepared%20audio.wav")

    assert location.bucket == "riffle-local"
    assert location.key == "recordings/session-1/prepared audio.wav"


@pytest.mark.parametrize(
    "uri",
    [
        "http://example.com/audio.wav",
        "s3:///recordings/session-1/prepared-audio.wav",
        "s3://riffle-local",
    ],
)
def test_parse_s3_uri_rejects_invalid_uri(uri):
    with pytest.raises(ValueError):
        parse_s3_uri(uri)
