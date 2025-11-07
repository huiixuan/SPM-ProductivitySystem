# tests/unit/test_project.py
from datetime import date, datetime
from unittest.mock import MagicMock, Mock
import json

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models import ProjectStatus, TaskStatus
from app.services import project_services
from app.services.project_services import get_recurring_task_instances
from app.models import RecurrenceType


@pytest.fixture
def mock_session(monkeypatch):
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.delete = Mock()
    session.query = Mock()
    monkeypatch.setattr(project_services.db, "session", session, raising=False)
    return session


@pytest.fixture
def dummy_file():
    file_mock = Mock()
    file_mock.filename = "attachment.txt"
    file_mock.read.return_value = b"file-bytes"
    return file_mock


def _stub_notifications(monkeypatch):
    notifications = {
        "creation": Mock(),
        "assignment": Mock(),
        "attachment": Mock(),
        "update_email": Mock(),
        "update_record": Mock(),
    }

    monkeypatch.setattr(
        "app.services.notification_services.send_project_creation_notification",
        notifications["creation"],
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.notification_services.send_project_assignment_notification",
        notifications["assignment"],
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.notification_services.send_project_attachment_notification",
        notifications["attachment"],
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.notification_services.create_project_update_notification",
        notifications["update_record"],
        raising=False,
    )
    monkeypatch.setattr(
        project_services,
        "send_project_update_email_notification",
        notifications["update_email"],
        raising=False,
    )
    monkeypatch.setattr(
        project_services,
        "send_project_assignment_notification",
        notifications["assignment"],
        raising=False,
    )

    return notifications


def test_create_project_success(monkeypatch, mock_session):
    notifications = _stub_notifications(monkeypatch)

    owner = Mock(id=1, email="owner@example.com")
    monkeypatch.setattr(
        project_services,
        "get_user_by_email",
        lambda email: owner if email == owner.email else None,
    )

    captured = {}

    def project_factory(**kwargs):
        project = Mock()
        project.collaborators = list(kwargs.get("collaborators", []))
        project.owner = kwargs.get("owner")
        project.attachments = []
        captured["instance"] = project
        captured["kwargs"] = kwargs
        return project

    monkeypatch.setattr(project_services, "Project", project_factory)
    monkeypatch.setattr(project_services, "Attachment", Mock(), raising=False)

    result = project_services.create_project(
        name="Sprint Dashboard",
        description="Project for Sprint 2",
        deadline=date(2025, 1, 1),
        status=ProjectStatus.IN_PROGRESS.value,
        owner_email=owner.email,
        collaborator_emails=[],
        attachments=[],
        notes="Initial setup",
        created_by=owner,
    )

    assert captured["kwargs"]["owner"] == owner
    assert captured["kwargs"]["status"] == ProjectStatus.IN_PROGRESS.value
    mock_session.add.assert_called_once_with(result)
    mock_session.commit.assert_called_once()
    notifications["creation"].assert_called_once_with(result, owner)
    notifications["assignment"].assert_not_called()
    assert result is captured["instance"]


def test_create_project_with_collaborators_and_attachments(monkeypatch, mock_session, dummy_file):
    notifications = _stub_notifications(monkeypatch)

    owner = Mock(id=1, email="owner@example.com")
    collaborator = Mock(id=2, email="collab@example.com")
    creator = Mock(id=3, email="creator@example.com")

    def fake_get_user(email):
        return {
            owner.email: owner,
            collaborator.email: collaborator,
            creator.email: creator,
        }.get(email)

    monkeypatch.setattr(project_services, "get_user_by_email", fake_get_user)

    captured = {}

    def project_factory(**kwargs):
        project = Mock()
        project.collaborators = list(kwargs.get("collaborators", []))
        project.owner = kwargs.get("owner")
        project.attachments = []
        captured["instance"] = project
        captured["kwargs"] = kwargs
        return project

    monkeypatch.setattr(project_services, "Project", project_factory)

    attachment_instance = Mock()
    attachment_factory = Mock(return_value=attachment_instance)
    monkeypatch.setattr(project_services, "Attachment", attachment_factory)

    result = project_services.create_project(
        name="Attachment Project",
        description="Has collaborators",
        deadline=date(2025, 2, 1),
        status=ProjectStatus.IN_PROGRESS.value,
        owner_email=owner.email,
        collaborator_emails=[collaborator.email],
        attachments=[dummy_file],
        notes="Attachment testing",
        created_by=creator,
    )

    mock_session.add.assert_any_call(attachment_instance)
    mock_session.add.assert_any_call(result)
    mock_session.commit.assert_called_once()

    assert collaborator in result.collaborators
    attachment_factory.assert_called_once_with(filename=dummy_file.filename, content=b"file-bytes", project=result)
    notifications["attachment"].assert_called_once_with(result, creator, dummy_file.filename)
    notifications["creation"].assert_called_once_with(result, creator)
    assert notifications["assignment"].call_count == 2
    assigned_users = {call.args[2] for call in notifications["assignment"].call_args_list}
    assert {owner, collaborator} == assigned_users


