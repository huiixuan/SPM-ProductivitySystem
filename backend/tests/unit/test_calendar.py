import pytest
from datetime import date, timedelta
from flask_jwt_extended import create_access_token
from app.models import db, User, Project, Task, ProjectStatus, TaskStatus, RecurrenceType


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


def test_get_personal_calendar_success(client):
    """Test successful retrieval of personal calendar"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/calendar/personal", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "events" in data
        assert isinstance(data["events"], list)


def test_get_personal_calendar_user_not_found(client):
    """Test personal calendar with invalid user"""
    invalid_token = create_access_token(identity="999")
    headers = {"Authorization": f"Bearer {invalid_token}"}
    
    response = client.get("/api/calendar/personal", headers=headers)
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_get_team_calendar_success(client):
    """Test successful retrieval of team calendar"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/calendar/team", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "events" in data
        assert isinstance(data["events"], list)


def test_get_workload_data_success(client):
    """Test successful retrieval of workload data"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/calendar/workload", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "team_members" in data
        assert isinstance(data["team_members"], list)


def test_debug_team_data_success(client):
    """Test successful retrieval of debug team data"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/calendar/debug-team", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "user_id" in data
        assert "team_member_ids" in data


def test_calendar_jwt_required(client):
    """Test that calendar endpoints require JWT authentication"""
    endpoints = [
        "/api/calendar/personal",
        "/api/calendar/team", 
        "/api/calendar/workload",
        "/api/calendar/debug-team"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401


def test_recurring_task_instances_generation(client):
    """Test recurring task instances generation function"""
    with client.application.app_context():
        from app.routes.calendar import get_recurring_task_instances
        
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        
        task = Task(
            title="Recurring Test Task",
            description="Test recurring task",
            duedate=date.today(),
            status=TaskStatus.UNASSIGNED,
            owner=user,
            isRecurring=True,
            recurrence_type=RecurrenceType.DAILY
        )
        
        db.session.add(user)
        db.session.add(task)
        db.session.commit()

        start_date = date.today()
        end_date = start_date + timedelta(days=10)
        instances = get_recurring_task_instances(task, start_date, end_date)
        
        assert len(instances) > 0
        assert len(instances) <= 10
        for instance in instances:
            assert "id" in instance
            assert "title" in instance
            assert "start" in instance
            assert "end" in instance


def test_recurring_task_instances_non_recurring(client):
    """Test that non-recurring tasks return empty instances"""
    with client.application.app_context():
        from app.routes.calendar import get_recurring_task_instances
        
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        
        task = Task(
            title="Non-Recurring Task",
            description="Test non-recurring task",
            duedate=date.today(),
            status=TaskStatus.UNASSIGNED,
            owner=user,
            isRecurring=False
        )
        
        db.session.add(user)
        db.session.add(task)
        db.session.commit()

        start_date = date.today()
        end_date = start_date + timedelta(days=10)
        instances = get_recurring_task_instances(task, start_date, end_date)
        assert instances == []