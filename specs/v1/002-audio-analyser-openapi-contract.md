# V1 002: Audio Analyser OpenAPI Contract

## 1. Purpose

Define the implementation work required to create the OpenAPI contract for the Python audio-analyser service.

The OpenAPI contract will document the small REST API implemented by `riffle-services/audio-analyser` for health checks and Basic Pitch audio analysis.

This spec does not define new service behaviour. `specs/v1/001-audio-analyser-basic-pitch.md` remains the source of truth for the audio-analyser API behaviour, validation rules, response shape, and error cases.

## 2. Suggested File Path

`specs/v1/002-audio-analyser-openapi-contract.md`

## 3. Implementation Output

The implementation agent should create:

`specs/v1/openapi/audio-analyser-api.yaml`

The YAML should use OpenAPI 3.x and should be readable, boring, and easy to review.

## 4. Scope

Create an OpenAPI YAML contract for the Python audio-analyser service that includes:

- `GET /health`
- `POST /v1/analyse-audio`
- Request schemas for analyse-audio.
- Success response schemas.
- Error response schemas.
- All expected status codes from `001-audio-analyser-basic-pitch`.
- Useful examples where they clarify the contract.
- Reusable OpenAPI components and schemas.

The contract should document the API consumed by the Spring backend when it calls the Python audio-analyser service.

## 5. Non-Scope

The OpenAPI contract must not include:

- Guitar tab generation.
- Guitar string or fret positions.
- MusicXML, Guitar Pro, text tab, PDF, image, or other export APIs.
- Actual MIDI file download, storage, or base64-encoded MIDI output.
- Spring backend job-management APIs.
- `jobId` as the primary analyse-audio input.
- ProcessingJob state ownership or mutation.
- Postgres persistence APIs.
- Calls from the Python service back to Spring.
- Combined audio/video media input.
- Video analysis endpoints.
- Authentication, users, ownership, billing, or authorisation.
- Callbacks, webhooks, queues, polling, or asynchronous job semantics.
- Production AWS, IAM, bucket provisioning, or deployment infrastructure.

## 6. Contract Rules

The OpenAPI YAML must:

- Use OpenAPI 3.x.
- Use British spelling: `analyse`, not `analyze`.
- Use endpoint path `/v1/analyse-audio`.
- Document that the service accepts prepared audio only.
- Document that `audioUri` points to S3-compatible object storage.
- Document that `sessionId` is an opaque trace/correlation identifier only.
- Not imply that `sessionId` is authoritative job state.
- Return normalised note events and minimal MIDI metadata only.
- Not return, store, or base64-encode an actual MIDI file.
- Use reusable `components.schemas`.
- Keep schema names clear and boring.
- Align with `specs/v1/001-audio-analyser-basic-pitch.md`.

## 7. Endpoints

### `GET /health`

Document a process liveness endpoint.

Expected `200 OK` response:

```json
{
  "status": "ok",
  "service": "audio-analyser"
}
```

The health endpoint should not require S3 access or Basic Pitch transcription.

### `POST /v1/analyse-audio`

Document a synchronous analyse-audio endpoint.

The endpoint receives a concrete prepared audio URI, reads that prepared audio from S3-compatible object storage, runs Basic Pitch, and returns structured audio analysis signals.

The endpoint must not document background job creation, queueing, callback registration, polling, or Spring job state mutation.

## 8. Request Schema

The analyse-audio request must include:

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `sessionId` | string | Yes | Non-blank opaque trace/correlation identifier. Do not require UUID format. |
| `audioUri` | string | Yes | `s3://` URI including bucket and object key. |
| `contentType` | string | Yes | Enum: `audio/wav`, `audio/x-wav`. |
| `durationMs` | integer | Yes | Minimum `1`, maximum `15000`. |

The request should include an example similar to:

```json
{
  "sessionId": "session-1",
  "audioUri": "s3://riffle-local/recordings/session-1/prepared-audio.wav",
  "contentType": "audio/wav",
  "durationMs": 5320
}
```

## 9. Success Response Schema

The `200 OK` response for `POST /v1/analyse-audio` must include:

| Field | Required | Description |
| --- | --- | --- |
| `sessionId` | Yes | Echoed trace/correlation identifier. |
| `source` | Yes | Echoed prepared audio source metadata. |
| `notes` | Yes | Ordered normalised note events. |
| `midi` | Yes | Minimal MIDI-derived metadata. |
| `confidence` | Yes | Overall confidence container. |
| `warnings` | Yes | Non-fatal warning array. |
| `analysis` | Yes | Model, service, and processing metadata. |

### `source`

Required fields:

- `audioUri`
- `contentType`
- `durationMs`

### `notes[]`

Required fields:

- `startMs`
- `endMs`
- `durationMs`
- `pitchMidi`
- `pitchName`
- `frequencyHz`
- `confidence`

