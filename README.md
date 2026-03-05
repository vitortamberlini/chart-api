# Healthcare Data Processing API

A clinical data API that ingests SOAP notes, classifies them with an LLM, and generates audience-aware patient summaries. Built as a take-home assignment for Ascertain.

---

## Quick Start

```bash
cp .env.example .env          # add your ANTHROPIC_API_KEY
make up                       # build + start (api + postgres)
make migrate                  # run Alembic migrations
make seed                     # create 2 patients with 6 SOAP notes each
```

Then generate a summary:

```bash
# 1. List patients to get an ID
curl http://localhost:8000/patients

# 2. Get a clinical summary
curl "http://localhost:8000/patients/<id>/summary?audience=clinician&verbosity=standard"
```

Expected response:

```json
{
  "patient": { "id": "...", "name": "James R. Mitchell", "dob": "1955-04-12", "mrn": "MRN-3AC7DE" },
  "summary": "68-year-old male admitted for inferior STEMI...",
  "key_diagnoses": ["Inferior STEMI", "Hypertension", "Hyperlipidemia"],
  "current_medications": ["Aspirin 81mg", "Atorvastatin 80mg", "Metoprolol 25mg"],
  "note_count": 3,
  "generated_at": "2024-06-20T10:00:00Z"
}
```

---

## API Reference

All endpoints are under `http://localhost:8000`. Error responses always include a `detail` field.

### Health

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/health` | 200 | Returns `{"status": "ok"}`. Pings the database. |

### Patients

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/patients` | 200 | List patients (paginated, sortable, searchable) |
| POST | `/patients` | 201 | Create a patient |
| GET | `/patients/{id}` | 200 | Get a patient by ID |
| PUT | `/patients/{id}` | 200 | Update a patient |
| DELETE | `/patients/{id}` | 204 | Soft-delete a patient |

**List patients** — query params: `page` (default 1), `per_page` (default 20, max 100), `sort_by` (`name`\|`created_at`\|`dob`), `order` (`asc`\|`desc`), `search` (partial name match).

```bash
curl "http://localhost:8000/patients?page=1&per_page=5&search=Mitchell"

curl -X POST http://localhost:8000/patients \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Carter", "dob": "1980-03-15"}'

curl -X PUT http://localhost:8000/patients/<id> \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Carter-Smith"}'

curl -X DELETE http://localhost:8000/patients/<id>
```

**Patient response shape:**
```json
{
  "id": "uuid",
  "name": "Alice Carter",
  "dob": "1980-03-15",
  "mrn": "MRN-A1B2C3",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null,
  "deleted_at": null
}
```

### Notes

Notes belong to a patient. The `note_type` field is set automatically via LLM classification on creation.

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/patients/{id}/notes` | 200 | List notes for a patient |
| POST | `/patients/{id}/notes` | 201 | Create a note (JSON or file upload) |
| DELETE | `/patients/{id}/notes/{note_id}` | 204 | Soft-delete a note |

**Create note — JSON body:**
```bash
curl -X POST http://localhost:8000/patients/<id>/notes \
  -H "Content-Type: application/json" \
  -d '{
    "content": "SUBJECTIVE: Patient presents for follow-up...",
    "taken_at": "2024-01-15T10:00:00Z"
  }'
```

**Create note — file upload (multipart/form-data):**
```bash
curl -X POST http://localhost:8000/patients/<id>/notes \
  -F "file=@/path/to/soap_note.txt" \
  -F "taken_at=2024-01-15T10:00:00Z"
```

`taken_at` may also be passed as a query param (`?taken_at=2024-01-15T10:00:00Z`) or omitted (defaults to now).

**Note response shape:**
```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "content": "SUBJECTIVE: ...",
  "note_type": "follow_up",
  "source_filename": "soap_note.txt",
  "taken_at": "2024-01-15T10:00:00Z",
  "created_at": "2024-01-15T10:00:01Z",
  "deleted_at": null
}
```

**Note types** (assigned by LLM): `admission` | `follow_up` | `discharge` | `procedure` | `routine`

### Summary

```bash
GET /patients/{id}/summary?audience=clinician&verbosity=standard
```

| Param | Values | Default |
|-------|--------|---------|
| `audience` | `clinician`, `family` | `clinician` |
| `verbosity` | `brief`, `standard`, `detailed` | `standard` |

```bash
# Clinician brief
curl "http://localhost:8000/patients/<id>/summary?audience=clinician&verbosity=brief"

# Family-friendly standard
curl "http://localhost:8000/patients/<id>/summary?audience=family"
```

**Summary response shape:**
```json
{
  "patient": { "id": "...", "name": "...", "dob": "...", "mrn": "..." },
  "summary": "Narrative text...",
  "key_diagnoses": ["Diagnosis A", "Diagnosis B"],
  "current_medications": ["Med A 10mg daily"],
  "note_count": 3,
  "generated_at": "2024-06-20T10:00:00Z"
}
```

---

## Running Tests

Tests run inside Docker against a dedicated `chartapi_test` database. The LLM is mocked — no API credits needed.

```bash
make test
```

The test suite (17 tests) covers:
- Patient CRUD (list, create, get, update, delete, pagination, search, 404)
- Note creation via JSON and file upload, listing, deletion, and patient-not-found guard
- Summary structured response, 404, and both audience variants

---

## Architecture

```
HTTP Request
     │
     ▼
┌──────────┐
│  Routes  │  Parse request, call one use case, return HTTP response
└──────────┘
     │
     ▼
┌───────────┐
│ Use Cases │  Sequence service calls. No business logic. Cross-service orchestration.
└───────────┘
     │
     ▼
