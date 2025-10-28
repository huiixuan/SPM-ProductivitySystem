import pytest
from datetime import date, timedelta
from flask_jwt_extended import create_access_token

from app import create_app
from app.models import (
    db,
    User,
    Task,
    Project,
    Notification,
    NotificationType,
    TaskStatus,
    ProjectStatus,
)


@pytest.fixture
def app_instance():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JWT_SECRET_KEY": "notifications-secret",
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
def seed_data(app_instance):
    with app_instance.app_context():
        user = User(name="Notify User", email="notify@example.com", role="STAFF")
        user.set_password("password")
        project = Project(name="Notify Project", owner=user, status=ProjectStatus.IN_PROGRESS)
        task = Task(
            title="Notify Task",
            description="Reminder",
            duedate=date.today() + timedelta(days=5),
            status=TaskStatus.ONGOING,
            owner=user,
            project=project,
        )
        db.session.add_all([user, project, task])
        db.session.commit()

        return {
            "user_id": user.id,
            "task_id": task.id,
            "user_email": user.email,
        }


@pytest.fixture
def auth_headers(app_instance, seed_data):
    with app_instance.app_context():
        token = create_access_token(identity=str(seed_data["user_id"]))
    return {"Authorization": f"Bearer {token}"}


def create_notification(task: Task, user: User, **overrides) -> Notification:
    payload = {
        "project_name": task.project.name if task.project else None,
        "task_title": task.title,
        "duedate": task.duedate.isoformat() if task.duedate else None,
    }
    notif = Notification(
        user=user,
        task=task,
        type=overrides.get("type", NotificationType.DUE_DATE_REMINDER),
        payload=payload,
        trigger_days_before=overrides.get("trigger_days_before", 3),
        is_read=overrides.get("is_read", False),
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def test_get_notifications_returns_augmented_payload(client, app_instance, auth_headers, seed_data):
    with app_instance.app_context():
        user = db.session.get(User, seed_data["user_id"])
        task = db.session.get(Task, seed_data["task_id"])
        create_notification(task, user)
        create_notification(
            task,
            user,
            type=NotificationType.NEW_COMMENT,
            trigger_days_before=None,
        )

    response = client.get("/api/notifications", headers=auth_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert all("message" in item for item in data)
    assert {item["type"] for item in data} == {
        NotificationType.DUE_DATE_REMINDER.value,
        NotificationType.NEW_COMMENT.value,
    }


def test_mark_single_notification_as_read(client, app_instance, auth_headers, seed_data):
    with app_instance.app_context():
        user = db.session.get(User, seed_data["user_id"])
        task = db.session.get(Task, seed_data["task_id"])
        notif = create_notification(task, user)
        notif_id = notif.id

    response = client.patch(f"/api/notifications/{notif_id}/read", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    with app_instance.app_context():
        refreshed = db.session.get(Notification, notif_id)
        assert refreshed.is_read is True


def test_mark_single_notification_not_found_returns_404(client, auth_headers):
    response = client.patch("/api/notifications/999/read", headers=auth_headers)
    assert response.status_code == 404
    assert response.get_json()["error"] == "Notification not found"


def test_mark_all_notifications_as_read(client, app_instance, auth_headers, seed_data):
    with app_instance.app_context():
        user = db.session.get(User, seed_data["user_id"])
        task = db.session.get(Task, seed_data["task_id"])
        create_notification(task, user, trigger_days_before=7)
        create_notification(task, user, trigger_days_before=3)

    response = client.patch("/api/notifications/read-all", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    with app_instance.app_context():
        unread = Notification.query.filter_by(user_id=seed_data["user_id"], is_read=False).count()
        assert unread == 0


def test_get_unread_count(client, app_instance, auth_headers, seed_data):
    with app_instance.app_context():
        user = db.session.get(User, seed_data["user_id"])
        task = db.session.get(Task, seed_data["task_id"])
        create_notification(task, user, is_read=False)
        create_notification(
            task,
            user,
            is_read=True,
            trigger_days_before=1,
            type=NotificationType.NEW_COMMENT,
        )

    response = client.get("/api/notifications/unread-count", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["unread_count"] == 1
