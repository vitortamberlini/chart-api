FROM python:3.12-slim

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Install dependencies (no dev extras)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application source
COPY app/ app/
COPY scripts/ scripts/
COPY alembic.ini .
COPY migrations/ migrations/

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
