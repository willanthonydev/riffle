# Riffle Architecture Spec

## 1. Purpose

This document defines the initial architecture for Riffle.

Riffle is a short-form guitar recording and tab generation tool. It helps guitarists, teachers, and learners record short riffs, exercises, scales, or ideas and generate usable guitar tablature from that performance.

This architecture is intentionally simple. The first implementation should prove the core pipeline before adding production concerns such as authentication, billing, advanced editing, or public deployment.

The core pipeline is:

- browser recording
- upload
- object storage
- analysis
- tab inference
- export generation
- result retrieval

## 2. Product Direction

Riffle is not initially intended to be a general “upload any song and generate a tab” service.

The product is focused on short, self-recorded guitar performances.

Example use cases:

- A guitarist records a riff idea and gets a quick tab.
- A teacher records a short exercise and generates a tab for students.
- A learner records a short phrase and uses the generated tab as a starting point.

The first implementation should optimise for short recordings, fast feedback, and a simple workflow.

## 3. Repository Structure

Riffle is a monorepo.

Expected top-level areas:

- `riffle-backend`
- `riffle-frontend`
- `riffle-services/audio-analyser`
- `riffle-services/video-analyser`
- `specs`

Responsibilities:

- `riffle-backend`: Spring Boot / Spring Modulith backend.
- `riffle-frontend`: React / TypeScript / Vite browser client.
- `riffle-services/audio-analyser`: Python Basic Pitch audio analysis service.
- `riffle-services/video-analyser`: future Python video analysis service.
- `specs`: architecture, domain model, API contracts, and implementation specs.

## 4. High-Level System Flow

The high-level flow is:

1. The user records a short guitar performance in the browser.
2. The frontend uploads the recording to the Spring backend.
3. The backend stores source media in S3-compatible object storage.
4. The backend creates a processing job in Postgres.
5. A backend worker claims pending jobs.
6. The backend prepares media assets where needed.
7. The backend calls the Python audio analyser.
8. The backend may later call the Python video analyser.
9. The backend combines analysis signals.
10. The backend runs tab inference.
11. The backend generates an export.
12. The frontend polls for job status and retrieves the generated result.

## 5. Client Strategy

The first client is a browser-based application built with React, TypeScript, and Vite.

Riffle should support both mobile and desktop browsers from the start.

Native iOS and Android apps are out of scope for the first implementation.

The UI should be mobile-first because the core use case is quickly recording short guitar performances using a phone, tablet, laptop, or desktop browser.

The frontend should support two capture modes:

- `AUDIO_ONLY`
- `AUDIO_VIDEO`

Audio is always required because it is the primary transcription source.

Video is optional. It is used as an enhancement signal for future fretboard, fingering, and technique inference. The system must not attempt to generate tabs from video alone.

## 6. Recording Constraints

The first version should only support recording directly in the browser.

Existing audio or video file upload is out of scope for the first implementation.

The initial maximum recording duration should be 15 seconds.

The recording UI should provide guidance to improve analysis quality, such as:

- use a clean guitar tone
- avoid heavy distortion
- play slower for better transcription
- use good lighting when recording video
- keep the guitar neck visible when using video
- align the guitar neck within the on-screen guide

For video capture, the UI should eventually allow the user to align the guitar neck in frame. This may include a guide box or calibration area. The exact calibration UX should be defined in a later frontend or video spec.

## 7. Metronome and Tempo

The recording UI should support an optional metronome.

BPM is optional for simple non-rhythmic tab generation.

BPM is required only when rhythmic or quantised tab output is requested.

The first implementation should focus on non-rhythmic tab. Timing data should still be preserved internally so rhythmic tab can be added later.

Conceptual output modes:

### `TAB_ONLY`

The first supported output mode.

BPM is not required.

The output focuses on:

- detected note order
- pitch
- likely string/fret positions
- simple readable tab
- confidence and warnings where useful

### `RHYTHMIC_TAB`

Planned future mode.

BPM is required.

This mode may include:

- beat/bar calculation
- quantised note start times
- quantised durations
- rests
- ties
- rhythmic export support

## 8. Media Capture and Preparation

For `AUDIO_ONLY` sessions, the browser records an audio media asset.

For `AUDIO_VIDEO` sessions, the browser should record a single combined audio/video media asset where possible.

Using a combined media asset preserves sync between the audio and video tracks better than recording separate files.

The backend stores the original captured media in S3-compatible object storage.

