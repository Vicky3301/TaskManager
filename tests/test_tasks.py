import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_db


# Create an isolated SQLite database for tests
TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)



@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_create_task(client):
    response = client.post(
        "/tasks",
        json={
            "title": "Learn pytest",
            "description": "Write automated API tests",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Learn pytest"
    assert data["description"] == "Write automated API tests"
    assert data["completed"] is False
    assert "id" in data
    assert "created_at" in data


def test_get_all_tasks(client):
    client.post(
        "/tasks",
        json={"title": "Task One", "description": "First task"},
    )

    client.post(
        "/tasks",
        json={"title": "Task Two", "description": "Second task"},
    )

    response = client.get("/tasks")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_single_task(client):
    create_response = client.post(
        "/tasks",
        json={"title": "Find me", "description": "Test retrieval"},
    )

    task_id = create_response.json()["id"]

    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["title"] == "Find me"


def test_update_task(client):
    create_response = client.post(
        "/tasks",
        json={"title": "Original title"},
    )

    task_id = create_response.json()["id"]

    response = client.put(
        f"/tasks/{task_id}",
        json={"completed": True},
    )

    assert response.status_code == 200
    assert response.json()["completed"] is True


def test_delete_task(client):
    create_response = client.post(
        "/tasks",
        json={"title": "Task to delete"},
    )

    task_id = create_response.json()["id"]

    response = client.delete(f"/tasks/{task_id}")

    assert response.status_code == 200

    get_response = client.get(f"/tasks/{task_id}")

    assert get_response.status_code == 404


def test_missing_task_returns_404(client):
    response = client.get("/tasks/99999")

    assert response.status_code == 404


def test_empty_title_is_rejected(client):
    response = client.post(
        "/tasks",
        json={"title": ""},
    )

    assert response.status_code == 422