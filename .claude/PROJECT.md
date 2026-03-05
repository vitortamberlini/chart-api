# PROJECT.md — Healthcare Data Processing API

## Context

This is a take-home assignment for Ascertain, a healthcare AI company that builds LLM-powered agents
to automate administrative workflows for care teams (prior authorizations, discharge planning, etc.).

The project must work on the first try. Running `make up` followed by `GET /patients/1/summary` should
produce a coherent clinical narrative. Code quality and documentation should reflect production-grade thinking.

---

## Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.12 | Latest stable. Mature asyncio, improved performance, `tomllib` native |
| Framework | FastAPI | Required by assignment. Async-native, Pydantic v2 built-in |
| Database | PostgreSQL | Production-grade, supports `pg_trgm` for fuzzy search, JSONB for future needs |
| ORM | SQLAlchemy 2.0 (async) | See ORM decision below |
| Migrations | Alembic | Never use `create_all()` in production. Alembic is the standard |
| Validation | Pydantic v2 | Already bundled with FastAPI, strict typing |
| Settings | pydantic-settings | 12-factor config via `.env` |
| LLM | Anthropic SDK (default) | Configurable via `LLM_PROVIDER` env var |
| Logging | structlog | JSON-structured logs, easy to ship to any log aggregator |
| Containerization | Docker + docker-compose | As required |

---

## Python Style

- Use modern union syntax everywhere: `int | None`, `str | None`, `list[str]`, `tuple[X, Y]`
- Never use `Optional`, `Union`, `List`, `Dict`, `Tuple` from `typing`
- All functions and methods must have type annotations on parameters and return types

---

## Architecture — Strict Layered Flow

Dependencies flow in **one direction only**, with **no layer skipping**, in a strict linear chain:

```
HTTP Request
     ↓
  Routes        → HTTP only. Parse request, call use case, return response.
     ↓
 Use Cases      → Dumb orchestration only. Sequences service calls. No business logic.
     ↓
 Services       → Business logic lives here. Calls its own Repository.
     ↓
Repositories    → DB only. SQLAlchemy queries, no logic.
```

### Layer responsibilities

**`api/routes/`**
- HTTP only: parse request body/params, call one use case, return response.
- No business logic. No direct calls to services or repositories.

**`use_cases/`**
- Pure sequencing. Calls one or more Services in order and composes their results.
- Contains no business logic — if you find an `if` here that isn't about control flow, it belongs in a Service.
- Raises `HTTPException` for flow errors (e.g. patient not found returned by a service).
- Example — `GenerateSummaryUseCase`:
  ```python
  patient = await self.patient_service.get_by_id(id)
  notes   = await self.note_service.get_by_patient(id)
  return  await self.llm_service.generate_summary(patient, notes, audience, verbosity)
  ```

**`services/`**
- Business logic lives here. Each service owns one domain concern.
- Services with persistence call their own Repository (1:1). `PatientService` → `PatientRepository`.
- Services without persistence (e.g. `LLMService`) call external APIs instead.
- Defined as `Protocol` so they can be mocked in tests without touching infrastructure.
- Services do NOT call other Services.

**`repositories/`**
- DB concerns only. SQLAlchemy queries, pagination, filtering. No business logic.
- Return Pydantic schemas, never raw ORM objects (convert at the boundary with `.model_validate()`).
- One repository per aggregate: `PatientRepository`, `NoteRepository`.

**`middleware/`**
- Cross-cutting concerns only. Structured request/response logging (method, path, status, duration_ms).

**`core/`**
- Application bootstrap: `config.py` (pydantic-settings), `db.py` (async engine + session factory), `dependencies.py` (FastAPI `Depends` providers).

### The rule in one sentence
> Routes call Use Cases. Use Cases call Services. Services call Repositories. No skipping, no reversing.

---

## ORM Decision — SQLAlchemy ORM (not raw SQL)

**Decision:** Use SQLAlchemy 2.0 ORM with async session.

**Rationale:**
- Type safety: ORM models are Python objects — no string-based column references
- Consistency with Alembic: migrations are auto-generated from the same model definitions
- The queries in this domain (filters, joins, ordering) are straightforward — ORM handles them cleanly
- Reduces boilerplate for pagination, ordering, and filtering

**Known tradeoff (documented consciously):**
ORM abstracts the generated SQL. For complex analytical queries, this can produce surprising results.
The mitigation is to log all SQL in development (`echo=True` on the engine) and use `.explain()` when needed.
For this domain, the queries never get complex enough to matter.

---

## LLM Provider Design

Provider is selected at runtime via `LLM_PROVIDER` env var.

```
LLM_PROVIDER=anthropic   → uses anthropic SDK (default)
LLM_PROVIDER=openai      → uses openai SDK
```

Both providers implement the same `LLMService` Protocol:

```python
class LLMService(Protocol):
    async def generate_summary(self, prompt: str) -> str: ...
    async def classify_note(self, content: str) -> str: ...
```

This allows swapping providers without touching use cases or routes.
It also means `LLMService` can be fully mocked in tests without any API calls.

---

## Summary Endpoint Design

`GET /patients/{id}/summary?audience=clinician&verbosity=standard`

**audience** (optional, default: `clinician`)
- `clinician` → clinical language, diagnoses, medications, labs, plan
- `family` → plain language, no jargon, empathetic tone

**verbosity** (optional, default: `standard`)
- `brief` → 2-3 sentence overview
- `standard` → full narrative with sections
- `detailed` → include timeline of all encounters

Response structure:
```json
{
  "patient": { "name": "...", "dob": "...", "mrn": "..." },
  "summary": "...",
  "key_diagnoses": ["..."],
  "current_medications": ["..."],
  "note_count": 6,
  "generated_at": "2024-06-20T10:00:00Z"
}
```

---

## Explicitly Out of Scope

These are conscious decisions, not omissions. Each is mentioned in the README.

| Item | Why it's out |
|---|---|
| Authentication / RBAC | Not required by assignment. In production: critical — HIPAA mandates access controls on PHI. Would use OAuth2 + JWT with role-based permissions. |
| Cursor-based pagination | `limit/offset` is sufficient for this data size. At scale, cursor-based is preferable for consistency during concurrent writes. Documented tradeoff. |
| Summary caching (Redis) | Adds a service dependency. In production: cache by hash of note IDs + content to avoid redundant LLM calls. |
| File storage (S3) | File uploads are stored as text content in the DB for simplicity. In production, binary files (PDFs, images) belong in S3 or equivalent object storage — this is a document processing system, not a file management system. |
| Async note classification | LLM classification runs synchronously on note creation for simplicity. In production, this is a natural fit for a background worker (Celery, ARQ) to avoid adding latency to the POST response. |
| PDF / handwritten notes | OCR (Tesseract) is a heavy dependency with diminishing return for the 2h scope. |
| CI/CD pipeline | A skeleton `.github/workflows/ci.yml` is sufficient to show intent. |
| Kubernetes / Prometheus | Overkill for local take-home. Mentioned in README as next steps. |
| Note updates (PUT) | Explicitly stated as unnecessary in the assignment spec. |
