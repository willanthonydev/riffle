# Architect Review: MVP 001 Audio Analyser Basic Pitch

## Findings

Severity: Low
File: `riffle-services/audio-analyser/pyproject.toml`
Issue:
`basic-pitch` is an optional dependency rather than a default runtime dependency.
Architecture concern:
This is acceptable for fast local/unit tests and matches the instruction to keep Basic Pitch optional for normal tests, but the service is architecturally defined as the Python Basic Pitch wrapper. A runtime environment that installs only the base project dependencies will start the FastAPI service but fail actual transcription requests with `TRANSCRIPTION_FAILED` because Basic Pitch is unavailable.
Suggested fix:
Keep Basic Pitch optional for normal tests, but make the runtime packaging path explicit when deployment or containerization is added. For example, production/local-real-transcription setup should install the `basic-pitch` extra or equivalent pinned Basic Pitch dependency.
Implementation agent instruction:
No source change is required for this slice. When adding Docker or deployment packaging, install the Basic Pitch extra in the runtime image and keep the normal unit-test install lightweight.

## Overall Architecture Assessment

The implementation preserves the agreed Riffle architecture.

The Python service boundary is clean: it exposes a small REST API, reads prepared audio from S3-compatible storage, runs Basic Pitch through a wrapper, and returns normalized analysis signals. It does not generate tabs, choose string/fret positions, generate exports, write to Postgres, call Spring, own `ProcessingJob` state, or introduce user/auth/billing concerns.

Spring remains the owner of orchestration, media preparation, persistence, tab inference, export generation, and lifecycle state. The audio-analyser accepts a concrete prepared `s3://` audio URI and WAV content types only, which aligns with the architecture direction that Spring/FFmpeg prepares audio before analysis.

S3 access is appropriate for this service because the architecture explicitly assigns prepared media storage to S3-compatible object storage and gives the analyser responsibility for reading prepared audio. LocalStack support is present through configuration and an opt-in integration test, without introducing real AWS, IAM, queues, event streaming, Kubernetes, or other premature infrastructure.

Python 3.10 expectations are clear in the spec, `pyproject.toml`, and README. Basic Pitch remains isolated behind `BasicPitchTranscriber`, and S3 access remains isolated behind `S3AudioStorage`, preserving testability and avoiding hidden coupling.

## Blocking Architecture Concerns

None.

## Non-Blocking Suggestions

- When a Dockerfile or deployment packaging is introduced, ensure the runtime image installs Basic Pitch using Python 3.10 while keeping normal unit-test dependencies lightweight.
- Keep the exact Basic Pitch package/version decision explicit before treating the smoke test as proof of transcription quality.

## Spec Conflicts

None found.

## Acceptable To Proceed

Yes. The implementation is acceptable to proceed from an architecture perspective.
