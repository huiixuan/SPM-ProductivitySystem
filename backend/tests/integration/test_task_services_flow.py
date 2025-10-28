import json
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app import create_app
from app.models import (
    db,
    User,
    Task,
    Project,
    Attachment,
    TaskStatus,
    ProjectStatus,
)
from app.services import task_services


class DummyFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    def read(self):
        return self._content


@pytest.fixture
def app_instance():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def seed_data(app_instance, monkeypatch):
    with app_instance.app_context():
        current_user = User(name="Current", email="current@example.com", role="STAFF")
        current_user.set_password("password")
        owner = User(name="Owner", email="owner@example.com", role="STAFF")
        owner.set_password("password")
        collaborator = User(name="Collaborator", email="collab@example.com", role="STAFF")
        collaborator.set_password("password")
        new_owner = User(name="New Owner", email="newowner@example.com", role="MANAGER")
        new_owner.set_password("password")
        db.session.add_all([current_user, owner, collaborator, new_owner])

        project = Project(
            name="Project",
            owner=owner,
            status=ProjectStatus.IN_PROGRESS,
            deadline=date.today() + timedelta(days=5),
        )
        db.session.add(project)
        db.session.commit()

        notification_calls = {
            "created": [],
            "assignment": [],
            "update": [],
            "remove": [],
            "update_due": [],
        }

        monkeypatch.setattr(task_services, "get_jwt_identity", lambda: str(current_user.id))
        monkeypatch.setattr(
            task_services.notification_service,
            "create_notifications_for_task",
            lambda task: notification_calls["created"].append(task.id),
        )
        monkeypatch.setattr(
            task_services.notification_service,
            "create_task_assignment_notification",
            lambda task, assigned_by, assignee: notification_calls["assignment"].append(
                (task.id, getattr(assigned_by, "email", None), getattr(assignee, "email", None))
            ),
        )
        monkeypatch.setattr(
            task_services.notification_service,
            "create_task_update_notification",
            lambda task, updated_by, fields: notification_calls["update"].append((task.id, tuple(fields))),
        )
        monkeypatch.setattr(
            task_services.notification_service,
            "remove_notifications_for_task",
            lambda task: notification_calls["remove"].append(task.id),
        )
        monkeypatch.setattr(
            task_services.notification_service,
            "update_notifications_for_task",
            lambda task: notification_calls["update_due"].append(task.id),
        )

        return {
            "current_user_id": current_user.id,
            "current_user_email": current_user.email,
            "owner_id": owner.id,
            "owner_email": owner.email,
            "collaborator_id": collaborator.id,
            "collaborator_email": collaborator.email,
            "new_owner_id": new_owner.id,
            "new_owner_email": new_owner.email,
            "project_id": project.id,
            "calls": notification_calls,
        }


@pytest.fixture
def session(app_instance):
    with app_instance.app_context():
        yield db.session


def test_create_task_full_flow(app_instance, seed_data):
    calls = seed_data["calls"]

    file_obj = DummyFile("spec.txt", b"spec content")

    task = task_services.create_task(
        title="Build",
        description="Build feature",
        duedate=date.today() + timedelta(days=3),
        status=TaskStatus.UNASSIGNED,
        owner_email=seed_data["owner_email"],
        collaborator_emails=[seed_data["collaborator_email"]],
        attachments=[file_obj],
        notes="priority work",
        priority=2,
        project_id=seed_data["project_id"],
    )

    with app_instance.app_context():
        stored = db.session.get(Task, task.id)
        assert stored is not None
        assert stored.owner.email == "owner@example.com"
        assert stored.project_id == seed_data["project_id"]
        assert stored.priority == 2
        assert [user.email for user in stored.collaborators] == [seed_data["collaborator_email"]]
        assert Attachment.query.filter_by(task_id=stored.id).count() == 1

    assert calls["created"] == [task.id]
    assert calls["assignment"] == [(task.id, "current@example.com", "owner@example.com")]


def test_create_task_owner_missing_raises(app_instance):
    with pytest.raises(ValueError):
        task_services.create_task(
            title="Build",
            description="",
            duedate=date.today(),
            status=TaskStatus.UNASSIGNED,
            owner_email="missing@example.com",
            collaborator_emails=[],
            attachments=None,
            notes=None,
            priority=1,
        )


