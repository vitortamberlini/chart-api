FROM python:3.12-slim

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Install dependencies including dev extras (pytest, httpx, ruff)
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[dev]"

# Copy application source
COPY app/ app/
COPY scripts/ scripts/
COPY tests/ tests/
COPY alembic.ini .
COPY migrations/ migrations/

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
