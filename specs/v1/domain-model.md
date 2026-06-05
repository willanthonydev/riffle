# Riffle Domain Model Spec

## 1. Purpose

This document defines the first-pass domain model for Riffle.

The goal is to establish the core domain concepts, relationships, lifecycle rules, and storage responsibilities before implementation begins.

This is not a final database schema. Exact field types, table names, indexes, migrations, and JSON schemas should be defined in later implementation specs.

## 2. Modelling Principles

Riffle should favour a traceable domain model.

The system should make it possible to answer questions such as:

- Which user owns this recording session?
- Which media file was analysed?
- Which job produced this derived asset?
- Which analysis result was used to create this tab document?
- Which tab document produced this export?
- Which processing step failed?

Storage responsibilities are split as follows:

- Postgres stores metadata, ownership, lifecycle state, and traceability links.
- S3-compatible object storage stores media files, analysis JSON, tab document JSON, and generated exports.

The model should avoid over-modelling unstable internal data such as note events and tab notes as relational tables during the proof-of-design phase. These structures should live in JSON artefacts until they stabilise.

## 3. Core Concepts

The main domain concepts are:

- `RecordingSession`
- `MediaAsset`
- `ProcessingJob`
- `AnalysisResult`
- `TabDocument`
- `GeneratedExport`

Supporting concepts include:

- `RecordingSessionStatus`
- `ProcessingJobStatus`
- `ProcessingJobType`
- `CaptureMode`
- `OutputMode`
- `MediaAssetType`
- `AnalysisResultType`
- `ExportFormat`

## 4. RecordingSession

`RecordingSession` is the user-facing root concept.

It represents one short captured guitar performance.

A recording session may be audio-only or audio-plus-video. Audio is always required because it is the primary transcription source. Video is optional and used as an enhancement signal for future fretboard, fingering, and technique inference.

A recording session owns or links to:

- source and derived media assets
- processing jobs
- analysis results
- tab documents
- generated exports

### Responsibilities

`RecordingSession` answers:

> What did the user record, what options did they choose, who owns it, and what is its overall state?

### Suggested fields

- `id`
- `ownerUserId`
- `captureMode`
- `outputMode`
- `durationMs`
- `bpm`
- `metronomeEnabled`
- `quantisationRequested`
- `status`
- `createdAt`
- `updatedAt`
- `completedAt`
- `failedAt`

### Ownership

`ownerUserId` is required.

Authentication is not implemented in the proof-of-design version, but every session should still have an owner identity.

For local development, the backend may use a configured development owner ID, such as `local-dev-user`.

Before production, this must be replaced with the authenticated user identity.

Child records do not need their own owner field initially. Ownership for media assets, jobs, analysis results, tab documents, and exports should be enforced through their parent `RecordingSession`.

### Status

`RecordingSession` has its own user-facing status separate from individual processing job statuses.

Suggested initial statuses:

- `CREATED`
- `UPLOADED`
- `PROCESSING`
- `COMPLETED`
- `FAILED`

Meanings:

- `CREATED`: session record exists, but upload may not be complete.
- `UPLOADED`: source media is stored and processing can begin.
- `PROCESSING`: one or more processing jobs are pending or running.
- `COMPLETED`: final export is available.
- `FAILED`: the pipeline failed and no final export is available.

The exact transition rules should be defined in the processing implementation spec.

## 5. MediaAsset

`MediaAsset` represents metadata for a file stored in S3-compatible object storage.

It does not contain the media itself.

Examples include:

- original audio recording
- original combined audio/video recording
- prepared audio extracted by FFmpeg
- future prepared video asset

Generated tab exports are not modelled as `MediaAsset`; they are modelled as `GeneratedExport`.

### Responsibilities

`MediaAsset` answers:

> What media file exists in object storage, what kind of file is it, and where did it come from?

### Suggested fields

- `id`
- `recordingSessionId`
- `processingJobId`
- `assetType`
- `objectKey`
- `bucket`
- `contentType`
- `sizeBytes`
- `durationMs`
- `createdAt`

### Processing provenance

`processingJobId` is optional.

If `processingJobId` is null, the asset came directly from user upload.

If `processingJobId` is present, the asset was produced by a processing job.

Examples:

- `ORIGINAL_AUDIO` has `processingJobId = null`
- `ORIGINAL_AUDIO_VIDEO` has `processingJobId = null`
- `PREPARED_AUDIO` has `processingJobId = <media-preparation-job-id>`

### Suggested asset types

- `ORIGINAL_AUDIO`
- `ORIGINAL_AUDIO_VIDEO`
- `PREPARED_AUDIO`
- `PREPARED_VIDEO`

`PREPARED_VIDEO` is future-facing and should not be implemented until needed.

## 6. ProcessingJob

`ProcessingJob` represents one unit of background work in the processing pipeline.

Riffle should use multiple processing jobs per recording session rather than one large generic job.

Jobs are created one step at a time. When one job completes successfully, the backend creates the next required job.

