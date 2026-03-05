# IMPLEMENTATION.md — Commit-by-Commit Build Plan

When starting a new Claude Code session, read PROJECT.md first, then this file.
Tell Claude which commit you're working on and it will have full context.

The project starts from an **empty folder** containing only `.claude/PROJECT.md` and
`.claude/IMPLEMENTATION.md`. Claude Code will create the entire directory structure from scratch.

---

## Commit 1 — Project Scaffold

**Goal:** Repo compiles, Docker builds, health check returns 200.

Tasks:
- Create the full directory structure:
  ```
  app/
  ├── api/routes/
  ├── core/
  ├── db/
  ├── middleware/
  ├── repositories/
  ├── schemas/
  ├── services/
  ├── use_cases/
  └── main.py
  scripts/
  tests/
  .claude/
  ```
- `pyproject.toml` with Python 3.12, dependencies:
  `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`,
  `pydantic-settings`, `structlog`, `anthropic`, `python-multipart`
  Dev: `pytest`, `pytest-asyncio`, `httpx`
- `app/main.py` with `GET /health → {"status": "ok"}`
- `app/core/config.py` — pydantic-settings with fields:
  `DATABASE_URL`, `LLM_PROVIDER` (default: "anthropic"), `ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, `LOG_LEVEL` (default: "INFO")
- `app/core/db.py` — async engine + `AsyncSession` factory + `get_db` dependency
- `app/core/dependencies.py` — FastAPI `Depends` providers (settings, db, llm_service)
- `Dockerfile` — python:3.12-slim, non-root user, no dev dependencies in final image
- `docker-compose.yml`:
  - `api` service: builds from Dockerfile, env_file, depends_on postgres with healthcheck
  - `postgres` service: postgres:16-alpine, healthcheck with `pg_isready`
  - volumes for postgres data persistence
- `.env.example` — all vars with inline comments explaining each
- `Makefile` targets: `up`, `down`, `logs`, `shell`, `migrate`, `seed`, `test`, `lint`

Acceptance: `make up` → `curl localhost:8000/health` returns `{"status": "ok"}`

---

## Commit 2 — Patient Model + Migration

**Goal:** Patient table exists in DB, readable via SQLAlchemy.

Tasks:
- `app/db/models.py` — `Patient` ORM model:
  - `id`: UUID, primary key, default `uuid4`
  - `name`: String, not null
  - `dob`: Date, not null — kept as `dob` (established medical domain term; forcing `*_at` here would be semantically wrong since it's a date, not an event timestamp)
  - `mrn`: String, unique, not null (generated at repo layer, format: `MRN-XXXXXX`)
  - `created_at`: DateTime, server_default `now()`
  - `updated_at`: DateTime, onupdate `now()`
  - `deleted_at`: DateTime, nullable — soft delete marker. Rows with `deleted_at IS NOT NULL` are treated as deleted. All queries must filter `deleted_at == None` by default.
- Configure `alembic.ini` and `migrations/env.py` to use async engine and import all models
- Generate first migration: `alembic revision --autogenerate -m "create_patients_table"`
- `app/schemas/patient.py`:
  - `PatientCreate`: `name: str`, `dob: date`
  - `PatientUpdate`: `name: str | None`, `dob: date | None`
  - `PatientResponse`: all fields including `mrn`, `created_at`
  - `PaginatedPatients`: `items: list[PatientResponse]`, `total: int`, `page: int`, `per_page: int`

Acceptance: `make migrate` runs cleanly. `patients` table visible in DB.

---

## Commit 3 — Patients CRUD

**Goal:** Full CRUD for patients with pagination, sorting, and search.

Tasks:
- `app/repositories/patient_repository.py`:
  - `get_by_id(session, id: UUID) -> PatientResponse | None`
  - `get_all(session, page: int, per_page: int, sort_by: str, order: str, search: str | None) -> tuple[list[PatientResponse], int]`
  - `create(session, data: PatientCreate) -> PatientResponse`
  - `update(session, id: UUID, data: PatientUpdate) -> PatientResponse | None`
  - `delete(session, id: UUID) -> bool` — soft delete: sets `deleted_at = now()`, does not remove the row
  - All `get_*` methods must filter `Patient.deleted_at == None`
  - MRN generation: `f"MRN-{uuid4().hex[:6].upper()}"` on create
  - Search via `Patient.name.ilike(f"%{search}%")`
- `app/services/patient_service.py`:
  - `PatientService` injected with `PatientRepository`
  - Each method calls the repository; raises `HTTPException(404)` on not found
  - Business logic lives here (e.g. MRN uniqueness check on create)
- `app/use_cases/patient_use_cases.py`:
  - Thin wrappers injected with `PatientService`
  - Each method calls the corresponding service method and returns the result — no logic
- `app/api/routes/patients.py` — 5 endpoints:
  - `GET /patients?page=1&per_page=20&sort_by=name&order=asc&search=`
  - `GET /patients/{id}`
  - `POST /patients` → 201
  - `PUT /patients/{id}`
  - `DELETE /patients/{id}` → 204
- `app/middleware/logging.py` — structured middleware logging:
  `method`, `path`, `status_code`, `duration_ms` as JSON via structlog
- Register middleware and patients router in `main.py`

Acceptance: All 5 endpoints work correctly. Pagination, sorting, and search behave as expected.

---

## Commit 4 — Notes Model + CRUD

**Goal:** Notes can be created (JSON or file), listed, and deleted per patient.

Tasks:
- `app/db/models.py` — add `Note` ORM model:
  - `id`: UUID, primary key
  - `patient_id`: UUID, FK → patients.id, cascade delete
  - `content`: Text, not null
  - `note_type`: String, nullable (filled by LLM in Commit 5)
  - `source_filename`: String, nullable — stores original filename for file uploads
  - `taken_at`: DateTime with timezone, not null (user-supplied)
  - `created_at`: DateTime, server_default `now()`
  - `deleted_at`: DateTime, nullable — soft delete, same pattern as `Patient`
- Generate migration: `alembic revision --autogenerate -m "create_notes_table"`
- `app/schemas/note.py`:
  - `NoteCreate`: `content: str`, `taken_at: datetime`
  - `NoteResponse`: all fields
- `app/repositories/note_repository.py`:
  - `create(session, patient_id, data) -> NoteResponse`
  - `get_by_patient(session, patient_id) -> list[NoteResponse]`
  - `get_by_id(session, note_id) -> NoteResponse | None`
  - `delete(session, note_id) -> bool` — soft delete: sets `deleted_at = now()`
  - `update_note_type(session, note_id, note_type) -> None`
  - All `get_*` methods must filter `Note.deleted_at == None`
- `app/services/note_service.py`:
  - `NoteService` injected with `NoteRepository` only — does not touch `PatientRepository`
  - Patient existence validation is the Use Case's responsibility (call `PatientService.get_by_id` first)
- `app/use_cases/note_use_cases.py`:
  - Injected with `PatientService` + `NoteService`
  - On create: call `PatientService.get_by_id` → raises 404 if not found → then call `NoteService.create`
  - This is the correct place for cross-service orchestration
- `app/api/routes/notes.py`:
  - `POST /patients/{id}/notes` — accept JSON body OR `multipart/form-data` file upload
    - For file: read as UTF-8 text, store filename in `source_filename`
    - In production, binary files would go to S3; we store content in DB here for simplicity
    - `taken_at` accepted as query param or form field when using file upload
  - `GET /patients/{id}/notes`
  - `DELETE /patients/{id}/notes/{note_id}` → 204

Acceptance: Notes can be created as JSON and as file upload. Listed per patient. Soft-deleted cleanly.

---

## Commit 5 — LLM Service + Note Classification + Summary

**Goal:** Notes are classified on creation. Summary endpoint returns structured clinical narrative.

Tasks:
- `app/services/llm_service.py`:
  - `LLMService` Protocol: `classify_note`, `generate_summary`
  - `AnthropicLLMService`: uses `anthropic.AsyncAnthropic`, model `claude-sonnet-4-5`
  - `OpenAILLMService`: stub that raises `NotImplementedError` (shows extensibility)
  - `get_llm_service(settings) -> LLMService` factory
- Wire in `app/core/dependencies.py` as `get_llm_service_dep`
- **Note classification** — synchronous, called inside `NoteService.create` after the note is saved:
  - Call `LLMService.classify_note(content)` and immediately update `note_type` on the same response
  - Categories: `admission | follow_up | discharge | procedure | routine`
  - Tradeoff: adds ~1s latency to POST /notes. In production this is a natural fit for a background worker (Celery, ARQ) — noted in README under "What I'd add with more time"
  - `NoteService` receives `LLMService` as an injected dependency
- `app/use_cases/summary_use_case.py` — `GenerateSummaryUseCase`:
  - Injected with `PatientService`, `NoteService`, `LLMService` — no repositories
  1. Call `PatientService.get_by_id(id)` — raises 404 if not found
  2. Call `NoteService.get_by_patient(id)` — returns notes ordered by `taken_at` ASC
  3. Call `LLMService.generate_summary(patient, notes, audience, verbosity)`
  4. Return structured `SummaryResponse` — no parsing logic here, LLMService owns that
- `app/schemas/summary.py`:
  - `SummaryResponse`: `patient`, `summary`, `key_diagnoses`, `current_medications`, `note_count`, `generated_at`
- `app/api/routes/summary.py`:
  - `GET /patients/{id}/summary?audience=clinician&verbosity=standard`
- Register summary router in `main.py`

**Summary prompt:**
```
System:
You are a clinical documentation assistant. Given SOAP notes for a patient,
synthesize a structured summary. Respond ONLY with a valid JSON object with these exact fields:
- summary: string narrative
- key_diagnoses: list of strings
- current_medications: list of strings
Audience: {audience} ({audience_description}).
Verbosity: {verbosity} ({verbosity_description}).

