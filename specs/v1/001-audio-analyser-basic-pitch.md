# MVP 001: Audio Analyser Basic Pitch Service

## 1. Purpose

Define the first implementation slice for `riffle-services/audio-analyser`.

This service wraps Spotify Basic Pitch so Riffle can turn a prepared short guitar audio file into structured, timestamped note-event data. The goal is to validate the riskiest technical assumption early: whether Basic Pitch can return useful note information from a short prepared guitar recording.

This spec intentionally keeps the Python service small. Spring owns product orchestration, job state, media preparation, tab inference, exports, and persistence.

## 2. Suggested File Path

`specs/v1/001-audio-analyser-basic-pitch.md`

## 3. Context

Relevant existing guidance:

- `AGENTS.md`
- `specs/v1/architecture.md`
- `specs/v1/domain-model.md`

The architecture currently says:

- The Python audio analyser is a separate service because Basic Pitch is Python-based.
- The audio analyser reads prepared audio from S3-compatible object storage.
- The audio analyser returns structured audio analysis results.
- The audio analyser does not generate tabs, choose string/fret positions, write to Postgres, own job state, or make product decisions.

## 4. Scope

Implement a deliberately simple Python REST service that:

- Exposes a health endpoint.
- Exposes an analyse-audio endpoint.
- Accepts a concrete prepared audio URI.
- Reads the prepared audio file from S3-compatible object storage.
- Runs Spotify Basic Pitch against the prepared audio.
- Returns structured timestamped note events.
- Returns minimal MIDI-derived metadata where practical.
- Returns confidence values where Basic Pitch or derived processing makes them available.
- Returns warnings where useful.
- Returns model and analysis metadata.
- Returns explicit machine-readable errors for expected failure cases.

The first implementation should prove that the service can return useful note-event data from a short guitar recording.

## 5. Non-Scope

The audio analyser must not:

- Generate guitar tabs.
- Choose guitar string or fret positions.
- Generate MusicXML, Guitar Pro, text tab, PDF, image, or other exports.
- Call the Spring backend.
- Query or write Postgres.
- Create, update, claim, or complete Riffle `ProcessingJob` records.
- Own Riffle job state.
- Know about users, authentication, authorisation, billing, or ownership.
- Receive combined audio/video media.
- Extract audio using FFmpeg.
- Store analysis results in S3 or Postgres.
- Implement video analysis.
- Introduce queues, event streaming, Kubernetes, or distributed workflow infrastructure.

## 6. Service Location

Service root:

`riffle-services/audio-analyser`

The implementation should favour a small, readable FastAPI/Pydantic/Uvicorn layout over framework-heavy structure. The service should expose a boring REST API and be straightforward for a backend Java engineer to read.

## 7. External Dependencies

Required runtime capabilities:

- Spotify Basic Pitch for transcription.
- An S3-compatible object-storage client.
- Local filesystem temporary storage, if Basic Pitch requires a local audio file path.

Required local test capability:

- LocalStack for S3-compatible integration tests.

The first implementation must not require:

- A real AWS account.
- Real IAM setup.
- A production S3 bucket.
- Network access to Spring.
- A running Postgres instance.

## 8. Inputs

### Analyse Audio Request

Endpoint:

`POST /v1/analyse-audio`

Request body:

```json
{
  "sessionId": "018fd0b5-8e5f-7f56-8b8e-0c6b1f7a1a55",
  "audioUri": "s3://riffle-local/recordings/018fd0b5/prepared-audio.wav",
  "contentType": "audio/wav",
  "durationMs": 5320
}
```

Fields:

| Field | Required | Description |
| --- | --- | --- |
| `sessionId` | Yes | Opaque non-blank trace/correlation identifier supplied by Spring. It must not be required to use UUID format and must not be treated as authoritative job state. |
| `audioUri` | Yes | Concrete URI for a prepared audio object in S3-compatible storage. Initial supported scheme is `s3://`. |
| `contentType` | Yes | Content type of the prepared audio object. |
| `durationMs` | Yes | Duration of the prepared audio in milliseconds, as determined by Spring during media preparation. |

### Supported Content Types

Initial supported content types:

- `audio/wav`
- `audio/x-wav`

The preferred prepared audio content type is `audio/wav`.