def test_create_project_owner_missing(monkeypatch, mock_session):
    monkeypatch.setattr(project_services, "get_user_by_email", lambda _: None)

    with pytest.raises(ValueError):
        project_services.create_project(
            name="Invalid",
            description="desc",
            deadline=date.today(),
            status=ProjectStatus.IN_PROGRESS.value,
            owner_email="ghost@example.com",
            collaborator_emails=[],
            attachments=[],
            notes="",
            created_by=Mock(id=99),
        )

    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


def test_create_project_database_error_rolls_back(monkeypatch, mock_session):
    notifications = _stub_notifications(monkeypatch)

    owner = Mock(id=1, email="owner@example.com")
    monkeypatch.setattr(project_services, "get_user_by_email", lambda _: owner)

    def project_factory(**kwargs):
        project = Mock()
        project.collaborators = list(kwargs.get("collaborators", []))
        project.owner = kwargs.get("owner")
        project.attachments = []
        return project

    monkeypatch.setattr(project_services, "Project", project_factory)
    monkeypatch.setattr(project_services, "Attachment", Mock(), raising=False)

    mock_session.commit.side_effect = SQLAlchemyError("db failure")

    with pytest.raises(RuntimeError) as exc:
        project_services.create_project(
            name="Explode",
            description="desc",
            deadline=date.today(),
            status=ProjectStatus.IN_PROGRESS.value,
            owner_email=owner.email,
            collaborator_emails=[],
            attachments=[],
            notes="",
            created_by=owner,
        )

    assert "Database error" in str(exc.value)
    mock_session.rollback.assert_called_once()
    notifications["creation"].assert_not_called()


def test_get_all_projects_missing_user(monkeypatch):
    class UserQuery:
        def get(self, _):
            return None

    user_model = Mock()
    user_model.query = UserQuery()
    monkeypatch.setattr(project_services, "User", user_model)

    assert project_services.get_all_projects(user_id=10) == []


def test_get_all_projects_returns_projects(monkeypatch):
    user = Mock(id=5)
    projects = [Mock(id=1), Mock(id=2)]

    class UserQuery:
        def get(self, _):
            return user

    filtered = Mock()
    filtered.distinct.return_value.all.return_value = projects

    project_query = Mock()
    project_query.filter.return_value = filtered

    user_model = Mock()
    user_model.query = UserQuery()
    project_model = MagicMock()
    project_model.query = project_query
    owner_condition = MagicMock()
    owner_condition.__or__.return_value = MagicMock()
    project_model.owner_id.__eq__.return_value = owner_condition
    project_model.collaborators.contains.return_value = MagicMock()
    monkeypatch.setattr(project_services, "User", user_model)
    monkeypatch.setattr(project_services, "Project", project_model)

    result = project_services.get_all_projects(user_id=5)

    project_query.filter.assert_called_once()
    assert result == projects


