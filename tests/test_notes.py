import io

from httpx import AsyncClient


async def _create_patient(client: AsyncClient, name: str = "Note Test Patient") -> str:
    resp = await client.post("/patients", json={"name": name, "dob": "1980-01-01"})
    return resp.json()["id"]


async def test_create_note_json(client: AsyncClient):
    patient_id = await _create_patient(client)

    resp = await client.post(
        f"/patients/{patient_id}/notes",
        json={"content": "SOAP note content", "taken_at": "2024-01-15T10:00:00+00:00"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "SOAP note content"
    assert data["patient_id"] == patient_id
    assert data["note_type"] == "follow_up"
    assert data["source_filename"] is None


async def test_create_note_file_upload(client: AsyncClient):
    patient_id = await _create_patient(client, "File Upload Patient")

    file_content = b"Date: 2024-02-01\n\nSOAP note from file."
    resp = await client.post(
        f"/patients/{patient_id}/notes",
        files={"file": ("note.txt", io.BytesIO(file_content), "text/plain")},
        data={"taken_at": "2024-02-01T00:00:00+00:00"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "SOAP note from file" in data["content"]
    assert data["source_filename"] == "note.txt"
    assert data["note_type"] == "follow_up"


async def test_list_notes(client: AsyncClient):
    patient_id = await _create_patient(client, "List Notes Patient")

    for i in range(2):
        await client.post(
            f"/patients/{patient_id}/notes",
            json={"content": f"Note {i}", "taken_at": f"2024-0{i + 1}-15T10:00:00+00:00"},
        )

    resp = await client.get(f"/patients/{patient_id}/notes")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_delete_note(client: AsyncClient):
    patient_id = await _create_patient(client, "Delete Note Patient")

    note = (
        await client.post(
            f"/patients/{patient_id}/notes",
            json={"content": "Note to delete", "taken_at": "2024-03-01T00:00:00+00:00"},
        )
    ).json()
    note_id = note["id"]

    del_resp = await client.delete(f"/patients/{patient_id}/notes/{note_id}")
    assert del_resp.status_code == 204

    notes = (await client.get(f"/patients/{patient_id}/notes")).json()
    assert len(notes) == 0


async def test_create_note_patient_not_found(client: AsyncClient):
    resp = await client.post(
        "/patients/00000000-0000-0000-0000-000000000000/notes",
        json={"content": "Note", "taken_at": "2024-01-01T00:00:00+00:00"},
    )
    assert resp.status_code == 404