def test_update_task_covers_notifications(app_instance, seed_data, monkeypatch):
    calls = seed_data["calls"]
    with app_instance.app_context():
        owner = db.session.get(User, seed_data["owner_id"])
        collaborator = db.session.get(User, seed_data["collaborator_id"])
        new_owner = db.session.get(User, seed_data["new_owner_id"])
        project = db.session.get(Project, seed_data["project_id"])
        task = Task(
            title="Initial",
            description="Desc",
            duedate=date.today() + timedelta(days=7),
            status=TaskStatus.UNASSIGNED,
            owner=owner,
            project=project,
            priority=1,
            notes="old",
        )
        task.collaborators.append(collaborator)
        attachment = Attachment(filename="keep.txt", content=b"keep", task=task)
        db.session.add_all([task, attachment])
        db.session.commit()
        task_id = task.id
        attachment_id = attachment.id
        original_due = task.duedate

    def fake_history(instance, field):
        mapping = {
            "status": SimpleNamespace(
                has_changes=lambda: True,
                deleted=[TaskStatus.UNASSIGNED],
                added=[TaskStatus.COMPLETED],
            ),
            "duedate": SimpleNamespace(
                has_changes=lambda: True,
                deleted=[original_due],
                added=[date.today() + timedelta(days=10)],
            ),
            "priority": SimpleNamespace(has_changes=lambda: True, deleted=[1], added=[3]),
            "owner_id": SimpleNamespace(
                has_changes=lambda: True,
                deleted=[seed_data["owner_id"]],
                added=[seed_data["new_owner_id"]],
            ),
        }
        return mapping[field]

    monkeypatch.setattr("sqlalchemy.orm.attributes.get_history", fake_history)

    new_file = DummyFile("new.txt", b"new")

    updated = task_services.update_task(
        task_id,
        {
            "title": "Updated",
            "description": "New desc",
            "duedate": (date.today() + timedelta(days=10)).isoformat() + "Z",
            "status": TaskStatus.COMPLETED.value,
            "priority": "3",
            "notes": "fresh",
            "owner": seed_data["new_owner_email"],
            "collaborators": json.dumps([seed_data["collaborator_email"]]),
            "existing_attachments": json.dumps([
                {"id": attachment_id, "filename": "keep.txt"}
            ]),
        },
        [new_file],
    )

    with app_instance.app_context():
        refreshed = db.session.get(Task, task_id)
        assert refreshed.title == "Updated"
        assert refreshed.status == TaskStatus.COMPLETED
        assert refreshed.owner.email == seed_data["new_owner_email"]
        assert len(refreshed.attachments) == 2

    assert calls["update"], "expected update notification to be recorded"
    assert calls["update_due"] == [task_id]
    assert calls["remove"] == [task_id]
    assert any(rec[2] == seed_data["new_owner_email"] for rec in calls["assignment"])


def test_get_project_users_for_tasks_without_project(app_instance, seed_data, monkeypatch):
    monkeypatch.setattr(task_services, "get_users_info", lambda: ["all"])
    with app_instance.app_context():
        task = Task(
            title="Standalone",
            duedate=date.today(),
            status=TaskStatus.UNASSIGNED,
            owner=db.session.get(User, seed_data["owner_id"]),
        )
        db.session.add(task)
        db.session.commit()
        result = task_services.get_project_users_for_tasks(task.id)
    assert result == ["all"]


def test_link_task_to_project_and_get_unassigned(app_instance, seed_data):
    with app_instance.app_context():
        task = Task(
            title="Loose",
            duedate=date.today(),
            status=TaskStatus.UNASSIGNED,
            owner=db.session.get(User, seed_data["owner_id"]),
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id
        unassigned = task_services.get_unassigned_tasks()
        assert any(t.id == task_id for t in unassigned)

        linked = task_services.link_task_to_project(task_id, seed_data["project_id"])
        assert linked.project_id == seed_data["project_id"]

    project_tasks = task_services.get_project_tasks(seed_data["project_id"])
    assert any(t.id == task_id for t in project_tasks)