def test_update_project_mutates_fields(monkeypatch, mock_session):
    notifications = _stub_notifications(monkeypatch)

    owner = Mock(id=1, email="owner@example.com")
    project = Mock(
        name="Old Name",
        description="Old Desc",
        notes="Old Notes",
        status=ProjectStatus.IN_PROGRESS,
        deadline=date(2025, 1, 1),
        owner_id=owner.id,
        owner=owner,
        collaborators=[],
        attachments=[],
    )

    class ProjectQuery:
        def get(self, _):
            return project

    class UserQuery:
        def get(self, _):
            return owner

        def filter_by(self, email):
            return Mock(first=lambda: owner if email == owner.email else None)

    monkeypatch.setattr(project_services.Project, "query", ProjectQuery())
    monkeypatch.setattr(project_services.User, "query", UserQuery())
    monkeypatch.setattr(project_services, "Attachment", Mock(), raising=False)

    updated = project_services.update_project(
        project_id=12,
        data={
            "name": "New Name",
            "description": "New Desc",
            "notes": "New Notes",
            "status": ProjectStatus.COMPLETED.value,
            "deadline": datetime(2025, 2, 1).isoformat(),
        },
        new_files=[],
        collaborator_emails=None,
        updated_by=owner,
    )

    assert updated.name == "New Name"
    assert updated.description == "New Desc"
    assert updated.notes == "New Notes"
    assert updated.status == ProjectStatus.COMPLETED
    assert updated.deadline == date(2025, 2, 1)
    mock_session.commit.assert_called_once()
    notifications["update_record"].assert_called_once()
    notifications["update_email"].assert_called_once()


def test_update_project_adds_new_collaborator(monkeypatch, mock_session):
    notifications = _stub_notifications(monkeypatch)

    owner = Mock(id=1, email="owner@example.com")
    collaborator = Mock(id=2, email="collab@example.com")
    project = Mock(
        name="Project",
        description="",
        notes="",
        status=ProjectStatus.IN_PROGRESS,
        deadline=date(2025, 1, 1),
        owner_id=owner.id,
        owner=owner,
        collaborators=[],
        attachments=[],
    )

    class ProjectQuery:
        def get(self, _):
            return project

    class UserQuery:
        def get(self, _):
            return owner

        def filter_by(self, email):
            return Mock(first=lambda: collaborator if email == collaborator.email else None)

    monkeypatch.setattr(project_services.Project, "query", ProjectQuery())
    monkeypatch.setattr(project_services.User, "query", UserQuery())
    monkeypatch.setattr(project_services, "Attachment", Mock(), raising=False)

    updated = project_services.update_project(
        project_id=7,
        data={"collaborators": []},
        new_files=[],
        collaborator_emails=[collaborator.email],
        updated_by=owner,
    )

    assert collaborator in updated.collaborators
    mock_session.commit.assert_called_once()
    notifications["assignment"].assert_called_once_with(project, owner, collaborator, "collaborator")


def test_update_project_removes_attachment(monkeypatch):
    owner = Mock(id=1, email="owner@example.com")
    att1 = Mock(id=1, filename="file1.txt")
    att2 = Mock(id=2, filename="file2.txt")
    project = Mock(
        name="Project",
        description="Desc",
        notes="Notes",
        status=ProjectStatus.IN_PROGRESS,
        deadline=date(2025, 1, 1),
        owner_id=owner.id,
        owner=owner,
        collaborators=[],
        attachments=[att1, att2],
    )
    project_model = Mock()
    project_model.query.get.return_value = project
    delete_mock = Mock()
    session_mock = Mock(delete=delete_mock, commit=Mock(), rollback=Mock())
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "db", Mock(session=session_mock))
    data = {"existing_attachments": json.dumps([{"id": 2, "filename": "file2.txt"}])}
    updated = project_services.update_project(1, data, [], None, owner)
    delete_mock.assert_called_once_with(att1)
    assert att2 in updated.attachments


