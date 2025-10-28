import pytest
from datetime import date, timedelta
from flask_jwt_extended import create_access_token

from app import create_app
from app.models import (
    db,
    User,
    Task,
    Project,
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
            "JWT_SECRET_KEY": "calendar-secret",
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
def calendar_data(app_instance):
    with app_instance.app_context():
        primary = User(name="Primary", email="primary@example.com", role="STAFF")
        primary.set_password("password")
        collaborator = User(name="Collab", email="collab@example.com", role="STAFF")
        collaborator.set_password("password")
        other = User(name="Other", email="other@example.com", role="MANAGER")
        other.set_password("password")
        db.session.add_all([primary, collaborator, other])

        today = date.today()

        overdue_project = Project(
            name="Overdue Project",
            description="",
            status=ProjectStatus.NOT_STARTED,
            deadline=today - timedelta(days=2),
            owner=primary,
        )
        completed_project = Project(
            name="Completed",
            status=ProjectStatus.COMPLETED,
            deadline=today - timedelta(days=1),
            owner=primary,
        )
        ongoing_project = Project(
            name="Ongoing",
            status=ProjectStatus.IN_PROGRESS,
            deadline=today + timedelta(days=5),
            owner=primary,
        )
        ongoing_project.collaborators.append(collaborator)

        collaborator_project = Project(
            name="Collaborator Project",
            status=ProjectStatus.IN_PROGRESS,
            deadline=today + timedelta(days=10),
            owner=other,
        )
        collaborator_project.collaborators.append(primary)

        db.session.add_all([overdue_project, completed_project, ongoing_project, collaborator_project])

        overdue_task = Task(
            title="Overdue Task",
            duedate=today - timedelta(days=1),
            status=TaskStatus.ONGOING,
            owner=primary,
            project=overdue_project,
        )
        completed_task = Task(
            title="Completed Task",
            duedate=today - timedelta(days=1),
            status=TaskStatus.COMPLETED,
            owner=primary,
            project=completed_project,
        )
        ongoing_task = Task(
            title="Ongoing Task",
            duedate=today + timedelta(days=2),
            status=TaskStatus.PENDING_REVIEW,
            owner=primary,
            project=ongoing_project,
        )
        upcoming_task = Task(
            title="Upcoming Task",
            duedate=today + timedelta(days=6),
            status=TaskStatus.UNASSIGNED,
            owner=primary,
            project=ongoing_project,
        )
        collaborator_task = Task(
            title="Collaborator Task",
            duedate=today + timedelta(days=3),
            status=TaskStatus.ONGOING,
            owner=collaborator,
            project=collaborator_project,
        )
        collaborator_task.collaborators.append(primary)

        db.session.add_all([overdue_task, completed_task, ongoing_task, upcoming_task, collaborator_task])
        db.session.commit()

        return {
            "primary_id": primary.id,
            "collaborator_id": collaborator.id,
            "project_ids": {
                "overdue": overdue_project.id,
                "completed": completed_project.id,
                "ongoing": ongoing_project.id,
                "collab": collaborator_project.id,
            },
            "task_ids": {
                "overdue": overdue_task.id,
                "completed": completed_task.id,
                "ongoing": ongoing_task.id,
                "upcoming": upcoming_task.id,
                "collab": collaborator_task.id,
            },
        }


@pytest.fixture
def auth_headers(app_instance, calendar_data):
    with app_instance.app_context():
        token = create_access_token(identity=str(calendar_data["primary_id"]))
    return {"Authorization": f"Bearer {token}"}


def test_personal_calendar_returns_statuses(client, auth_headers, calendar_data):
    response = client.get("/api/calendar/personal", headers=auth_headers)
    assert response.status_code == 200
    events = {event["id"]: event for event in response.get_json()["events"]}

    projects = calendar_data["project_ids"]
    tasks = calendar_data["task_ids"]

    assert events[f"project-{projects['overdue']}"]["status"] == "overdue"
    assert events[f"project-{projects['completed']}"]["status"] == "completed"
    assert events[f"project-{projects['ongoing']}"]["status"] == "ongoing"
    assert events[f"task-{tasks['overdue']}"]["status"] == "overdue"
    assert events[f"task-{tasks['completed']}"]["status"] == "completed"
    assert events[f"task-{tasks['ongoing']}"]["status"] == "ongoing"
    assert events[f"task-{tasks['upcoming']}"]["status"] == "upcoming"


def test_personal_calendar_user_not_found_returns_404(client, app_instance):
    with app_instance.app_context():
        token = create_access_token(identity="999")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/calendar/personal", headers=headers)
    assert response.status_code == 404


def test_team_calendar_includes_collaborators(client, auth_headers):
    response = client.get("/api/calendar/team", headers=auth_headers)
    assert response.status_code == 200
    events = response.get_json()["events"]

    project_event = next(e for e in events if e["type"] == "project" and e["title"] == "Collaborator Project")
    assert "primary@example.com" in project_event["collaborators"]
    assert project_event["assigneeEmail"] == "other@example.com"

    task_event = next(e for e in events if e["type"] == "task" and e["title"] == "Collaborator Task")
    assert task_event["assigneeEmail"] == "collab@example.com"
    assert "primary@example.com" in task_event["collaborators"]


def test_team_calendar_user_not_found_returns_404(client, app_instance):
    with app_instance.app_context():
        token = create_access_token(identity="999")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/calendar/team", headers=headers)
    assert response.status_code == 404


def test_workload_data_counts_active_items(client, auth_headers):
    response = client.get("/api/calendar/workload", headers=auth_headers)
    assert response.status_code == 200
    team_members = response.get_json()["team_members"]

    primary_entry = next(member for member in team_members if member["email"] == "primary@example.com")
    assert primary_entry["task_count"] >= 1
    assert primary_entry["project_count"] >= 1
    assert "workload" in primary_entry


def test_workload_user_not_found_returns_404(client, app_instance):
    with app_instance.app_context():
        token = create_access_token(identity="999")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/calendar/workload", headers=headers)
    assert response.status_code == 404


def test_debug_team_endpoint_returns_structure(client, auth_headers):
    response = client.get("/api/calendar/debug-team", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "team_members" in data
    assert "team_member_ids" in data
    assert isinstance(data["team_member_ids"], list)
