import pytest
from datetime import date, datetime
from app.models import (
    db,
    User,
    Task,
    Project,
    Notification,
    TaskStatus,
    ProjectStatus,
    NotificationType,
)
from werkzeug.security import check_password_hash


@pytest.fixture
def app_instance():
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
def session(app_instance):
    with app_instance.app_context():
        yield db.session


def create_user(email: str, name: str = "Test User") -> User:
    user = User(email=email, name=name, role="STAFF")
    user.set_password("password123")
    return user


def create_project(owner: User, name: str = "Project Alpha") -> Project:
    return Project(name=name, owner=owner, status=ProjectStatus.NOT_STARTED)


def create_task(owner: User, project: Project | None = None, **overrides) -> Task:
    task = Task(
        title=overrides.get("title", "Task Title"),
        description=overrides.get("description", "A task description"),
        duedate=overrides.get("duedate", date.today()),
        status=overrides.get("status", TaskStatus.UNASSIGNED),
        owner=owner,
        project=project,
        notes=overrides.get("notes", None),
        priority=overrides.get("priority", 1),
    )
    return task


def test_user_password_hashing(session):
    user = create_user("alice@example.com")
    session.add(user)
    session.commit()

    assert user.password_hash != "password123"
    assert check_password_hash(user.password_hash, "password123")


def test_task_to_dict_includes_related_data(session):
    owner = create_user("owner@example.com")
    collaborator = create_user("collab@example.com", name="Collab")
    project = create_project(owner, name="Launch Project")
    task = create_task(owner, project=project, notes="Remember to sync")
    task.collaborators.append(collaborator)

    session.add_all([owner, collaborator, project, task])
    session.commit()

    task_dict = task.to_dict()

    assert task_dict["owner_email"] == owner.email
    assert task_dict["project"] == project.name
    assert task_dict["notes"] == "Remember to sync"
    assert task_dict["status"] == TaskStatus.UNASSIGNED.value
    assert task_dict["priority"] == 1
    assert task_dict["collaborators"] == [
        {"id": collaborator.id, "email": collaborator.email, "name": collaborator.name}
    ]


def test_project_to_dict_includes_collaborators(session):
    owner = create_user("owner@example.com")
    collaborator = create_user("collab@example.com", name="Teammate")
    project = create_project(owner)
    project.collaborators.append(collaborator)

    session.add_all([owner, collaborator, project])
    session.commit()

    project_dict = project.to_dict()

    assert project_dict["owner_email"] == owner.email
    assert project_dict["status"] == ProjectStatus.NOT_STARTED.value
    assert project_dict["collaborators"] == [
        {"id": collaborator.id, "email": collaborator.email}
    ]


def test_notification_message_builders(session):
    owner = create_user("owner@example.com")
    assignee = create_user("assignee@example.com", name="Assignee")
    project = create_project(owner, name="Launch")
    task = create_task(owner, project=project, title="Design")

    notification = Notification(
        user=assignee,
        task=task,
        type=NotificationType.DUE_DATE_REMINDER,
        payload=Notification.build_payload(
            NotificationType.DUE_DATE_REMINDER,
            project_name=project.name,
            task_title=task.title,
            duedate=date(2025, 1, 1),
        ),
        trigger_days_before=3,
    )

    session.add_all([owner, assignee, project, task, notification])
    session.commit()

    assert "Design" in notification.message
    assert "due on" in notification.message
    assert "3 day(s)" in notification.message


def test_notification_payload_for_comment(session):
    owner = create_user("owner@example.com")
    commenter = create_user("commenter@example.com", name="Commenter")
    project = create_project(owner, name="Launch")
    task = create_task(owner, project=project, title="Design")

    payload = Notification.build_payload(
        NotificationType.NEW_COMMENT,
        project_name=project.name,
        task_title=task.title,
        comment_author=commenter.name,
        comment_excerpt="Nice work",
        comment_id=42,
    )

    notification = Notification(
        user=owner,
        task=task,
        type=NotificationType.NEW_COMMENT,
        payload=payload,
        trigger_days_before=None,
    )

    session.add_all([owner, commenter, project, task, notification])
    session.commit()

    assert payload["comment_author"] == "Commenter"
    assert payload["comment_id"] == 42
    assert "Nice work" in notification.message