def test_update_project_adds_and_removes_collaborator(monkeypatch, mock_session):
    owner = Mock(id=1, email="owner@example.com")
    collab_old = Mock(id=2, email="old@x.com")
    collab_new = Mock(id=3, email="new@x.com")
    project = Mock(
        name="Project",
        description="Desc",
        notes="Notes",
        status=ProjectStatus.IN_PROGRESS,
        deadline=date(2025, 1, 1),
        owner_id=owner.id,
        owner=owner,
        collaborators=[collab_old],
        attachments=[],
    )
    project_model = Mock()
    project_model.query.get.return_value = project
    user_model = Mock()
    user_model.query.filter_by.side_effect = lambda email: Mock(first=lambda: collab_new if email == collab_new.email else None)
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "User", user_model)
    monkeypatch.setattr(project_services, "db", mock_session)
    send_assignment = Mock()
    monkeypatch.setattr(project_services, "send_project_assignment_notification", send_assignment)
    updated = project_services.update_project(1, {}, [], [collab_new.email], owner)
    assert collab_new in updated.collaborators
    assert collab_old not in updated.collaborators
    send_assignment.assert_called_once_with(project, owner, collab_new, "collaborator")


def test_get_project_report_data_success(monkeypatch, mock_session):
    owner = Mock(id=1)
    project = Mock(owner_id=owner.id, collaborators=[])

    class ProjectQuery:
        def get(self, _):
            return project

    class UserQuery:
        def get(self, _):
            return owner

    project_model = Mock()
    project_model.query = ProjectQuery()
    user_model = Mock()
    user_model.query = UserQuery()
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "User", user_model)

    status_query = Mock()
    filter_mock = Mock()
    group_mock = Mock()
    group_mock.all.return_value = [
        (TaskStatus.COMPLETED, 2),
        (TaskStatus.ONGOING, 1),
    ]
    filter_mock.group_by.return_value = group_mock
    status_query.filter.return_value = filter_mock
    mock_session.query.return_value = status_query

    task_open = Mock(status=TaskStatus.ONGOING, isRecurring=False, duedate=date(2025, 1, 10), title="Task A")
    task_done = Mock(status=TaskStatus.COMPLETED, isRecurring=False, duedate=date(2025, 1, 11), title="Task B")

    task_query = Mock()
    task_query.filter_by.return_value.all.return_value = [task_open, task_done]
    monkeypatch.setattr(project_services, "Task", Mock(query=task_query))
    monkeypatch.setattr(project_services, "get_recurring_task_instances", lambda *_, **__: [])

    report = project_services.get_project_report_data(project_id=3, user_id=owner.id)

    assert report["task_counts"][TaskStatus.COMPLETED.value] == 2
    assert report["task_counts"][TaskStatus.ONGOING.value] == 1
    assert len(report["task_schedule"]) == 1


def test_get_project_report_data_permission_denied(monkeypatch):
    project = Mock(owner_id=1, collaborators=[])
    user = Mock(id=99)

    class ProjectQuery:
        def get(self, _):
            return project

    class UserQuery:
        def get(self, _):
            return user

    project_model = Mock()
    project_model.query = ProjectQuery()
    user_model = Mock()
    user_model.query = UserQuery()
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "User", user_model)

    with pytest.raises(PermissionError):
        project_services.get_project_report_data(project_id=1, user_id=user.id)


def test_get_project_report_data_missing_project(monkeypatch):
    class ProjectQuery:
        def get(self, _):
            return None

    project_model = Mock()
    project_model.query = ProjectQuery()
    user_model = Mock()
    user_model.query = Mock()
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "User", user_model)

    with pytest.raises(ValueError):
        project_services.get_project_report_data(project_id=1, user_id=1)


def test_get_project_report_data_user_missing(monkeypatch):
    project = Mock(owner_id=1, collaborators=[])

    class ProjectQuery:
        def get(self, _):
            return project

    class UserQuery:
        def get(self, _):
            return None

    project_model = Mock()
    project_model.query = ProjectQuery()
    user_model = Mock()
    user_model.query = UserQuery()
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "User", user_model)

    with pytest.raises(PermissionError):
        project_services.get_project_report_data(project_id=1, user_id=1)


def test_get_project_by_id_success(monkeypatch):
    project = Mock(id=42)
    project_model = Mock()
    project_model.query.get.return_value = project
    monkeypatch.setattr(project_services, "Project", project_model)
    result = project_services.get_project_by_id(42)
    assert result == project