Spring controls prepared audio generation through FFmpeg. The first implementation should accept prepared WAV audio only. Broader format support can be added deliberately later if Spring/FFmpeg preparation and Basic Pitch handling need it.

Additional content types must not be accepted silently.

### Duration Limits

The service should reject requests with:

- `durationMs <= 0`
- `durationMs > 15000`

Riffle V1 is focused on short riffs, exercises, teaching snippets, and quick idea capture. The first implementation duration limit is 15 seconds.

## 9. Outputs

### Successful Response

Status:

`200 OK`

Response body:

```json
{
  "sessionId": "018fd0b5-8e5f-7f56-8b8e-0c6b1f7a1a55",
  "source": {
    "audioUri": "s3://riffle-local/recordings/018fd0b5/prepared-audio.wav",
    "contentType": "audio/wav",
    "durationMs": 5320
  },
  "notes": [
    {
      "startMs": 120,
      "endMs": 480,
      "durationMs": 360,
      "pitchMidi": 64,
      "pitchName": "E4",
      "frequencyHz": 329.63,
      "confidence": 0.91
    }
  ],
  "midi": {
    "available": true,
    "noteCount": 1
  },
  "confidence": {
    "overall": 0.91
  },
  "warnings": [],
  "analysis": {
    "modelName": "basic-pitch",
    "modelVersion": null,
    "serviceVersion": "local-dev",
    "startedAt": "2026-06-05T13:00:00Z",
    "completedAt": "2026-06-05T13:00:03Z",
    "processingTimeMs": 3000
  }
}
```

Response fields:

| Field | Required | Description |
| --- | --- | --- |
| `sessionId` | Yes | Echo of request trace identifier. |
| `source` | Yes | Echoed source audio metadata. |
| `notes` | Yes | Ordered timestamped note events derived from Basic Pitch output. Empty only when transcription succeeds but no notes are detected. |
| `midi` | Yes | MIDI-derived metadata where practical. |
| `confidence` | Yes | Overall confidence where practical. Use `null` if unavailable. |
| `warnings` | Yes | Non-fatal warnings. Empty array when none. |
| `analysis` | Yes | Model, service, and runtime metadata. |

`analysis.modelVersion` may be `null` when the Basic Pitch model or package version cannot be determined reliably.

### Note Event

Each note event should contain:

| Field | Required | Description |
| --- | --- | --- |
| `startMs` | Yes | Note onset time in milliseconds from start of prepared audio. |
| `endMs` | Yes | Note end time in milliseconds from start of prepared audio. |
| `durationMs` | Yes | `endMs - startMs`. |
| `pitchMidi` | Yes | MIDI note number. |
| `pitchName` | Yes | Human-readable pitch name, such as `E4`. |
| `frequencyHz` | Yes | Frequency derived from MIDI pitch. |
| `confidence` | No | Per-note confidence if available. Use `null` if unavailable. |

Rules:

- Notes must be sorted by `startMs`, then `pitchMidi`.
- Times must be rounded to whole milliseconds.
- The service must not attach string, fret, tuning, technique, hand-position, or tab-specific fields to note events.

### MIDI Output

The response should include normalized note events and minimal MIDI-derived metadata only.

Initial response may include:

- `available`
- `noteCount`

The first implementation must not return, store, or base64-encode an actual MIDI file. If Basic Pitch creates MIDI output internally, the service may use it to derive response metadata, but that file is an implementation detail and must not become part of this API slice.

### Confidence

The service should return confidence values where available.

Rules:

- If Basic Pitch exposes per-note confidence, map it to `notes[].confidence`.
- If only partial confidence is available, return available values and leave unavailable fields as `null`.
- `confidence.overall` may be derived from note confidence values, such as a simple average, if that derivation is clearly named in code and metadata.
- Do not invent confidence precision beyond what is available from Basic Pitch or a simple documented derivation.

### Warnings

Warnings are non-fatal issues where analysis completed but the caller should treat results carefully.

Initial warning examples:

- `NO_NOTES_DETECTED`
- `LOW_OVERALL_CONFIDENCE`
- `AUDIO_DURATION_NEAR_LIMIT`
- `MIDI_METADATA_UNAVAILABLE`

Warning shape:

```json
{
  "code": "LOW_OVERALL_CONFIDENCE",
  "message": "Overall transcription confidence is below the configured warning threshold."
}
```

