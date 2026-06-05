# Test Review: MVP 001 Audio Analyser Basic Pitch

Note: `agents/test-reviewer.md` is not present in this repository. This review follows the test-review scope and finding format from the request.

## Findings

Severity: Low
File: `riffle-services/audio-analyser/tests/test_app.py:55`
Test gap:
The request validation tests cover missing `audioUri`, blank `sessionId`, invalid `audioUri`, unsupported content type, zero duration, and duration above 15 seconds, but they do not cover all required validation rules from the spec. In particular, there is no direct test for missing `sessionId`, missing `contentType`, missing `durationMs`, non-integer `durationMs`, or malformed `s3://` URIs without a bucket/object key.
Why it matters:
The current validation is mostly covered through representative examples, and FastAPI/Pydantic will reject the missing fields. Still, the spec lists these as explicit validation rules. A few additional tests would make future changes to request models less likely to weaken the API contract accidentally.
Suggested fix:
Add small API tests for missing `sessionId`, missing `contentType`, missing `durationMs`, non-integer `durationMs`, `s3://` with no bucket, and `s3://bucket` with no key. Keep assertions broad for validation messages if the exact Pydantic message is intentionally hidden.
Implementation agent instruction:
Extend `test_app.py` with focused invalid-request cases for the untested validation rules. Assert `400` and `INVALID_REQUEST`; do not assert exact framework validation text.

Severity: Low
File: `riffle-services/audio-analyser/tests/test_app.py:116`
Test gap:
`UNREADABLE_AUDIO` is tested for status and code, but unlike `UNSUPPORTED_CONTENT_TYPE`, `AUDIO_OBJECT_NOT_FOUND`, and `TRANSCRIPTION_FAILED`, it does not assert the expected safe message.
Why it matters:
The review-approved message assertions cover the requested representative errors, so this is not blocking. However, `UNREADABLE_AUDIO` is one of the explicit spec error cases, and checking the message would keep the error contract more consistent.
Suggested fix:
Add the expected message assertion to `test_unreadable_audio_maps_to_unreadable_audio`.
Implementation agent instruction:
Update the existing unreadable-audio test to assert message `"Prepared audio object could not be decoded."`.

Severity: Low
File: `riffle-services/audio-analyser/tests/test_app.py`
Test gap:
There is no direct API test for `STORAGE_READ_FAILED`.
Why it matters:
The spec includes `STORAGE_READ_FAILED` as an explicit error case for unexpected object-storage read failures. The storage wrapper maps unexpected S3/Boto errors to `StorageReadFailedError`, and the service maps that to `500`, but the service-level API path is not covered by a fake-storage test.
Suggested fix:
Add a fake-storage test that raises `StorageReadFailedError` and asserts `500`, `STORAGE_READ_FAILED`, and the safe message.
Implementation agent instruction:
Import `StorageReadFailedError` in `test_app.py`, set `fake_storage.error = StorageReadFailedError()`, and assert the mapped response.

Severity: Low
File: `riffle-services/audio-analyser/tests/test_storage.py:4`
Test gap:
S3 URI parsing has one positive test but no direct parser-level invalid URI tests.
Why it matters:
The API has invalid URI coverage, so behavior is protected at the route level. Since parsing is now a shared helper used by both validation and storage, direct negative tests would make that helper safer to change.
Suggested fix:
Add parser tests for non-`s3://` schemes, missing bucket, and missing object key.
Implementation agent instruction:
Extend `test_storage.py` or add `test_s3_uri.py` with invalid parser cases that assert `ValueError`.

Severity: Low
File: `riffle-services/audio-analyser/tests/test_localstack_integration.py:45`
Test gap:
The LocalStack integration test uploads `b"short wav fixture"` rather than an actual short WAV fixture.
Why it matters:
The test is still useful because it proves the REST path can read an object through S3-compatible storage without real AWS, and it intentionally uses a fake transcriber to avoid Basic Pitch. But the spec says integration tests should upload a small sample audio fixture. Using minimally valid WAV bytes would make the test closer to the specified prepared-audio path without making it depend on Basic Pitch.
Suggested fix:
Upload a tiny generated WAV byte fixture in the LocalStack test, or reuse the short WAV generator from the smoke test in byte form.
Implementation agent instruction:
Replace the placeholder bytes with valid short WAV bytes while keeping the fake transcriber and opt-in LocalStack behavior.

Severity: Low
File: `riffle-services/audio-analyser/tests/test_basic_pitch_smoke.py:18`
Test gap:
The Basic Pitch smoke test asserts the wrapper returns a model name and a list of notes, but it does not assert that the result can be converted into the response note-event shape as described in the spec.
Why it matters:
This is opt-in and not part of the fast test path, so it is not blocking. Still, the smoke test is meant to prove the wrapper output is usable by the service. A conversion assertion would better connect the real Basic Pitch wrapper to the response mapping used by the API.
Suggested fix:
After transcription, convert any returned notes through the existing response mapping helper or assert that the service can process a fake storage object with the real transcriber when Basic Pitch smoke is enabled.
Implementation agent instruction:
Update the smoke test to exercise conversion through `to_note_event()` for returned notes, or run the service path with a local fixture and real `BasicPitchTranscriber` if that remains practical.

## Overall Test Assessment

The implementation has solid fast-test coverage for the main API contract and keeps tests aligned with the service boundaries. Unit tests use fakes for S3 and Basic Pitch, so normal tests do not require real AWS or Basic Pitch. Health endpoint behavior, successful note-event mapping, unsupported content type, invalid requests, missing object mapping, unreadable audio mapping, Basic Pitch failure mapping, no-notes warning, and low-confidence warning are covered.

LocalStack integration support is opt-in with `RUN_LOCALSTACK_TESTS=1`, and README documents endpoint, bucket, region, and credentials. The Basic Pitch smoke test is also opt-in with `RUN_BASIC_PITCH_SMOKE=1`, and Basic Pitch remains an optional dependency. Python 3.10 expectations are clear in `pyproject.toml` and README test commands.

The remaining gaps are mostly completeness gaps against the explicit validation/error matrix and making the opt-in tests closer to the spec wording.

## Blocking Test Gaps

None.

## Non-Blocking Suggestions

- Add invalid-request tests for the remaining required validation rules.
- Add API coverage for `STORAGE_READ_FAILED`.
- Assert the `UNREADABLE_AUDIO` safe message.
- Add direct negative tests for the shared S3 URI parser.
- Use valid WAV bytes in the LocalStack integration test.
- Make the Basic Pitch smoke test prove conversion into the response note-event shape.

## Tests Expected Before Commit

Run the normal fast suite under Python 3.10:

```bash
cd riffle-services/audio-analyser
python3.10 -m venv .venv
. .venv/bin/activate
python3.10 -m pip install -e '.[test]'
python3.10 -m pytest
```

Optional before merging the slice, when the local dependencies are available:

```bash
RUN_LOCALSTACK_TESTS=1 python3.10 -m pytest -m integration
python3.10 -m pip install -e '.[basic-pitch]'
RUN_BASIC_PITCH_SMOKE=1 python3.10 -m pytest -m basic_pitch
```

## Acceptable To Proceed

Yes. The implementation is acceptable to proceed from a test-coverage perspective. The listed gaps are non-blocking and can be addressed in a cleanup pass or before finalizing the MVP slice.