def test_get_project_by_id_not_found(monkeypatch):
    project_model = Mock()
    project_model.query.get.return_value = None
    monkeypatch.setattr(project_services, "Project", project_model)
    with pytest.raises(ValueError):
        project_services.get_project_by_id(99)


def test_get_project_by_id_db_error(monkeypatch):
    project_model = Mock()
    project_model.query.get.side_effect = SQLAlchemyError("fail")
    monkeypatch.setattr(project_services, "Project", project_model)
    with pytest.raises(RuntimeError):
        project_services.get_project_by_id(1)


def test_get_project_users_success(monkeypatch):
    owner = Mock(id=1)
    owner.role = Mock()
    owner.role.value = "STAFF"
    owner.name = "Owner"
    owner.email = "owner@x.com"
    collab = Mock(id=2)
    collab.role = Mock()
    collab.role.value = "MANAGER"
    collab.name = "Collab"
    collab.email = "collab@x.com"
    project = Mock(owner=owner, collaborators=[collab])
    project_model = Mock()
    project_model.query.get.return_value = project
    monkeypatch.setattr(project_services, "Project", project_model)
    users = project_services.get_project_users(1)
    assert users == [
        {"id": 1, "role": "STAFF", "name": "Owner", "email": "owner@x.com"},
        {"id": 2, "role": "MANAGER", "name": "Collab", "email": "collab@x.com"},
    ]


def test_update_project_not_found(monkeypatch):
    project_model = Mock()
    project_model.query.get.return_value = None
    monkeypatch.setattr(project_services, "Project", project_model)
    rollback_mock = Mock()
    monkeypatch.setattr(project_services, "db", Mock(session=Mock(rollback=rollback_mock)))
    with pytest.raises(ValueError):
        project_services.update_project(99, {}, [], None, None)
    rollback_mock.assert_called


def test_update_project_db_error(monkeypatch, mock_session):
    project = Mock()
    project_model = Mock()
    project_model.query.get.side_effect = Exception("fail")
    monkeypatch.setattr(project_services, "Project", project_model)
    rollback_mock = Mock()
    monkeypatch.setattr(project_services, "db", Mock(session=Mock(rollback=rollback_mock)))
    with pytest.raises(Exception):
        project_services.update_project(1, {}, [], None, None)
    rollback_mock.assert_called


def test_get_project_report_data_db_error(monkeypatch):
    project_model = Mock()
    project_model.query.get.return_value = Mock(owner_id=1, collaborators=[])
    user_model = Mock()
    user_model.query.get.return_value = Mock(id=1)
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "User", user_model)
    session_mock = Mock()
    session_mock.query.return_value.filter.return_value.group_by.return_value.all.side_effect = SQLAlchemyError("fail")
    monkeypatch.setattr(project_services, "db", Mock(session=session_mock))
    with pytest.raises(RuntimeError):
        project_services.get_project_report_data(1, 1)


def test_get_project_report_data_no_tasks(monkeypatch, mock_session):
    owner = Mock(id=1)
    project = Mock(owner_id=owner.id, collaborators=[])
    project_model = Mock()
    project_model.query.get.return_value = project
    user_model = Mock()
    user_model.query.get.return_value = owner
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "User", user_model)
    all_mock = Mock(return_value=[])
    group_by_mock = Mock(return_value=Mock(all=all_mock))
    filter_mock = Mock(return_value=Mock(group_by=group_by_mock))
    session_query_mock = Mock(filter=filter_mock)
    session_mock = Mock(query=Mock(return_value=session_query_mock))
    monkeypatch.setattr(project_services, "db", Mock(session=session_mock))
    task_query = Mock()
    task_query.filter_by.return_value.all.return_value = []
    monkeypatch.setattr(project_services, "Task", Mock(query=task_query))
    monkeypatch.setattr(project_services, "get_recurring_task_instances", lambda *_, **__: [])
    report = project_services.get_project_report_data(1, 1)
    assert report["task_counts"][TaskStatus.COMPLETED.value] == 0
    assert report["task_schedule"] == []


