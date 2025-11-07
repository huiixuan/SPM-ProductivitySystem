import pytest
from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token
from app.models import db, User, Task, Project, Notification, NotificationType, TaskStatus, ProjectStatus


@pytest.fixture
def app():
    from app import create_app
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "JWT_SECRET_KEY": "test-secret",
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_get_user_notifications_success(client):
    """Test successful retrieval of user notifications"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/notifications", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)


def test_mark_notification_as_read_success(client):
    """Test successfully marking a notification as read"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        
        project = Project(name="Test Project", owner=user)
        task = Task(title="Test Task", duedate=datetime.now().date(), owner=user, project=project)
        notification = Notification(
            user=user,
            task=task,
            type=NotificationType.DUE_DATE_REMINDER,
            payload={"message": "test"}
        )
        
        db.session.add_all([user, project, task, notification])
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.patch(f"/api/notifications/{notification.id}/read", headers=headers)
        assert response.status_code == 200
        assert response.get_json()["success"] is True


def test_mark_notification_as_read_not_found(client):
    """Test marking non-existent notification as read"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.patch("/api/notifications/999/read", headers=headers)
        assert response.status_code == 404
        assert "error" in response.get_json()


def test_mark_all_notifications_as_read_success(client):
    """Test successfully marking all notifications as read"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.patch("/api/notifications/read-all", headers=headers)
        assert response.status_code == 200
        assert response.get_json()["success"] is True


def test_get_unread_count_success(client):
    """Test successful retrieval of unread notification count"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/notifications/unread-count", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)


def test_debug_notifications_success(client):
    """Test successful debug notifications endpoint"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/notifications/debug", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "user_id" in data
        assert "user_email" in data


def test_check_future_notifications(client):
    """Test manual check for future notifications"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.post("/api/notifications/check-future", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


def test_debug_task_notifications_not_found(client):
    """Test debug task notifications with non-existent task"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/notifications/debug-task/999", headers=headers)
        assert response.status_code == 404
        assert "error" in response.get_json()


def test_notifications_jwt_required(client):
    """Test that notifications endpoints require JWT authentication"""
    # Test GET without auth
    response = client.get("/api/notifications")
    assert response.status_code == 401


def test_notification_payload_building():
    """Test notification payload building"""
    from app.models import NotificationType
    
    payload = Notification.build_payload(
        NotificationType.DUE_DATE_REMINDER,
        project_name="Test Project",
        task_title="Test Task",
        duedate=datetime.now().date()
    )
    
    assert payload is not None
    assert payload["project_name"] == "Test Project"
    assert payload["task_title"] == "Test Task"