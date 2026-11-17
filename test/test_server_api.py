"""FastAPI API 契约测试；不需要启动游戏或真实窗口。"""
from fastapi.testclient import TestClient

from OAT.server.app import create_app

TOKEN = "test-token"


def client():
    return TestClient(create_app(TOKEN))


def auth():
    return {"X-OAT-Token": TOKEN}


def test_health_is_public():
    with client() as api:
        response = api.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_private_api_requires_token():
    with client() as api:
        assert api.get("/api/v1/settings").status_code == 401
        assert api.get("/api/v1/settings", headers=auth()).status_code == 200


def test_modes_do_not_include_placeholder():
    with client() as api:
        response = api.get("/api/v1/modes", headers=auth())
        assert response.status_code == 200
        names = {item["name"] for item in response.json()}
        assert "魂土" in names
        assert "请选择模式" not in names


def test_task_request_rejects_invalid_times():
    with client() as api:
        response = api.post("/api/v1/tasks/start", headers=auth(), json={
            "mode": "魂土", "times": 0, "client": {"title": "阴阳师"},
        })
        assert response.status_code == 422


def test_settings_reject_unknown_fields():
    with client() as api:
        response = api.patch("/api/v1/settings", headers=auth(), json={"command": "whoami"})
        assert response.status_code == 422