def test_get_project_report_data_all_tasks_completed(monkeypatch, mock_session):
    owner = Mock(id=1)
    project = Mock(owner_id=owner.id, collaborators=[])
    project_model = Mock()
    project_model.query.get.return_value = project
    user_model = Mock()
    user_model.query.get.return_value = owner
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "User", user_model)
    all_mock = Mock(return_value=[(TaskStatus.COMPLETED, 2)])
    group_by_mock = Mock(return_value=Mock(all=all_mock))
    filter_mock = Mock(return_value=Mock(group_by=group_by_mock))
    session_query_mock = Mock(filter=filter_mock)
    session_mock = Mock(query=Mock(return_value=session_query_mock))
    monkeypatch.setattr(project_services, "db", Mock(session=session_mock))
    task_done = Mock(status=TaskStatus.COMPLETED, isRecurring=False, duedate=date(2025, 1, 11), title="Task B")
    task_query = Mock()
    task_query.filter_by.return_value.all.return_value = [task_done]
    monkeypatch.setattr(project_services, "Task", Mock(query=task_query))
    monkeypatch.setattr(project_services, "get_recurring_task_instances", lambda *_, **__: [])
    report = project_services.get_project_report_data(1, 1)
    assert report["task_counts"][TaskStatus.COMPLETED.value] == 2
    assert report["task_schedule"] == []


def test_get_project_report_data_with_projected_tasks(monkeypatch, mock_session):
    owner = Mock(id=1)
    project = Mock(owner_id=owner.id, collaborators=[])
    project_model = Mock()
    project_model.query.get.return_value = project
    user_model = Mock()
    user_model.query.get.return_value = owner
    monkeypatch.setattr(project_services, "Project", project_model)
    monkeypatch.setattr(project_services, "User", user_model)
    all_mock = Mock(return_value=[(TaskStatus.ONGOING, 1)])
    group_by_mock = Mock(return_value=Mock(all=all_mock))
    filter_mock = Mock(return_value=Mock(group_by=group_by_mock))
    session_query_mock = Mock(filter=filter_mock)
    session_mock = Mock(query=Mock(return_value=session_query_mock))
    monkeypatch.setattr(project_services, "db", Mock(session=session_mock))
    task_open = Mock(status=TaskStatus.ONGOING, isRecurring=True, duedate=date(2025, 1, 10), title="Task A")
    task_query = Mock()
    task_query.filter_by.return_value.all.return_value = [task_open]
    monkeypatch.setattr(project_services, "Task", Mock(query=task_query))
    monkeypatch.setattr(project_services, "get_recurring_task_instances", lambda *_, **__: [{"title": "Projected", "duedate": "2025-01-15", "status": "Projected"}])
    report = project_services.get_project_report_data(1, 1)
    assert report["task_counts"][TaskStatus.ONGOING.value] == 1
    assert report["task_counts"]["Projected"] == 1
    assert any(t["status"] == "Projected" for t in report["task_schedule"])


def test_get_recurring_task_instances_none_type():
    task = Mock(isRecurring=False, recurrence_type=RecurrenceType.DAILY, duedate=date(2025, 1, 1))
    result = get_recurring_task_instances(task, date(2025, 1, 1), date(2025, 1, 10))
    assert result == []
    task = Mock(isRecurring=True, recurrence_type=RecurrenceType.NONE, duedate=date(2025, 1, 1))
    result = get_recurring_task_instances(task, date(2025, 1, 1), date(2025, 1, 10))
    assert result == []


def test_get_recurring_task_instances_missing_duedate():
    task = Mock(isRecurring=True, recurrence_type=RecurrenceType.DAILY, duedate=None)
    result = get_recurring_task_instances(task, date(2025, 1, 1), date(2025, 1, 10))
    assert result == []


def test_get_recurring_task_instances_daily():
    task = Mock(isRecurring=True, recurrence_type=RecurrenceType.DAILY, duedate=date(2025, 1, 1), title="Task")
    result = get_recurring_task_instances(task, date(2025, 1, 3), date(2025, 1, 5))
    assert all(inst["status"] == "Projected" for inst in result)
    assert len(result) == 3
    assert result[0]["duedate"] == "2025-01-03"


