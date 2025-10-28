import json
from datetime import date

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.models import db, User, Task, TaskStatus


@pytest.fixture
def app_instance(monkeypatch):
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JWT_SECRET_KEY": "integration-secret",
        }
    )

    with app.app_context():
        db.create_all()

        # Seed a baseline user used for authentication
        owner = User(
            name="Owner",
            email="owner@example.com",
            role="STAFF",
        )
        owner.set_password("password")
        db.session.add(owner)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture
def auth_headers(app_instance):
    with app_instance.app_context():
        token = create_access_token(identity="1")
        return {"Authorization": f"Bearer {token}"}


def test_create_task_success(client, auth_headers):
    payload = {
        "title": "Integration Task",
        "description": "Verify creation",
        "duedate": date.today().isoformat(),
        "status": TaskStatus.UNASSIGNED.value,
        "owner": "owner@example.com",
        "priority": "1",
        "collaborators": [],
    }

    response = client.post(
        "/api/task/create-task",
        data=payload,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["title"] == "Integration Task"

    with client.application.app_context():
        task = db.session.get(Task, data["task_id"])
        assert task is not None
        assert task.title == "Integration Task"
        assert task.owner.email == "owner@example.com"


def test_get_task_returns_dict(client, auth_headers):
    with client.application.app_context():
        owner = db.session.get(User, 1)
        task = Task(
            title="Existing Task",
            description="Pre-created",
            duedate=date.today(),
            status=TaskStatus.UNASSIGNED,
            owner=owner,
            priority=1,
        )
        db.session.add(task)
        db.session.commit()

        task_id = task.id

    response = client.get(f"/api/task/get-task/{task_id}", headers=auth_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["title"] == "Existing Task"
    assert data["status"] == TaskStatus.UNASSIGNED.value
    assert data["owner_email"] == "owner@example.com"


def test_get_task_not_found(client, auth_headers):
    response = client.get("/api/task/get-task/999", headers=auth_headers)
    assert response.status_code == 404


def test_get_user_tasks(client, auth_headers):
    with client.application.app_context():
        owner = db.session.get(User, 1)
        task = Task(
            title="User Task",
            description="Belongs to user",
            duedate=date.today(),
            status=TaskStatus.UNASSIGNED,
            owner=owner,
            priority=1,
        )
        db.session.add(task)
        db.session.commit()

    response = client.get("/api/task/get-user-tasks", headers=auth_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, list)
    assert any(item["title"] == "User Task" for item in data)


def test_get_user_tasks_requires_auth(client):
    response = client.get("/api/task/get-user-tasks")
    assert response.status_code == 401
    data = response.get_json()
    assert data["msg"] == "Missing Authorization Header"
