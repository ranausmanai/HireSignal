# AGENT.md

## Purpose

This project is a recruiter-facing interview feedback analysis app.

It does four main things:

1. Ingests interview feedback from PDFs, text, CSV, JSON, pasted text, or Greenhouse.
2. Normalizes that input into structured interview entries.
3. Runs deeper analysis and recruiter-oriented analytics on top of those entries.
4. Exposes a web UI with dashboards, Copilot chat, and HTML deck generation.

The current implementation is centered around `app.py` and a single-page frontend in `templates/index.html` plus `static/js/app.js`.

## Current Product Model

The app is no longer just a flat aggregate dashboard.

It now supports two source modes:

- Manual mode:
  PDF upload, text/CSV/JSON upload, or pasted feedback.
- Greenhouse mode:
  Harvest-style scorecard ingestion, with a realistic mock path available by typing `mock` as the API key.

The app also now has a dataset/workspace model:

- New uploads can create a new dataset.
- Uploads can merge into the active dataset.
- Uploads can replace all existing datasets.
- `All datasets` is an explicit aggregate scope.
- Greenhouse imports are intended to split by job scope when metadata is available.

This matters because recruiter workflows should not silently mix different roles, jobs, or hiring waves.

## LLM Model

The app can use a local CLI LLM backend.

Supported backends:

- `codex`
- `claude`

The current preferred default is:

- backend: `codex`
- model: `gpt-5.3-codex`
- reasoning: `medium`

The backend is configurable through environment variables, not hard-coded to Claude anymore.

Relevant env vars:

```bash
INTERVIEW_INSIGHTS_LLM_BACKEND=codex
INTERVIEW_INSIGHTS_CODEX_MODEL=gpt-5.3-codex
INTERVIEW_INSIGHTS_CODEX_REASONING=medium
```

## High-Level Runtime Flow

### Manual Upload Flow

1. User uploads PDFs/files or pastes text.
2. Backend parses the input locally.
3. PDFs are text-extracted first.
4. Entries are normalized into internal feedback rows.
5. Entries are assigned to a dataset/workspace.
6. `/api/data` runs deep analysis if needed.
7. Dashboard and Copilot operate on the active dataset scope.

### Greenhouse Flow

1. User enters a Harvest API key or `mock`.
2. Backend loads scorecards and candidate/application context.
3. Raw Greenhouse objects are normalized into internal entries.
4. Each entry keeps source metadata such as candidate/application/job identifiers.
5. Import is saved into one or more datasets.
6. Recruiter analytics and Copilot use the normalized entries, not raw Greenhouse JSON.

### Copilot Flow

1. User asks a question or requests a deck.
2. Backend builds a scoped context from the active dataset.
3. Only relevant analytics/fragments should be sent to the model when possible.
4. Chat is multi-turn for the browser tab session.
5. Deck generation returns a saved standalone HTML deck under `data/decks`.

## Important Files

### Backend

- `app.py`
  Main Flask app. Holds parsing, analytics, dataset management, Greenhouse ingestion, Copilot routes, deck generation, and persistence.

- `mock_greenhouse.py`
  Realistic mock Harvest-style data. Use this to develop Greenhouse flows without a live key.

### Frontend

- `templates/index.html`
  Main SPA shell and page markup.

- `static/js/app.js`
  Frontend state, routing, rendering, upload handling, Copilot UX, dataset manager, deck library, and settings actions.

- `static/css/style.css`
  Complete visual system for dashboard, recruiter UX, Copilot, waiting states, and settings/dataset management.

### Data

- `data/`
  Stores sessions, decks, uploads, and sample/session artifacts.

## Important Backend Concepts

### 1. `feedback_store`

Global in-memory source of truth for loaded feedback entries.

Each entry is a normalized record with fields such as:

- `candidate`
- `interviewer`
- `role`
- `decision`
- `score`
- `feedback_text`
- `date`
- `round_type`
- dataset metadata
- optional Greenhouse source metadata

### 2. Dataset State

Key globals:

- `dataset_registry`
- `active_dataset_id`

Key helpers:

