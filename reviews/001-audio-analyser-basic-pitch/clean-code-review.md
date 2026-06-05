# Clean Code Review: MVP 001 Audio Analyser Basic Pitch

## Findings

Severity: Medium
File: `riffle-services/audio-analyser/audio_analyser/app.py:62`
Issue:
The analyse-audio endpoint runs the synchronous `AudioAnalysisService.analyse()` method directly inside an `async def` FastAPI handler.
Why it matters:
The current structure is simple, but it mixes an async FastAPI boundary with blocking file, S3, and Basic Pitch work. For a Java/Spring developer, this is easy to miss because the endpoint looks asynchronous even though the implementation is fully blocking. It also makes the service boundary less explicit: the app layer appears non-blocking while the service layer is blocking by design.
Suggested fix:
Make the endpoint a normal synchronous FastAPI handler (`def analyse_audio(...)`) or explicitly run the blocking work through FastAPI/Starlette's threadpool helper. The synchronous handler is the simpler option and better matches the current service design.
Implementation agent instruction:
Change `async def analyse_audio(...)` to `def analyse_audio(...)` unless there is a concrete reason to keep an async route. Keep service behavior and response shape unchanged.

Severity: Low
File: `riffle-services/audio-analyser/audio_analyser/app.py:63`
Issue:
The spec asks for logs around request receipt, audio download start/completion, Basic Pitch analysis start/completion, and errors. The implementation currently logs request receipt and mapped failures only; download and transcription step logs are absent.
Why it matters:
This is not a product behavior problem, but it weakens maintainability and local debugging for the first risky integration point. The service is intentionally small, so a few explicit logs around the two external boundaries would help future maintainers understand where failures happen.
Suggested fix:
Add simple logs in `AudioAnalysisService.analyse()` before/after `read_audio()` and before/after `transcribe()`, using `sessionId` and safe messages only.
Implementation agent instruction:
Add four straightforward info logs in the service layer: download start, download complete, Basic Pitch start, Basic Pitch complete. Do not log credentials, object bytes, local temp paths, or exception dumps.

Severity: Low
File: `riffle-services/audio-analyser/audio_analyser/models.py:25` and `riffle-services/audio-analyser/audio_analyser/storage.py:16`
Issue:
S3 URI parsing is duplicated. The request model validates bucket/key by manually splitting the URI, and the storage layer separately parses the same URI.
Why it matters:
The duplication is small, but it creates two places to keep URI interpretation consistent. This is exactly the kind of small drift that can confuse a future Java/Spring maintainer when one layer accepts a URI that another layer parses differently.
Suggested fix:
Use one shared `parse_s3_uri()` helper for both validation and storage, or keep validation minimal in the model and let the storage parser be the single source of bucket/key parsing.
Implementation agent instruction:
Consolidate S3 URI parsing into one helper. If importing storage from models would create an awkward dependency, move `S3Location` and `parse_s3_uri()` into a small neutral module such as `audio_analyser.s3_uri`.

Severity: Low
File: `riffle-services/audio-analyser/audio_analyser/basic_pitch_wrapper.py:60`
Issue:
`normalize_note_events()` accepts several guessed dict keys and tuple shapes for Basic Pitch output.
Why it matters:
The wrapper is isolated, which is good, but the permissive mapping hides uncertainty about the actual Basic Pitch return shape. That makes the code harder to reason about and can silently drop or misinterpret events if Basic Pitch returns something unexpected. The spec asks for simple, explicit code and a Basic Pitch wrapper, not a broad adapter for many possible schemas.
Suggested fix:
Once the exact Basic Pitch package/version is pinned, narrow this mapper to the actual observed output shape and keep only compatibility branches that tests prove are needed.
Implementation agent instruction:
Do not expand the mapper further. After the Basic Pitch version is chosen, replace the guessed key list with explicit mapping for that version's output and update the wrapper tests accordingly.

Severity: Low
File: `riffle-services/audio-analyser/tests/test_app.py:177`
Issue:
`assert_error()` copies the response's own error message back into the expected object instead of asserting a specific message.
Why it matters:
This keeps tests focused on error codes and status, but it also means the documented safe human-readable messages can drift accidentally. Since the spec calls for clear errors, checking the message in at least a few representative cases would make the API contract easier to maintain.
Suggested fix:
Either pass the expected message into `assert_error()` or add targeted assertions for representative messages such as `UNSUPPORTED_CONTENT_TYPE`, `AUDIO_OBJECT_NOT_FOUND`, and `TRANSCRIPTION_FAILED`.
Implementation agent instruction:
Strengthen `assert_error()` so it verifies the expected message text for mapped service errors. Keep validation-message tests broad if exact Pydantic validation details are intentionally hidden.

## Overall Summary

The implementation is small, readable, and generally well separated. FastAPI boundary code, request/response models, S3 loading, Basic Pitch wrapping, service orchestration, config, and errors each live in focused modules. The code stays within the major spec boundaries: it does not generate tabs, choose string/fret positions, call Spring, write to Postgres, or own job state.

Basic Pitch and S3 are isolated behind small wrappers, and the unit tests use fakes cleanly. The implementation should be understandable to a Java/Spring developer with limited Python experience. The main clean-code concern is not over-engineering; it is a handful of small clarity issues around sync/async boundaries, duplicated S3 URI parsing, and making wrapper assumptions more explicit once the Basic Pitch version is pinned.

## Blocking Issues

None.

## Non-Blocking Suggestions

- Prefer a synchronous FastAPI route for the blocking analyse-audio path.
- Add explicit service-layer logs around S3 download and Basic Pitch transcription steps.
- Consolidate S3 URI parsing into one helper.
- Narrow Basic Pitch output normalization after the exact package/version is pinned.
- Strengthen error-response tests to assert representative message text.

## Acceptable To Proceed

Yes. The implementation is acceptable to proceed, with the findings above treated as non-blocking cleanup before or during the next implementation pass.
