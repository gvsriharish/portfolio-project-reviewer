import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_execute_task_success():
    response = client.post("/tasks/execute?task_id=task-123")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

def test_execute_task_missing_param():
    response = client.post("/tasks/execute?task_id=")
    assert response.status_code == 400