- `create_dataset(...)`
- `rebuild_dataset_registry()`
- `assign_dataset_metadata(...)`
- `set_active_dataset(...)`
- `get_active_entries()`
- `build_dataset_summary()`
- `dataset_entries(...)`
- `ingest_grouped_entries(...)`

Use these instead of assuming all entries should always be analyzed together.

### 3. Deep Analysis

The app is designed so deep analysis is part of the normal experience, not an optional hidden step.

`/api/data` should ensure the active dataset has enriched analysis before returning recruiter-facing analytics.

### 4. Greenhouse Normalization

Do not send raw Greenhouse payloads directly to the LLM and hope for the best.

The correct pattern is:

1. Fetch Harvest objects.
2. Normalize them.
3. Keep stable identifiers.
4. Let the LLM enrich and interpret already-clean records.

Relevant functions in `app.py` include:

- `_greenhouse_get_json(...)`
- `_greenhouse_collect_pages(...)`
- `_greenhouse_application_context(...)`
- `map_greenhouse_scorecard(...)`
- `normalize_greenhouse_payload(...)`
- `fetch_greenhouse_harvest_data(...)`

## Important API Routes

### Core data

- `GET /api/data`
- `POST /api/upload`
- `POST /api/paste`
- `POST /api/reset`
- `DELETE /api/clear`

### Copilot

- `POST /api/chat`
- `POST /api/deck`
- `GET /api/decks`
- `GET /decks/<filename>`
- `DELETE /api/decks/<filename>`

### Sessions

- `POST /api/save`
- `GET /api/sessions`
- `POST /api/sessions/load`
- `DELETE /api/sessions/<filename>`
- `DELETE /api/sessions`

### Greenhouse

- `POST /api/greenhouse/connect`
- `POST /api/greenhouse/sync`
- `GET /api/greenhouse/status`

### Datasets

- `GET /api/datasets`
- `POST /api/datasets/select`
- `DELETE /api/datasets/<dataset_id>`
- `GET /api/datasets/compare`

## Frontend Page Intent

### Overview

This is the recruiter command center, not a generic analytics screen.

It should answer:

- What needs attention right now?
- Which pipeline is drifting?
- Which interviewer needs calibration?
- What should I say in the next sync?

### Add Feedback

This page should make ingestion simple and safe.

Users must be able to decide whether new input:

- creates a new dataset
- merges into the current dataset
- replaces all existing datasets

### Interview Team

This should focus on calibration, consistency, and interviewer-specific risk.

### Role Pipelines

This should focus on friction, blockers, and role-specific review pressure.

### Copilot

This should be a premium chat workspace for:

- multi-turn analysis
- recruiter questions
- HTML briefing deck generation
- reopening saved decks

### Settings

This is the control plane for:

- sessions
- datasets
- dataset comparison
- Greenhouse connection state

## Token and Context Strategy

Avoid sending large generic payloads to the model if targeted context will do.

Preferred approach:

1. Use active dataset scope first.
2. Build compact analytics summaries.
3. Pull only relevant entry fragments for the question.
4. Send recent thread history, not the full conversation forever.

Do not send raw PDFs or folders to the model.

PDFs should be parsed locally first, then reduced into structured entries and targeted context.

## What To Preserve

When editing this project, preserve these product decisions unless explicitly changed:

- Recruiter-first UX over generic analytics UX
- Dataset/workspace model over silent aggregation
- Greenhouse normalization before LLM enrichment
- Multi-turn Copilot within the open browser session
- Saved HTML deck outputs
- Premium waiting states for long-running model actions

## What Still Needs Care

Known areas that are improved but still not final:

- Full browser QA of every dataset interaction path
- Packaging for third-party installation
- True production deployment instead of Flask dev server
- Real Greenhouse tenant validation with a live Harvest key
- Possible future dataset rename/compare/history refinements

## Recommended Local Run Command

```bash
INTERVIEW_INSIGHTS_LLM_BACKEND=codex \
INTERVIEW_INSIGHTS_CODEX_MODEL=gpt-5.3-codex \
INTERVIEW_INSIGHTS_CODEX_REASONING=medium \
python app.py
```

Open:

```text
http://localhost:8021
```
