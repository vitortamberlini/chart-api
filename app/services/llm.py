import json
import re
from typing import Protocol

import anthropic

from app.schemas.note import NoteResponse
from app.schemas.patient import PatientResponse
from app.schemas.summary import SummaryResponse


class LLMService(Protocol):
    async def classify_note(self, content: str) -> str: ...
    async def generate_summary(
        self,
        patient: PatientResponse,
        notes: list[NoteResponse],
        audience: str,
        verbosity: str,
    ) -> SummaryResponse: ...


class AnthropicLLMService:
    _CLASSIFY_CATEGORIES = ("admission", "follow_up", "discharge", "procedure", "routine")

    _AUDIENCE_DESCRIPTIONS = {
        "clinician": "clinical language, diagnoses, medications, labs, plan",
        "family": "plain language, no jargon, empathetic tone",
    }
    _VERBOSITY_DESCRIPTIONS = {
        "brief": "2-3 sentence overview",
        "standard": "full narrative with sections",
        "detailed": "include timeline of all encounters",
    }

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def classify_note(self, content: str) -> str:
        categories_str = " | ".join(self._CLASSIFY_CATEGORIES)
        message = await self._client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=16,
            system=(
                f"Classify the following clinical note into exactly one category: "
                f"{categories_str}. "
                "Respond with only the category name, nothing else."
            ),
            messages=[{"role": "user", "content": content}],
        )
        raw = message.content[0].text.strip().lower()
        for category in self._CLASSIFY_CATEGORIES:
            if category in raw:
                return category
        return raw.split()[0]

    async def generate_summary(
        self,
        patient: PatientResponse,
        notes: list[NoteResponse],
        audience: str,
        verbosity: str,
    ) -> SummaryResponse:
        audience_desc = self._AUDIENCE_DESCRIPTIONS.get(audience, audience)
        verbosity_desc = self._VERBOSITY_DESCRIPTIONS.get(verbosity, verbosity)

        formatted_notes = "\n\n".join(
            f"[{i + 1}] {note.taken_at.date()} ({note.note_type or 'unclassified'}):\n{note.content}"
            for i, note in enumerate(notes)
        )

        message = await self._client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=(
                "You are a clinical documentation assistant. Given SOAP notes for a patient, "
                "synthesize a structured summary. Respond ONLY with a valid JSON object with these exact fields:\n"
                "- summary: string narrative\n"
                "- key_diagnoses: list of strings\n"
                "- current_medications: list of strings\n"
                f"Audience: {audience} ({audience_desc}).\n"
                f"Verbosity: {verbosity} ({verbosity_desc})."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Patient: {patient.name} | DOB: {patient.dob} | MRN: {patient.mrn}\n\n"
                    f"Notes ({len(notes)} total, chronological):\n{formatted_notes}"
                ),
            }],
        )

        text = message.content[0].text.strip()
        # Strip markdown code fences if the model wraps the JSON
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        raw = json.loads(text)
        return SummaryResponse(
            patient=patient,
            summary=raw["summary"],
            key_diagnoses=raw["key_diagnoses"],
            current_medications=raw["current_medications"],
            note_count=len(notes),
        )


class OpenAILLMService:
    async def classify_note(self, content: str) -> str:
        raise NotImplementedError("OpenAI provider is not yet implemented")

    async def generate_summary(
        self,
        patient: PatientResponse,
        notes: list[NoteResponse],
        audience: str,
        verbosity: str,
    ) -> SummaryResponse:
        raise NotImplementedError("OpenAI provider is not yet implemented")