┌──────────┐
│ Services │  Business logic. Each service owns one domain concern.
│          │  Defined as Protocol → fully mockable in tests.
└──────────┘
     │
     ▼
┌──────────────┐
│ Repositories │  DB queries only. Returns Pydantic schemas. No logic.
└──────────────┘
     │
     ▼
┌────────────┐
│ PostgreSQL │
└────────────┘
```

**Dependencies flow one direction only. No layer skipping. No reversing.**

| Layer | File(s) | Responsibility |
|-------|---------|----------------|
| Routes | `app/api/routes/` | HTTP parsing and response. One use case call per endpoint. |
| Use Cases | `app/use_cases/` | Dumb sequencing of service calls. Raises HTTPException on flow errors. |
| Services | `app/services/` | Business logic. `PatientService`, `NoteService`, `LLMService` (Protocol). |
| Repositories | `app/repositories/` | SQLAlchemy queries. Soft-delete filtering. Returns Pydantic models. |
| Core | `app/core/` | Config (pydantic-settings), DB engine, FastAPI dependency providers. |
| Middleware | `app/middleware/` | Structured JSON request/response logging via structlog. |

---

## Design Decisions & Tradeoffs

### Async stack (FastAPI + SQLAlchemy async + asyncpg)

The entire stack is async end-to-end. FastAPI is async-native; SQLAlchemy 2.0 supports async sessions via `asyncpg`; all I/O (DB, LLM API) is non-blocking. This means one worker thread can handle many concurrent requests while waiting on Postgres or the Anthropic API — the two dominant latency sources in this system.

Tradeoff: async code is harder to debug and test. pytest-asyncio requires explicit event loop scope configuration; SQLAlchemy async has subtle differences from sync (e.g. `expire_on_commit=False` is required with `async_sessionmaker`).

### Clean architecture (strict layer separation)

Routes → Use Cases → Services → Repositories. Each layer has a single, well-defined responsibility. This was a deliberate overengineering choice for a take-home project, but it pays off in production:

- Services are `Protocol`-typed, so the test suite mocks `LLMService` without touching the HTTP layer or database.
- Adding a new LLM provider means implementing a Protocol — no other layer changes.
- Moving classification to a background worker (Celery/ARQ) only touches the Use Case layer.

Tradeoff: more files and indirection than a typical small project warrants. The right call for a codebase with a team and a 2-year horizon.

### SQLAlchemy ORM (not raw SQL)

ORM models are the single source of truth for both Alembic migrations (auto-generated via `--autogenerate`) and runtime queries. Type-safe column references, built-in pagination helpers, and consistent soft-delete filtering justify the abstraction cost.

Tradeoff: ORM can generate surprising SQL for complex analytical queries. Mitigation: `echo=True` in development, `.explain()` when needed. None of the queries here get complex enough to matter.

### LLM abstraction via Protocol

`LLMService` is a structural Protocol. `AnthropicLLMService` and `OpenAILLMService` implement it without inheriting from it. The test suite's `MockLLMService` implements the same interface without touching any infrastructure. Provider selection happens in `dependencies.py` at request time via `LLM_PROVIDER` env var.

### Soft deletes

Deleted patients and notes are never removed from the database. All queries filter `deleted_at IS NULL`. This is standard in healthcare systems where audit trails and data recovery requirements make hard deletes inappropriate.

### Synchronous LLM classification on note creation

`POST /notes` calls the LLM to classify the note type before returning. This adds ~1s of latency to the response. The tradeoff: simplicity. In production, this is a natural fit for a background worker (Celery, ARQ) — the `note_type` field would be `null` until classification completes, and the client would poll or receive a webhook.

---

## What I'd Add With More Time

| Item | Why |
|------|-----|
| **Authentication / RBAC** | HIPAA mandates access controls on PHI. OAuth2 + JWT with role-based permissions. Not optional in production. |
| **HIPAA audit log** | Every read/write on patient data must be logged with user identity, timestamp, and action. Typically a separate append-only table or external audit sink. |
| **Async note classification** | Move LLM classification to a background worker (Celery or ARQ) to eliminate the ~1s latency on `POST /notes`. |
| **Cursor-based pagination** | `limit/offset` drifts during concurrent writes. Cursor-based pagination on `(created_at, id)` is consistent. |
| **Summary caching (Redis)** | Cache summary responses by hash of `(patient_id, note_ids, audience, verbosity)`. Avoid redundant LLM calls on re-fetches. |
| **S3 file storage** | File content is stored in Postgres for simplicity. In production, binary files (PDFs, scanned documents) belong in S3 or equivalent object storage. |
| **PDF / OCR support** | Accept scanned PDFs via Tesseract. Most real clinical notes aren't plain text. |
| **Structured logging + observability** | Ship structlog JSON to a log aggregator (Datadog, Loki). Add OpenTelemetry traces. |
| **Full integration test coverage** | The current test suite mocks the LLM. A separate integration test suite should validate real LLM output shape (key fields present, JSON valid). |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL async connection string (`postgresql+asyncpg://...`) |
| `LLM_PROVIDER` | No | `anthropic` | LLM backend: `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` | If `LLM_PROVIDER=anthropic` | `""` | Anthropic API key |
| `OPENAI_API_KEY` | If `LLM_PROVIDER=openai` | `""` | OpenAI API key |
| `LOG_LEVEL` | No | `INFO` | Logging level. Set to `DEBUG` to enable SQLAlchemy query echo. |

Copy `.env.example` to `.env` and fill in the required values before running `make up`.