Warnings must be safe to show in logs. They should not include credentials, signed URLs, stack traces, or local filesystem paths.

## 10. API Contract

### Health

Endpoint:

`GET /health`

Successful response:

```json
{
  "status": "ok",
  "service": "audio-analyser"
}
```

`/health` should not require S3 or Basic Pitch transcription to run. It is a process liveness check.

### Analyse Audio

Endpoint:

`POST /v1/analyse-audio`

The endpoint performs one synchronous analysis request from Spring's perspective. It should return only after Basic Pitch finishes or an error occurs.

The endpoint must not enqueue background work in the Python service.

## 11. Validation Rules

The service must reject invalid requests before reading from object storage.

Validation rules:

- Request body must be valid JSON.
- `sessionId` must be present and non-blank.
- `audioUri` must be present and non-blank.
- `audioUri` must use the `s3://` scheme for the first implementation.
- `audioUri` must include bucket and object key.
- `contentType` must be present and one of the supported content types.
- `durationMs` must be an integer.
- `durationMs` must be greater than `0`.
- `durationMs` must be less than or equal to `15000`.

If validation fails, return `400 Bad Request` with an `INVALID_REQUEST` error code unless a more specific code below applies.

## 12. Error Cases

Error response shape:

```json
{
  "error": {
    "code": "UNSUPPORTED_CONTENT_TYPE",
    "message": "Unsupported audio content type.",
    "sessionId": "018fd0b5-8e5f-7f56-8b8e-0c6b1f7a1a55"
  }
}
```

Error fields:

| Field | Required | Description |
| --- | --- | --- |
| `error.code` | Yes | Stable machine-readable error code. |
| `error.message` | Yes | Safe human-readable summary. |
| `error.sessionId` | No | Echoed when present and parseable from the request. |

Initial error codes:

| HTTP Status | Code | Meaning |
| --- | --- | --- |
| `400` | `INVALID_REQUEST` | JSON shape, required fields, URI format, or duration validation failed. |
| `415` | `UNSUPPORTED_CONTENT_TYPE` | `contentType` is not supported. |
| `404` | `AUDIO_OBJECT_NOT_FOUND` | The S3 bucket/object does not exist or is not readable as a missing object. |
| `422` | `UNREADABLE_AUDIO` | The object exists but cannot be decoded or read as audio. |
| `500` | `TRANSCRIPTION_FAILED` | Basic Pitch failed while processing a readable audio file. |
| `500` | `STORAGE_READ_FAILED` | Object storage returned an unexpected non-missing-object failure. |

Error messages must not include:

- Object storage credentials.
- Signed URLs.
- Local temporary file paths.
- Python stack traces.
- Full dependency exception dumps.

Detailed errors may be logged with `sessionId` for local debugging.

## 13. Data Model Impact

No Postgres schema changes are required for this slice.

The audio analyser returns JSON to Spring. Spring is responsible for deciding whether and where to persist that JSON as an `AnalysisResult` artefact.

The note-event response shape in this spec may later become the audio analysis JSON stored in S3 by Spring, but this service does not write that artefact itself.

## 14. Storage Impact

The service reads a prepared audio object from S3-compatible storage.

The service does not create, update, or delete Riffle storage objects.

Temporary local files are allowed only as an implementation detail needed to run Basic Pitch. Temporary files should be removed after each request where practical.

## 15. Configuration

The service should support local S3-compatible configuration without requiring AWS.

Initial configuration should include:

- S3 endpoint URL for LocalStack or compatible storage.
- S3 region.
- S3 access key.
- S3 secret key.
- Optional service version string for response metadata.
- Optional temporary directory path.
- Optional confidence warning threshold.

Configuration should be environment-variable friendly.

Do not add production AWS-specific deployment assumptions in this spec.

## 15.1 REST Framework

The first implementation should use:

- FastAPI for the REST service.
- Pydantic for request and response models.
- Uvicorn for local serving.

The service should still remain small and readable for a Java/Spring developer. Avoid framework-heavy structure, dependency injection complexity, and Python-specific cleverness that is not needed for this slice.

## 15.2 Python Runtime

The first implementation targets Python 3.10.

The audio analyser should be developed, tested, and run with Python 3.10. Basic Pitch should also be installed and run with Python 3.10 because newer Python versions, such as Python 3.13, may hit dependency or build compatibility issues in Basic Pitch or its transitive audio/ML dependencies.

