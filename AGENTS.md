# Riffle AGENTS.md

## Purpose

This file defines how AI assistants should work in the Riffle repository.

Use it as shared guidance for Claude, Codex, and other coding agents.

This file is not a complete product specification. Feature behaviour, API contracts, acceptance criteria, and architecture decisions should live in `/specs`.

## Project Summary

Riffle is a guitar tab generation MVP.

The initial product flow is browser audio recording, upload to a Spring Boot backend, transcription by a Python Basic Pitch service, conversion into an internal guitar tab model, and export to an editable tab format.

The MVP should prioritise a working vertical slice over feature completeness.

Video recording and video-based analysis are intended for a later version and must not be implemented unless explicitly requested.

## Repository Structure

This is a monorepo.

Top-level areas:

- `riffle-backend`: Spring Boot / Spring Modulith backend.
- `riffle-frontend`: React / TypeScript / Vite frontend.
- `riffle-services/audio-analyser`: Python audio transcription service.
- `riffle-services/video-analyser`: future or placeholder video analysis service.
- `specs`: product specs, architecture notes, API decisions, and implementation plans.

Do not move responsibilities between these areas without explicit approval.

## Operating Rules

- Read the relevant spec in `/specs` before implementing.
- If no relevant spec exists, ask before implementing.
- Ask clarifying questions when requirements, architecture, or expected behaviour are unclear.
- Do not infer missing product decisions, business rules, API contracts, or architecture choices.
- If a spec conflicts with this file, stop and ask for clarification.
- Do not make architectural changes without explicit approval.
- Do not introduce new frameworks, services, queues, infrastructure, or persistence technologies without asking.
- Prefer the smallest useful reversible change.
- Do not rewrite unrelated code.
- Do not silently expand scope.
- Before editing, briefly state the intended approach.
- After editing, summarise changed files and tests run.
- If tests cannot be run, say why.

## Architecture Guardrails

- Prefer a modular monolith for the backend.
- Use Spring Modulith boundaries deliberately.
- Spring owns product orchestration.
- Python services perform specialist analysis only.
- The audio analyser returns structured transcription data, not product decisions.
- Keep tab conversion, export decisions, job orchestration, and product workflow in the backend unless a spec says otherwise.
- Avoid premature distributed-system complexity.
- Do not introduce queues, Kubernetes, event streaming, or complex deployment automation unless explicitly requested.
- Prefer explicit, understandable code over clever abstractions.
- Optimise for maintainability by a backend Java engineer who is not primarily a frontend developer.

## MVP Constraints

Unless a spec says otherwise:

- Six-string guitar only.
- Standard tuning only.
- Maximum recording duration is 60 seconds.
- BPM range is 40–240.
- Quantisation is optional.
- Text tab may be used for debugging or fallback export only.
- The main export should be editable in external guitar/tab software.
- Authentication, billing, collaboration, alternate tunings, seven-string guitars, and video analysis are out of scope for the initial MVP.

## Spec-Driven Workflow

Before implementing a feature:

1. Read the relevant spec in `/specs`.
2. Ask clarifying questions if anything is ambiguous.
3. Confirm the requested implementation slice.
4. Implement only what the spec requires.
5. Add or update tests.
6. Do not expand scope without updating the spec first.

Each feature spec should define:

- Purpose
- Scope
- Non-scope
- Inputs
- Outputs
- API contracts
- Data model changes
- Validation rules
- Error cases
- Acceptance criteria
- Tests required

## Coding Standards

General:

- Keep code simple and readable.
- Prefer small classes, functions, and components.
- Avoid speculative abstractions.
- Avoid large methods.
- Use clear domain names.
- Keep side effects at the edges.
- Prefer boring, obvious code over clever code.

Java / Spring:

- Use constructor injection.
- Keep controllers thin.
- Put business logic in application/domain services.
- Keep package and module boundaries aligned with Spring Modulith.
- Use DTOs for REST contracts.
- Do not expose persistence entities directly through API responses.
- Use Java records where appropriate.
- Write unit tests for domain logic.
- Write integration tests for API/database flows where useful.

React / TypeScript:

- Use functional components.
- Keep components small.
- Separate UI components from audio/business logic.
- Use explicit TypeScript types.
- Avoid unnecessary frontend libraries.
- Make the UI simple and usable before making it visually polished.

Python Services:

- Keep Python analysis services focused and minimal.
- Do not add product workflow logic to Python services.
- Return structured data with confidence/error information where available.
- Keep service APIs small and explicit.

## Testing Rules

Every meaningful feature should include tests.

Do not remove or weaken tests to make an implementation pass unless explicitly asked.

If adding tests is impractical for a change, explain why.

## Review Behaviour

When reviewing code:

- Review against the relevant spec.
- Separate blocking issues from suggestions.
- Be specific about files, risks, and suggested fixes.
- Do not invent requirements that are not in the spec.
- Ask clarifying questions instead of assuming intent.