For `AUDIO_VIDEO` sessions, the backend worker uses FFmpeg in the Java/Spring layer to extract a prepared audio asset from the combined recording.

This provides:

- one original source capture for sync
- a clean prepared audio asset for Basic Pitch
- a future video source for video analysis

FFmpeg usage should be wrapped behind a small backend interface so media preparation does not leak into domain logic.

Suggested backend abstraction:

- `MediaPreparationService`

Possible first implementation:

- `FfmpegMediaPreparationService`

Media preparation should happen in the background worker, not during the upload request.

## 9. Backend Responsibilities

The Spring backend owns product orchestration.

It is responsible for:

- receiving recording uploads
- validating recording metadata
- storing source media in S3-compatible storage
- creating recording/session/job state in Postgres
- preparing media assets with FFmpeg where needed
- calling analysis services
- combining analysis results
- running tab inference
- calculating combined confidence
- handling quantisation decisions
- generating exports
- storing export metadata
- exposing job status to the frontend

The backend should start as a modular monolith using Spring Boot and Spring Modulith boundaries where useful.

Do not split the backend into additional services unless a later spec explicitly decides to do so.

## 10. Python Audio Analyser

The audio analyser is a separate Python service because Basic Pitch is Python-based.

The Python audio analyser should remain deliberately small.

It is responsible only for:

- reading prepared audio from S3-compatible storage
- running Basic Pitch
- returning structured audio analysis results

It should not:

- generate tabs
- choose string/fret positions
- generate exports
- write to Postgres
- own job state
- make product decisions

The audio analyser should receive a prepared audio asset URI, not a combined audio/video media URI.

The exact REST API should be defined in a later OpenAPI spec.

Conceptual request fields:

- `sessionId`
- `audioUri`
- `contentType`
- `durationMs`

Conceptual response fields:

- note events
- MIDI-derived metadata
- confidence values where available
- warnings
- analysis metadata

## 11. Future Python Video Analyser

The video analyser is a planned future Python service.

It should analyse video and return timestamped visual or performance hints.

Possible future hints include:

- approximate hand position
- likely fret region
- fingering hints
- fretboard observations
- slide hints
- hammer-on hints
- pull-off hints
- bend hints
- confidence and warnings

The video analyser must not generate tabs.

The backend remains responsible for combining audio and video evidence into a final tab representation.

Likely future video technologies include:

- OpenCV for frame processing
- MediaPipe for hand landmarks
- manual fretboard calibration initially
- object detection later if required

Video analysis is not part of the first working audio pipeline, but the architecture should preserve a clean path for adding it.

## 12. Analysis Signals and Tab Inference

Riffle should not treat Basic Pitch output as the final tab.

The architecture separates analysis signals from tab inference.

First implementation:

- Audio analysis result -> tab inference engine -> tab document

Future video-enhanced implementation:

- Audio analysis result + video analysis result -> tab inference engine -> tab document

The backend should own a `TabInferenceEngine` abstraction.

Possible implementations over time:

- `SimpleTabInferenceEngine`
- `VideoAwareTabInferenceEngine`
- `TechniqueAwareTabInferenceEngine`

The first implementation should use a simple heuristic approach:

- take detected pitch
- find possible string/fret positions
- choose a simple playable position
- produce a basic tab document

More advanced playability, video-aware, and technique-aware inference should come later.

## 13. Export Strategy

Tab inference and export generation are separate responsibilities.

Tab inference produces an internal `TabDocument`.

Exporters convert a `TabDocument` into a specific output format.

The backend should own a `TabExporter` abstraction.

The first export format should be simple text tab.

Text tab is the initial validation and debug format. It proves that the system can move from recording to analysis to string/fret inference to a readable output.

Future exporters may include:

- MusicXML
- Guitar Pro-compatible output
- PDF or image export

MusicXML and Guitar Pro-compatible export are not required for the first implementation.

## 14. Processing Model

Processing is asynchronous from the frontend’s perspective.

The upload request should not wait for transcription, tab inference, or export generation to complete.

Initial flow:

1. Frontend uploads a recording session.
2. Backend stores source media.
3. Backend creates a job with status `PENDING`.
4. Backend returns a session/job ID immediately.
5. Frontend polls for status.
6. Backend worker claims pending jobs.
7. Backend processes the recording.
8. Backend marks the job `COMPLETED` or `FAILED`.

For the first implementation, the worker runs inside the same Spring Boot backend service.