`confidence` must be nullable.

The contract must not include string, fret, tuning, technique, hand-position, or tab-specific fields on note events.

### `midi`

Required fields:

- `available`
- `noteCount`

The contract must document only metadata. It must not include a MIDI file body, object location, download URL, or base64 field.

### `confidence`

Required fields:

- `overall`

`overall` must be nullable.

### `warnings[]`

Required fields:

- `code`
- `message`

The contract may include examples such as:

- `NO_NOTES_DETECTED`
- `LOW_OVERALL_CONFIDENCE`
- `AUDIO_DURATION_NEAR_LIMIT`
- `MIDI_METADATA_UNAVAILABLE`

### `analysis`

Required fields:

- `modelName`
- `modelVersion`
- `serviceVersion`
- `startedAt`
- `completedAt`
- `processingTimeMs`

`modelVersion` must be nullable.

`startedAt` and `completedAt` should be documented as date-time strings.

## 10. Error Responses

All error responses must use this shape:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid analyse-audio request.",
    "sessionId": "session-1"
  }
}
```

`error.sessionId` is optional and should be documented as present only when it can be safely read from the request.

The OpenAPI contract must include these error responses for `POST /v1/analyse-audio`:

| HTTP Status | Code |
| --- | --- |
| `400` | `INVALID_REQUEST` |
| `415` | `UNSUPPORTED_CONTENT_TYPE` |
| `404` | `AUDIO_OBJECT_NOT_FOUND` |
| `422` | `UNREADABLE_AUDIO` |
| `500` | `TRANSCRIPTION_FAILED` |
| `500` | `STORAGE_READ_FAILED` |

Because two error codes use status `500`, document both possibilities for the `500` response, either through examples or a schema description.

Error messages must be safe summaries and must not expose credentials, signed URLs, local temporary paths, stack traces, or dependency exception dumps.

## 11. Validation Rules To Represent

The contract should represent these validation rules where OpenAPI can express them clearly:

- `sessionId` is required.
- `sessionId` is a string and should be non-blank.
- `audioUri` is required.
- `audioUri` is a string using the `s3://` scheme.
- `audioUri` must include bucket and object key.
- `contentType` is required.
- `contentType` enum is `audio/wav` or `audio/x-wav`.
- `durationMs` is required.
- `durationMs` is an integer.
- `durationMs` minimum is `1`.
- `durationMs` maximum is `15000`.

If a validation rule cannot be fully expressed in OpenAPI, include it in the field description rather than inventing new runtime behaviour.

## 12. Data Model Impact

No Postgres schema changes are required.

No domain model changes are required.

This contract describes a service-to-service API between Spring and the Python audio analyser. It does not create new persisted entities.

## 13. Review Checks

Review the generated OpenAPI YAML against:

- `AGENTS.md`
- `specs/v1/architecture.md`
- `specs/v1/domain-model.md`
- `specs/v1/001-audio-analyser-basic-pitch.md`

Checks:

- The contract file exists at `specs/v1/openapi/audio-analyser-api.yaml`.
- The contract uses OpenAPI 3.x.
- The only paths are `/health` and `/v1/analyse-audio`.
- The contract uses `analyse`, not `analyze`.
- The analyse-audio request contains only `sessionId`, `audioUri`, `contentType`, and `durationMs`.
- The content type enum is limited to `audio/wav` and `audio/x-wav`.
- The duration limit is represented as `1` to `15000` milliseconds.
- The success response includes source, notes, midi metadata, confidence, warnings, and analysis metadata.
- `notes[]` contains no tab, string, fret, tuning, or technique fields.
- The contract does not include actual MIDI file output.
- All specified error codes and statuses are documented.
- The contract does not introduce auth, users, billing, callbacks, webhooks, queues, async jobs, Spring calls, Postgres writes, exports, or video analysis.

## 14. Acceptance Criteria

The implementation is complete when:

- `specs/v1/openapi/audio-analyser-api.yaml` exists.
- The YAML is valid OpenAPI 3.x.
- The YAML documents `GET /health`.
- The YAML documents `POST /v1/analyse-audio`.
- The YAML includes reusable schemas for request, success response, note event, MIDI metadata, confidence, warning, analysis metadata, and error response.
- The YAML includes all required request fields, validation constraints, response fields, error statuses, and error codes listed in this spec.
- The YAML stays aligned with `specs/v1/001-audio-analyser-basic-pitch.md`.
- The YAML does not include any non-scope responsibilities.
- The contract is readable enough to be used by the Spring backend implementation later.

## 15. Tests Required

At minimum, manually review the YAML against the checks in this spec.

If practical, run an OpenAPI validation tool against `specs/v1/openapi/audio-analyser-api.yaml`.

If the repository later adds OpenAPI linting or contract tests, include this contract in that validation path.

## 16. Open Questions

None.
