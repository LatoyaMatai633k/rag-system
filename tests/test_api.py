from fastapi.testclient import TestClient

from app.main import app, service


client = TestClient(app)


def test_health_reports_unindexed_state():
    service.nodes = []
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"success": True, "indexed": False}


def test_chat_requires_an_index():
    service.nodes = []
    service.query_rewriting_pack = None
    response = client.post("/chat", json={"question": "Who is Yaya?"})
    assert response.status_code == 409
    assert response.json()["success"] is False


def test_chat_rejects_empty_question():
    response = client.post("/chat", json={"question": ""})
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_cors_preflight_allows_local_frontend():
    response = client.options(
        "/chat",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