### Responsibilities

`ProcessingJob` answers:

> What processing step is currently pending, running, completed, or failed?

### Suggested fields

- `id`
- `recordingSessionId`
- `jobType`
- `status`
- `sequenceNumber`
- `dependsOnJobId`
- `createdAt`
- `startedAt`
- `completedAt`
- `failedAt`
- `errorCode`
- `errorMessage`

### Initial job types

- `MEDIA_PREPARATION`
- `AUDIO_ANALYSIS`
- `TAB_INFERENCE`
- `EXPORT_GENERATION`

### Future job types

- `VIDEO_ANALYSIS`

### Job status

`ProcessingJob` uses a separate status enum from `RecordingSession`.

Suggested initial statuses:

- `PENDING`
- `PROCESSING`
- `COMPLETED`
- `FAILED`

Meanings:

- `PENDING`: job has been created but not claimed.
- `PROCESSING`: worker has claimed and started the job.
- `COMPLETED`: job finished successfully.
- `FAILED`: job failed and no later jobs should be created.

### Dependencies

`dependsOnJobId` is optional.

For the first implementation, the pipeline is linear, so a single previous-job dependency is sufficient.

Example:

- `MEDIA_PREPARATION` depends on nothing.
- `AUDIO_ANALYSIS` depends on `MEDIA_PREPARATION`.
- `TAB_INFERENCE` depends on `AUDIO_ANALYSIS`.
- `EXPORT_GENERATION` depends on `TAB_INFERENCE`.

Later, if audio and video analysis run in parallel, the model may need multiple job dependencies. Do not build that complexity until required.

### Outputs

Different job types produce different persisted outputs:

- `MEDIA_PREPARATION` produces `MediaAsset` records.
- `AUDIO_ANALYSIS` produces an `AnalysisResult`.
- `VIDEO_ANALYSIS` will produce an `AnalysisResult`.
- `TAB_INFERENCE` produces a `TabDocument`.
- `EXPORT_GENERATION` produces a `GeneratedExport`.

`ProcessingJob` should not have a single generic result field, because the output type varies by job type. Instead, output records should reference the job that produced them.

## 7. AnalysisResult

`AnalysisResult` represents metadata for an analysis output.

It is generic rather than split into separate `AudioAnalysisResult` and `VideoAnalysisResult` tables.

The full analysis payload is stored as JSON in S3-compatible object storage. Postgres stores metadata and traceability links.

### Responsibilities

`AnalysisResult` answers:

> What analysis was performed, which media asset was analysed, which job produced it, and where is the full result JSON?

### Suggested fields

- `id`
- `recordingSessionId`
- `processingJobId`
- `sourceMediaAssetId`
- `resultType`
- `resultObjectKey`
- `bucket`
- `modelName`
- `modelVersion`
- `overallConfidence`
- `warningsSummary`
- `createdAt`

### Result types

Initial result types:

- `AUDIO`
- `VIDEO`

`VIDEO` is future-facing and should not be implemented until the video analyser exists.

### Source media

`sourceMediaAssetId` is required.

Examples:

- audio analysis result references the `PREPARED_AUDIO` media asset.
- video analysis result may later reference `ORIGINAL_AUDIO_VIDEO` or `PREPARED_VIDEO`.

### Result JSON

The full result JSON should live in S3.

Example object categories:

- `analysis/{sessionId}/audio-analysis.json`
- `analysis/{sessionId}/video-analysis.json`

The exact object key format should be defined later.

### Note events

For the proof-of-design, detected note events should remain inside the analysis result JSON rather than being modelled as relational rows.

A future implementation may promote note events into relational tables if there is a clear need to query them directly.

## 8. TabDocument

`TabDocument` represents Riffle’s internal generated tab model.

It is the output of tab inference and the input to export generation.

It is not the same thing as a text tab, MusicXML file, or Guitar Pro-compatible file.

The full tab document is stored as JSON in S3-compatible object storage. Postgres stores metadata and traceability links.

### Responsibilities

`TabDocument` answers:

> What tab did Riffle infer from the available analysis signals?

### Suggested fields

- `id`
- `recordingSessionId`
- `processingJobId`
- `documentObjectKey`
- `bucket`
- `outputMode`
- `tuning`
- `stringCount`
- `overallConfidence`
- `warningsSummary`
- `createdAt`

### Relationship to RecordingSession

A `RecordingSession` may have many `TabDocument`s.

The first implementation will usually create one `TabDocument` per session, but the model should allow multiple tab documents.

This supports future cases such as:

- regenerated tabs
- improved inference algorithms
- video-enhanced tab versions
- rhythmic tab versions
- user-edited tab versions

### Relationship to AnalysisResult

A `TabDocument` should reference the `AnalysisResult` records used to infer it.

Because a tab document may use more than one analysis result, this should be modelled conceptually as a join relationship.

Suggested join concept:

`TabDocumentSourceAnalysis`

Fields:

