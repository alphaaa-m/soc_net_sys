"""Phase 0 deliverable: GET /health returns {"status": "ok"}."""


def test_health_root(client):
    assert client.get("/health").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}


def test_health_v1(client):
    assert client.get("/api/v1/health").status_code == 200
