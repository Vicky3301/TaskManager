import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import models so SQLAlchemy registers both tables.
from app.database import Base
from app import models, user_models
from app.main import app
from app.dependencies import get_db


# Separate in-memory database for automated tests.
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
    # Start every test with an empty database.
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


def register_user(client, email):
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201
    return response.json()


def login_user(client, email):
    response = client.post(
        "/auth/token",
        data={
            "username": email,
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def create_task(client, token, title):
    response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": title,
            "description": "Automated security test",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "alice@example.com"

    # Password hashes must never appear in registration responses.
    assert "hashed_password" not in response.json()
    assert "password" not in response.json()


def test_duplicate_registration_rejected(client):
    register_user(client, "alice@example.com")

    response = client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 409


def test_login_returns_access_token(client):
    register_user(client, "alice@example.com")

    token = login_user(client, "alice@example.com")

    assert isinstance(token, str)
    assert len(token) > 0


def test_wrong_password_rejected(client):
    register_user(client, "alice@example.com")

    response = client.post(
        "/auth/token",
        data={
            "username": "alice@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_tasks_require_authentication(client):
    response = client.get("/tasks")

    assert response.status_code == 401


def test_user_can_create_and_read_own_task(client):
    register_user(client, "alice@example.com")
    token = login_user(client, "alice@example.com")

    task = create_task(client, token, "Alice's task")

    response = client.get(
        f"/tasks/{task['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Alice's task"


def test_user_cannot_read_another_users_task(client):
    register_user(client, "alice@example.com")
    register_user(client, "bob@example.com")

    alice_token = login_user(client, "alice@example.com")
    bob_token = login_user(client, "bob@example.com")

    alice_task = create_task(
        client,
        alice_token,
        "Alice's private task",
    )

    response = client.get(
        f"/tasks/{alice_task['id']}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )

    assert response.status_code == 404


def test_user_cannot_update_another_users_task(client):
    register_user(client, "alice@example.com")
    register_user(client, "bob@example.com")

    alice_token = login_user(client, "alice@example.com")
    bob_token = login_user(client, "bob@example.com")

    alice_task = create_task(
        client,
        alice_token,
        "Alice's original task",
    )

    response = client.put(
        f"/tasks/{alice_task['id']}",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={"title": "Bob changed this"},
    )

    assert response.status_code == 404

    # Confirm Alice's original data remains unchanged.
    verify_response = client.get(
        f"/tasks/{alice_task['id']}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["title"] == "Alice's original task"


def test_user_cannot_delete_another_users_task(client):
    register_user(client, "alice@example.com")
    register_user(client, "bob@example.com")

    alice_token = login_user(client, "alice@example.com")
    bob_token = login_user(client, "bob@example.com")

    alice_task = create_task(
        client,
        alice_token,
        "Alice's task",
    )

    response = client.delete(
        f"/tasks/{alice_task['id']}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )

    assert response.status_code == 404

    # Alice must still be able to retrieve her task.
    verify_response = client.get(
        f"/tasks/{alice_task['id']}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )

    assert verify_response.status_code == 200