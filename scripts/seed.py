#!/usr/bin/env python3
"""
Seed script: creates two patients with clinical SOAP notes.
Idempotent — skips creation if a patient with the same name already exists.

Usage:
    make seed
    # or directly:
    docker compose exec api python scripts/seed.py
"""
import asyncio
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Ensure app is importable when run from repo root inside Docker
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.db.models import Note, Patient  # noqa: F401 — register models
from app.repositories.note import NoteRepository
from app.repositories.patient import PatientRepository
from app.schemas.note import NoteCreate
from app.schemas.patient import PatientCreate

SOAP_DIR = Path(__file__).parent / "soap_notes"

_patient_repo = PatientRepository()
_note_repo = NoteRepository()

PATIENTS = [
    {
        "name": "James R. Mitchell",
        "dob": date(1955, 4, 12),
        "notes": ["soap_01.txt", "soap_02.txt", "soap_03.txt"],
    },
    {
        "name": "Emily G. Williams",
        "dob": date(1996, 12, 2),
        "notes": ["soap_04.txt", "soap_05.txt", "soap_06.txt"],
    },
]


def _parse_taken_at(text: str) -> datetime:
    match = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", text)
    if not match:
        raise ValueError("SOAP note is missing a 'Date: YYYY-MM-DD' header line")
    return datetime.fromisoformat(f"{match.group(1)}T00:00:00+00:00")


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        for spec in PATIENTS:
            result = await session.execute(
                select(Patient).where(
                    Patient.name == spec["name"],
                    Patient.deleted_at.is_(None),
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"Skipping: '{spec['name']}' already exists (id={existing.id})")
                continue

            patient = await _patient_repo.create(
                session, PatientCreate(name=spec["name"], dob=spec["dob"])
            )
            print(f"Created patient: '{patient.name}' (id={patient.id}, mrn={patient.mrn})")

            for fname in spec["notes"]:
                text = (SOAP_DIR / fname).read_text()
                taken_at = _parse_taken_at(text)
                await _note_repo.create(
                    session,
                    patient.id,
                    NoteCreate(content=text, taken_at=taken_at),
                    source_filename=fname,
                )
                print(f"  Added note: {fname} (taken_at={taken_at.date()})")

    await engine.dispose()
    print("\nSeeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