External queues, topics, event buses, and separate worker services are out of scope for the first implementation.

The processing code should be structured so it could later move behind SQS or into a separate worker service if required.

Initial job statuses:

- `PENDING`
- `PROCESSING`
- `COMPLETED`
- `FAILED`

For the first implementation, failed jobs are not automatically retried.

Failures should be stored with a clear error code and a safe user-facing message.

## 15. Storage

Uploaded source media, derived media assets, and generated exports should be stored in S3-compatible object storage.

Postgres should store metadata and job state only.

Example S3 object categories:

- `recordings/{sessionId}/original.webm`
- `recordings/{sessionId}/prepared-audio.wav`
- `exports/{sessionId}/tab.txt`

The exact object key format should be defined later.

Generated text tab should also be stored in S3, even though it is small, so all generated exports follow the same storage model.

Postgres should store metadata such as:

- session ID
- job status
- media asset metadata
- export metadata
- object keys
- content types
- file sizes
- timestamps
- error codes
- safe error messages

Local S3-compatible development and testing should use LocalStack.

Integration tests that verify object storage behaviour should use Testcontainers with LocalStack where practical.

## 16. Retention

Riffle is intended to help users preserve short guitar ideas, exercises, and riffs.

Completed recording sessions should not be deleted unexpectedly.

For the proof-of-design implementation, automatic deletion is not required.

Retention settings should be configurable so future account, billing, storage-limit, or privacy policies can define how long media and generated exports are retained.

Failed or abandoned jobs may later use shorter retention periods, but this is not required for the first implementation.

## 17. Authentication, Authorisation, and Billing

Authentication, authorisation, and billing are not part of the initial proof-of-design implementation.

The first implementation should prove the core product pipeline:

- browser recording
- upload
- storage
- analysis
- tab inference
- export generation

Before production release, Riffle must add:

- user authentication
- ownership checks for sessions and exports
- usage limits
- billing or subscription support
- storage and account retention rules
- production monitoring

The data model should avoid blocking this later. Recording sessions and generated exports should be easy to associate with a user account when auth is added.

Do not introduce Cognito, Stripe, or production account management until the core design has been proven and explicitly requested.

## 18. Deployment Strategy

The first proof-of-design version should run locally.

Local development should support:

- React frontend
- Spring backend
- Python audio analyser
- future Python video analyser
- local Postgres
- LocalStack S3

After the core pipeline works locally, Riffle may be deployed to a private AWS test environment.

The private AWS test environment should not be treated as a public production release.

Temporary access protection may be used for early testing, such as:

- basic auth
- IP allowlist
- VPN
- private URL

Before any public production release, the system must add authentication, authorisation, billing or usage controls, retention policies, and production monitoring.

AWS is the preferred production hosting direction.

Likely future AWS components:

- S3
- RDS or Aurora PostgreSQL
- ECS Fargate for Spring backend
- ECS Fargate for Python services
- CloudFront or equivalent frontend hosting
- CloudWatch logging and monitoring

Do not introduce complex deployment automation before the product pipeline is proven.

## 19. First Implementation Target

The first implementation slice should be the Python audio analyser.

Reason:

- It is isolated.
- It is testable.
- It validates the riskiest technical assumption early.
- It proves whether Basic Pitch gives useful output for short guitar recordings.

Initial target:

- prepared audio file -> Python audio analyser -> Basic Pitch -> timestamped note events and MIDI-derived output

This should be specified separately before implementation.

Suggested spec:

- `specs/mvp/001-audio-analyser-basic-pitch.md`

## 20. Relationship to Domain Model

This architecture document intentionally does not fully define the domain model.

It only identifies likely domain concepts.

A separate domain model spec should define entity boundaries, fields, relationships, lifecycle rules, and persistence decisions.

Likely concepts:

- `RecordingSession`
- `MediaAsset`
- `AnalysisJob`
- `AudioAnalysisResult`
- `VideoAnalysisResult`
- `TabDocument`
- `GeneratedExport`

The next spec should be:

- `specs/domain-model.md`

## 21. Open Questions

The following decisions are intentionally left for other specs:

- Exact backend REST API shape.
- Exact audio-analyser REST API shape.
- Exact S3 object key structure.
- Exact Postgres schema.
- Exact frontend recording UX.
- Exact video calibration UX.
- Exact tab inference heuristic for V1.
- Exact text tab output format.
- Exact error codes.
- Exact local development Docker Compose setup.
- Exact AWS deployment shape.