User:
Patient: {name} | DOB: {dob} | MRN: {mrn}

Notes ({count} total, chronological):
{formatted_notes}
```

Acceptance: `GET /patients/1/summary` returns structured JSON. `?audience=family` returns plain-language summary.
`?audience=clinician&verbosity=brief` returns a short clinical summary.

---

## Commit 6 — Seed Script + Tests

**Goal:** `make seed` populates DB. Tests cover all major functionality without real API calls.

Tasks:
- Copy SOAP note files into `scripts/soap_notes/` (soap_01.txt through soap_06.txt)
- `scripts/seed.py`:
  - Patient 1 (unnamed, ID patient--001): notes from soap_01.txt + soap_02.txt + soap_03.txt
    - Use encounter dates from the files as `taken_at`
  - Patient 2 (Emily G. Williams, DOB 1996-12-02): notes from soap_04.txt + soap_05.txt + soap_06.txt
  - Script is idempotent: skip creation if patient with same name already exists
  - Called via `make seed` which runs `docker compose exec api python scripts/seed.py`
- `tests/conftest.py`:
  - Async test client using `httpx.AsyncClient`
  - In-memory SQLite or test PostgreSQL via env var
  - Mock `LLMService` that returns fixed JSON — injected via FastAPI dependency override
- `tests/test_patients.py`:
  - `test_health_check`
  - `test_create_patient`
  - `test_get_patient_by_id`
  - `test_get_patient_not_found`
  - `test_list_patients_pagination`
  - `test_list_patients_search`
  - `test_update_patient`
  - `test_delete_patient`
- `tests/test_notes.py`:
  - `test_create_note_json`
  - `test_create_note_file_upload`
  - `test_list_notes`
  - `test_delete_note`
  - `test_create_note_patient_not_found`
- `tests/test_summary.py`:
  - `test_summary_returns_structured_response` — asserts shape of response with mocked LLM
  - `test_summary_patient_not_found`
  - `test_summary_clinician_audience`
  - `test_summary_family_audience`

Acceptance: `make seed` + `make test` both pass cleanly.

---

## Commit 7 — README + Final Polish

**Goal:** Project is presentable. An unfamiliar engineer runs it in under 3 minutes.

Tasks:
- `README.md`:
  1. **Quick Start** — 3 commands from zero to running, including example curl for summary
  2. **API Reference** — all endpoints with curl examples and response shapes
  3. **Architecture** — ASCII diagram of layer flow + one-line responsibility per layer
  4. **Design Decisions & Tradeoffs** — prose on: async stack, clean architecture, ORM choice, LLM abstraction
  5. **What I'd add with more time** — honest list: cursor pagination, Redis cache, auth/RBAC, HIPAA audit log, full test coverage
  6. **Running Tests**
  7. **Environment Variables** — table of all vars with descriptions
- `.github/workflows/ci.yml` — skeleton: checkout, setup python, install deps, run pytest
- Final check: all endpoints return correct HTTP status codes, error responses have `detail` field

---

## Session Prompts (copy-paste into Claude Code)

**Commit 1:**
```
Read .claude/PROJECT.md and .claude/IMPLEMENTATION.md.
We are starting from an empty folder. Work on Commit 1 exactly as described.
Create the full directory structure and all files listed. Ask before making any decision not covered in the docs.
```

**Commit N (2-7):**
```
Read .claude/PROJECT.md and .claude/IMPLEMENTATION.md.
Commits 1 through {N-1} are complete. Work on Commit {N} exactly as described.
```