## 16. Logging and Traceability

The service should log:

- Request received with `sessionId`.
- Audio download start and completion with `sessionId`.
- Basic Pitch analysis start and completion with `sessionId`.
- Error code and safe message with `sessionId`.

The service should not log:

- Credentials.
- Signed URLs.
- Full audio file contents.
- Full stack traces in normal request logs.

`sessionId` is for traceability only. It must not cause the service to call Spring or query job state.

## 17. Acceptance Criteria

The slice is complete when:

- `GET /health` returns a simple JSON liveness response.
- `POST /v1/analyse-audio` accepts a valid request with an `s3://` prepared audio URI.
- The service reads the object from S3-compatible storage.
- The service runs Basic Pitch on the prepared audio.
- The service returns ordered timestamped note events with MIDI pitch data.
- The service returns analysis metadata including model name and processing time.
- The service returns confidence values where available or `null` where unavailable.
- The service returns warnings as an array.
- The service returns explicit errors for invalid request, unsupported content type, missing object, unreadable audio, transcription failure, and unexpected storage read failure.
- The service does not generate tabs, string/fret positions, exports, job updates, or database writes.
- The service can be exercised locally without a real AWS account.

## 18. Tests Required

### Unit Tests

Unit tests should use fakes or mocks for S3 and Basic Pitch.

Required unit coverage:

- Valid request validation passes.
- Missing required fields return `INVALID_REQUEST`.
- Invalid `audioUri` returns `INVALID_REQUEST`.
- Unsupported `contentType` returns `UNSUPPORTED_CONTENT_TYPE`.
- Invalid `durationMs` returns `INVALID_REQUEST`.
- Missing S3 object maps to `AUDIO_OBJECT_NOT_FOUND`.
- Existing but unreadable audio maps to `UNREADABLE_AUDIO`.
- Basic Pitch failure maps to `TRANSCRIPTION_FAILED`.
- Successful Basic Pitch output maps to ordered note events.
- Warning generation returns an empty array when there are no warnings.
- Warning generation returns `NO_NOTES_DETECTED` when analysis succeeds with no notes.

### Integration Tests

Integration tests must not require real AWS.

For the first implementation, LocalStack may be provided by Docker Compose or assumed to be running before integration tests start.

The integration test documentation must state the expected:

- LocalStack endpoint.
- Test bucket.
- Region.
- Access key.
- Secret key.

The first implementation does not need Python test tooling to automatically start LocalStack.

Required integration coverage:

- Create a test bucket in LocalStack.
- Upload a small sample audio fixture.
- Call `POST /v1/analyse-audio` with an `s3://` URI.
- Assert `200 OK`.
- Assert the response contains `sessionId`, `source`, `notes`, `midi`, `confidence`, `warnings`, and `analysis`.
- Assert `notes` is an array of note-event objects when the fixture is expected to produce notes.

### Basic Pitch Smoke Test

Include a smoke test using a small local audio fixture if practical.

The smoke test should:

- Use a short fixture, ideally only a few seconds.
- Run Basic Pitch through the same wrapper used by the REST endpoint.
- Assert that the result can be converted into the response note-event shape.

The smoke test may be marked or documented separately if it is slower than normal unit tests.

## 19. Fixtures

Fixtures should be short and small.

Preferred fixture:

- A short prepared guitar recording that can reasonably produce at least one note event.

Alternative fixture:

- A generated simple tone or short audio file may be used for infrastructure tests, but the first implementation should still include at least one practical guitar-recording check before treating the slice as proven.

Do not commit large media fixtures.

## 20. Implementation Notes

These notes guide the first implementation without prescribing full code structure:

- Keep the Python service deliberately simple.
- Put Basic Pitch access behind a small wrapper so unit tests can fake transcription.
- Put S3 access behind a small wrapper so unit tests can fake object reads.
- Prefer explicit request and response models.
- Prefer explicit exception-to-error mapping.
- Keep framework-specific code at the REST boundary.
- Keep product workflow concepts out of the service.

## 21. Open Questions

- Which exact Basic Pitch package/version should be pinned?
- What exact confidence threshold should trigger `LOW_OVERALL_CONFIDENCE`?
- Should LocalStack later be started automatically by Python test tooling?