- `tabDocumentId`
- `analysisResultId`

Examples:

- audio-only tab uses one audio analysis result.
- future audio-plus-video tab uses audio and video analysis results.

### Tab document JSON

The full tab document should live in S3.

Example object category:

- `tabs/{sessionId}/tab-document.json`

The exact JSON schema should be defined later.

### Tab notes

For the proof-of-design, tab notes should remain inside the tab document JSON rather than being modelled as relational rows.

A future implementation may promote tab notes into relational tables if there is a clear need.

## 9. GeneratedExport

`GeneratedExport` represents a downloadable or renderable artefact produced from a `TabDocument`.

Examples include:

- text tab
- MusicXML
- Guitar Pro-compatible file
- PDF or image export later

Generated exports are stored in S3-compatible object storage. Postgres stores metadata and traceability links.

### Responsibilities

`GeneratedExport` answers:

> What file was generated for the user, where is it stored, and which tab document produced it?

### Suggested fields

- `id`
- `recordingSessionId`
- `tabDocumentId`
- `processingJobId`
- `format`
- `objectKey`
- `bucket`
- `contentType`
- `sizeBytes`
- `createdAt`

### Relationships

A `GeneratedExport` must reference:

- the `RecordingSession` it belongs to
- the `TabDocument` it was generated from
- the `ProcessingJob` that produced it

`recordingSessionId` makes querying by session simple.

`tabDocumentId` preserves provenance.

`processingJobId` shows which export-generation job produced the file.

### Export formats

Initial format:

- `TEXT_TAB`

Future formats:

- `MUSIC_XML`
- `GUITAR_PRO`
- `PDF`
- `IMAGE`

Only `TEXT_TAB` is required for the first implementation.

## 10. Recording Options

Recording options may be modelled as fields on `RecordingSession` initially rather than a separate entity.

Suggested concepts:

- `captureMode`
- `outputMode`
- `bpm`
- `metronomeEnabled`
- `quantisationRequested`
- `durationMs`

For the first implementation:

- `captureMode` is `AUDIO_ONLY` or `AUDIO_VIDEO`.
- `outputMode` is `TAB_ONLY`.
- `bpm` is optional.
- `metronomeEnabled` is optional.
- `quantisationRequested` should be false or future-facing.
- maximum duration is 15 seconds.
- tuning is standard.
- string count is 6.

A later spec may introduce a separate `RecordingOptions` value object if the options become large or complex.

## 11. Video Calibration

Video calibration is future-facing.

It may later represent user-provided alignment metadata from the recording UI.

Possible concepts:

- neck guide box
- guitar orientation
- handedness
- fretboard start point
- fretboard end point
- calibration confidence

Do not implement this until the video capture and video analysis specs require it.

## 12. Conceptual Relationships

The first-pass relationship model is:

- `RecordingSession` 1:M `MediaAsset`
- `RecordingSession` 1:M `ProcessingJob`
- `RecordingSession` 1:M `AnalysisResult`
- `RecordingSession` 1:M `TabDocument`
- `RecordingSession` 1:M `GeneratedExport`
- `ProcessingJob` 1:M `MediaAsset` for derived media assets only
- `ProcessingJob` 1:0..1 `AnalysisResult`
- `ProcessingJob` 1:0..1 `TabDocument`
- `ProcessingJob` 1:0..1 `GeneratedExport`
- `AnalysisResult` M:1 `MediaAsset`
- `TabDocument` M:N `AnalysisResult`
- `TabDocument` 1:M `GeneratedExport`

Conceptual traceability chain:

1. `RecordingSession`
2. original uploaded `MediaAsset`
3. `ProcessingJob` of type `MEDIA_PREPARATION`
4. prepared audio `MediaAsset`
5. `ProcessingJob` of type `AUDIO_ANALYSIS`
6. `AnalysisResult` of type `AUDIO`
7. `ProcessingJob` of type `TAB_INFERENCE`
8. `TabDocument`
9. `ProcessingJob` of type `EXPORT_GENERATION`
10. `GeneratedExport`

## 13. Storage Summary

Postgres stores:

- recording session metadata
- owner ID
- lifecycle status
- media asset metadata
- processing job metadata
- analysis result metadata
- tab document metadata
- generated export metadata
- provenance links

S3-compatible object storage stores:

- original media files
- prepared media files
- analysis result JSON
- tab document JSON
- generated export files

This gives the system traceability while allowing JSON artefact shapes to evolve during early development.

## 14. Open Questions

The following are intentionally left for later specs:

- Exact database table names.
- Exact Java package/module boundaries.
- Exact field types and constraints.
- Exact S3 object key structure.
- Exact JSON schema for audio analysis results.
- Exact JSON schema for video analysis results.
- Exact JSON schema for tab documents.
- Exact generated text tab format.
- Exact error code enum.
- Exact processing status transition rules.
- Whether job dependencies eventually need to support multiple prerequisites.
- Whether note events or tab notes should ever be promoted into relational tables.
