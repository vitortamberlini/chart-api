from httpx import AsyncClient


async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_create_patient(client: AsyncClient):
    resp = await client.post("/patients", json={"name": "John Doe", "dob": "1980-01-15"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "John Doe"
    assert data["dob"] == "1980-01-15"
    assert data["mrn"].startswith("MRN-")
    assert "id" in data


async def test_get_patient_by_id(client: AsyncClient):
    create_resp = await client.post("/patients", json={"name": "Jane Smith", "dob": "1990-05-20"})
    patient_id = create_resp.json()["id"]

    resp = await client.get(f"/patients/{patient_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Jane Smith"


async def test_get_patient_not_found(client: AsyncClient):
    resp = await client.get("/patients/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_list_patients_pagination(client: AsyncClient):
    for i in range(3):
        await client.post("/patients", json={"name": f"Patient {i}", "dob": "1970-01-01"})

    resp = await client.get("/patients?page=1&per_page=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["per_page"] == 2


async def test_list_patients_search(client: AsyncClient):
    await client.post("/patients", json={"name": "Alice Wonder", "dob": "1985-03-10"})
    await client.post("/patients", json={"name": "Bob Builder", "dob": "1975-07-22"})

    resp = await client.get("/patients?search=Alice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Alice Wonder"


async def test_update_patient(client: AsyncClient):
    create_resp = await client.post("/patients", json={"name": "Old Name", "dob": "1960-06-01"})
    patient_id = create_resp.json()["id"]

    resp = await client.put(f"/patients/{patient_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


async def test_delete_patient(client: AsyncClient):
    create_resp = await client.post("/patients", json={"name": "To Delete", "dob": "1955-11-30"})
    patient_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/patients/{patient_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/patients/{patient_id}")
    assert get_resp.status_code == 404
