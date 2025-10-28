from datetime import date

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.models import db, User, Task, Comment, TaskStatus
from app.services import notification_services


@pytest.fixture
def app_instance():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JWT_SECRET_KEY": "comments-secret",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture
def seed_user_and_task(app_instance):
    with app_instance.app_context():
        user = User(name="Commenter", email="commenter@example.com", role="STAFF")
        user.set_password("password")
        task_owner = User(name="Owner", email="owner@example.com", role="STAFF")
        task_owner.set_password("password")
        task = Task(
            title="Task",
            duedate=date.today(),
            status=TaskStatus.UNASSIGNED,
            owner=task_owner,
        )
        db.session.add_all([user, task_owner, task])
        db.session.commit()
        return {"user_id": user.id, "task_id": task.id, "user_email": user.email}


@pytest.fixture
def auth_headers(app_instance, seed_user_and_task):
    with app_instance.app_context():
        token = create_access_token(identity=str(seed_user_and_task["user_id"]))
    return {"Authorization": f"Bearer {token}"}


def test_create_comment_requires_content(client, auth_headers):
    response = client.post(
        "/api/comments/save-comment/1",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Content is required"


def test_create_comment_task_not_found(client, auth_headers, monkeypatch):
    response = client.post(
        "/api/comments/save-comment/999",
        json={"content": "Hi"},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.get_json()["error"] == "Task not found"


def test_create_comment_success(client, auth_headers, seed_user_and_task, monkeypatch):
    calls = {}

    def fake_notify(comment):  # noqa: ANN001
        calls["called"] = comment.id

    monkeypatch.setattr(notification_services, "create_comment_notification", fake_notify)

    response = client.post(
        f"/api/comments/save-comment/{seed_user_and_task['task_id']}",
        json={"content": "Great job"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["comment"]["content"] == "Great job"
    assert calls


def test_get_comments_returns_ordered_list(client, auth_headers, seed_user_and_task):
    with client.application.app_context():
        comment = Comment(
            task_id=seed_user_and_task["task_id"],
            user_id=seed_user_and_task["user_id"],
            content="First",
        )
        db.session.add(comment)
        db.session.commit()

    response = client.get(
        f"/api/comments/get-comments/{seed_user_and_task['task_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["content"] == "First"
    assert data[0]["user_email"] == seed_user_and_task["user_email"]
