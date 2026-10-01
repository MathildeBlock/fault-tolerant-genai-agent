from fastapi.testclient import TestClient

from api.main import app, tickets

client = TestClient(app)


def setup_function():
    tickets.clear()


def make_ticket():
    return client.post("/tickets", json={"title": "Keyboard", "description": "Not working"}).json()


def test_create_and_get():
    t = make_ticket()
    assert t["status"] == "OPEN"
    assert client.get(f"/tickets/{t['id']}").json()["title"] == "Keyboard"


def test_blank_title_is_rejected():
    response = client.post("/tickets", json={"title": "   ", "description": "Not working"})
    assert response.status_code == 422
    assert "Title must not be blank" in response.json()["detail"][0]["msg"]


def test_unknown_id_404():
    assert client.get("/tickets/nope").status_code == 404
    assert client.patch("/tickets/nope", json={"status": "CLOSED"}).status_code == 404
    assert client.delete("/tickets/nope").status_code == 404


def test_invalid_status_422_lists_options():
    t = make_ticket()
    r = client.patch(f"/tickets/{t['id']}", json={"status": "PROGRESS"})
    assert r.status_code == 422
    assert "OPEN, RESOLVED, CLOSED" in r.json()["detail"]


def test_resolved_requires_resolution():
    t = make_ticket()
    assert client.patch(f"/tickets/{t['id']}", json={"status": "RESOLVED"}).status_code == 422
    r = client.patch(f"/tickets/{t['id']}", json={"status": "RESOLVED", "resolution": "Replaced cable"})
    assert r.status_code == 200 and r.json()["resolution"] == "Replaced cable"


def test_filter_and_delete():
    a, b = make_ticket(), make_ticket()
    client.patch(f"/tickets/{b['id']}", json={"status": "CLOSED"})
    assert len(client.get("/tickets", params={"status": "OPEN"}).json()) == 1
    assert client.delete(f"/tickets/{a['id']}").status_code == 204
    assert len(client.get("/tickets").json()) == 1
