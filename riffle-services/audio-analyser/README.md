# Riffle Audio Analyser

Small FastAPI service that reads a prepared WAV object from S3-compatible storage, runs Spotify Basic Pitch, and returns normalized note-event data.

## Python Runtime

The audio-analyser targets Python 3.10 for development, tests, and local runtime.

Use Python 3.10 for Basic Pitch as well. Newer Python versions such as Python 3.13 may hit dependency or build compatibility issues in Basic Pitch or its transitive audio/ML dependencies.

## Run Locally

Install dependencies in a virtual environment:

```bash
python3.10 -m venv .venv
. .venv/bin/activate
python3.10 -m pip install -e '.[test]'
```

Install the Basic Pitch runtime when you want to run real transcription:

```bash
python3.10 -m pip install -e '.[basic-pitch]'
```

Run the service:

```bash
python3.10 -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

Health check:

```bash
curl http://localhost:8001/health
```

## Configuration

Environment variables use the `RIFFLE_AUDIO_ANALYSER_` prefix.

| Variable | Default | Description |
| --- | --- | --- |
| `RIFFLE_AUDIO_ANALYSER_S3_ENDPOINT_URL` | unset | S3-compatible endpoint, such as LocalStack. |
| `RIFFLE_AUDIO_ANALYSER_S3_REGION` | `us-east-1` | S3 region. |
| `RIFFLE_AUDIO_ANALYSER_S3_ACCESS_KEY` | `test` | S3 access key. |
| `RIFFLE_AUDIO_ANALYSER_S3_SECRET_KEY` | `test` | S3 secret key. |
| `RIFFLE_AUDIO_ANALYSER_SERVICE_VERSION` | `local-dev` | Value returned in response metadata. |
| `RIFFLE_AUDIO_ANALYSER_TEMP_DIR` | unset | Optional temp file directory. |
| `RIFFLE_AUDIO_ANALYSER_LOW_CONFIDENCE_THRESHOLD` | unset | Optional warning threshold. |

## LocalStack Integration Test Prerequisites

No real AWS account is required.

For the first implementation, integration tests assume LocalStack is already running or is provided by Docker Compose outside the Python test process.

Expected default values:

| Setting | Value |
| --- | --- |
| LocalStack endpoint | `http://localhost:4566` |
| Test bucket | `riffle-audio-analyser-test` |
| Region | `us-east-1` |
| Access key | `test` |
| Secret key | `test` |

Example LocalStack command:

```bash
docker run --rm -p 4566:4566 -e SERVICES=s3 localstack/localstack
```

Run unit tests:

```bash
python3.10 -m pytest
```

Run the LocalStack integration test:

```bash
RUN_LOCALSTACK_TESTS=1 python3.10 -m pytest -m integration
```

Run the Basic Pitch smoke test:

```bash
python3.10 -m pip install -e '.[basic-pitch]'
RUN_BASIC_PITCH_SMOKE=1 python3.10 -m pytest -m basic_pitch
```
