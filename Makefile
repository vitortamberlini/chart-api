.PHONY: up down logs shell migrate seed test lint

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api

shell:
	docker compose exec api bash

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python scripts/seed.py

test:
	docker compose exec api python -m pytest tests/ -v

lint:
	.venv/bin/ruff check app/ tests/