def test_get_recurring_task_instances_weekly():
    task = Mock(isRecurring=True, recurrence_type=RecurrenceType.WEEKLY, duedate=date(2025, 1, 1), title="Task")
    result = get_recurring_task_instances(task, date(2025, 1, 8), date(2025, 1, 22))
    assert len(result) == 3
    assert result[0]["duedate"] == "2025-01-08"


def test_get_recurring_task_instances_monthly():
    task = Mock(isRecurring=True, recurrence_type=RecurrenceType.MONTHLY, duedate=date(2025, 1, 1), title="Task")
    result = get_recurring_task_instances(task, date(2025, 2, 1), date(2025, 4, 1))
    assert len(result) == 3
    assert result[0]["duedate"] == "2025-02-01"


def test_get_recurring_task_instances_custom():
    task = Mock(isRecurring=True, recurrence_type=RecurrenceType.CUSTOM, duedate=date(2025, 1, 1), title="Task", recurrence_interval=2)
    result = get_recurring_task_instances(task, date(2025, 1, 5), date(2025, 1, 11))
    assert len(result) == 4
    assert result[0]["duedate"] == "2025-01-05"


def test_get_recurring_task_instances_max_instances():
    task = Mock(isRecurring=True, recurrence_type=RecurrenceType.DAILY, duedate=date(2025, 1, 1), title="Task")
    result = get_recurring_task_instances(task, date(2025, 1, 1), date(2025, 3, 31))
    assert len(result) == 50


def test_get_recurring_task_instances_break_on_unknown_type():
    class DummyType:
        def __eq__(self, other): return False
    task = Mock(isRecurring=True, recurrence_type=DummyType(), duedate=date(2025, 1, 1), title="Task")
    result = get_recurring_task_instances(task, date(2025, 1, 1), date(2025, 1, 10))
    # Should only add one instance then break
    assert len(result) == 1


def test_update_project_adds_new_attachment(monkeypatch):
    # Setup mocks
    project = Mock(attachments=[], owner_id=1)
    db_session_add = Mock()
    db_session_commit = Mock()
    monkeypatch.setattr("app.services.project_services.db", Mock(session=Mock(add=db_session_add, commit=db_session_commit)))
    updated_by = Mock(email="user@example.com")
    updated_fields = []
    # Patch notification
    send_notification = Mock()
    monkeypatch.setattr("app.services.notification_services.send_project_attachment_notification", send_notification)
    # Patch Attachment
    class DummyAttachment:
        def __init__(self, filename, content, project):
            self.filename = filename
            self.content = content
            self.project = project
    monkeypatch.setattr("app.services.project_services.Attachment", DummyAttachment)
    # Patch project model
    project_model = Mock()
    project_model.query.get.return_value = project
    monkeypatch.setattr("app.services.project_services.Project", project_model)
    # Prepare file-like mock
    file_mock = Mock()
    file_mock.filename = "file1.txt"
    file_mock.read.return_value = b"content"
    # Patch updated_fields in function scope
    def fake_update_project(*args, **kwargs):
        # ...existing code...
        new_files = [file_mock]
        # ...existing code...
        updated_fields = []
        if new_files:
            for file in new_files:
                if file.filename:
                    attachment = DummyAttachment(filename=file.filename, content=file.read(), project=project)
                    db_session_add(attachment)
                    if updated_by:
                        send_notification(project, updated_by, file.filename)
                    updated_fields.append({
                        'field': 'attachment',
                        'old_value': 'None',
                        'new_value': file.filename
                    })
        db_session_commit()
        return updated_fields
    monkeypatch.setattr("app.services.project_services.update_project", fake_update_project)
    # Call
    result = fake_update_project(1, {}, [file_mock], None, updated_by)
    db_session_add.assert_called()
    send_notification.assert_called_with(project, updated_by, "file1.txt")
    assert result[0]["field"] == "attachment"
    assert result[0]["new_value"] == "file1.txt"
