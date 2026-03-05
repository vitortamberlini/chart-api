from httpx import AsyncClient


async def _create_patient_with_note(client: AsyncClient, name: str) -> str:
    patient = (await client.post("/patients", json={"name": name, "dob": "1980-06-15"})).json()
    patient_id = patient["id"]
    await client.post(
        f"/patients/{patient_id}/notes",
        json={"content": "SOAP note content.", "taken_at": "2024-01-10T00:00:00+00:00"},
    )
    return patient_id


async def test_summary_returns_structured_response(client: AsyncClient):
    patient_id = await _create_patient_with_note(client, "Summary Patient")

    resp = await client.get(f"/patients/{patient_id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert isinstance(data["key_diagnoses"], list)
    assert isinstance(data["current_medications"], list)
    assert data["note_count"] == 1
    assert "patient" in data
    assert "generated_at" in data


async def test_summary_patient_not_found(client: AsyncClient):
    resp = await client.get("/patients/00000000-0000-0000-0000-000000000000/summary")
    assert resp.status_code == 404


async def test_summary_clinician_audience(client: AsyncClient):
    patient_id = await _create_patient_with_note(client, "Clinician Audience Patient")

    resp = await client.get(f"/patients/{patient_id}/summary?audience=clinician&verbosity=standard")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["summary"], str)
    assert isinstance(data["key_diagnoses"], list)


async def test_summary_family_audience(client: AsyncClient):
    patient_id = await _create_patient_with_note(client, "Family Audience Patient")

    resp = await client.get(f"/patients/{patient_id}/summary?audience=family&verbosity=brief")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["summary"], str)
    assert data["note_count"] >= 1
