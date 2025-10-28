from datetime import date

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.models import db, Attachment, Task, User, TaskStatus
from app.services import attachment_services
from app.services.attachment_services import get_attachment, get_attachment_by_task


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


def test_get_attachment_returns_instance(app_instance):
    with app_instance.app_context():
        owner = User(name="Owner", email="attachment-owner@example.com", role="STAFF")
        owner.set_password("password")
        task = Task(title="T", status=TaskStatus.UNASSIGNED, owner=owner, duedate=date.today())
        db.session.add_all([owner, task])
        db.session.flush()
        attachment = Attachment(filename="file.txt", content=b"data", task=task)
        db.session.add(attachment)
        db.session.commit()

        retrieved = get_attachment(attachment.id)
        assert retrieved.filename == "file.txt"


def test_get_attachment_not_found_raises_value_error(app_instance):
    with app_instance.app_context():
        with pytest.raises(ValueError):
            get_attachment(99)


def test_get_attachment_database_error_translates_to_runtime_error(monkeypatch, app_instance):
    with app_instance.app_context():
        class FailingQuery:
            def get(self, *_args, **_kwargs):
                raise SQLAlchemyError("db failure")

        monkeypatch.setattr(attachment_services.Attachment, "query", FailingQuery())

        with pytest.raises(RuntimeError, match="Database error while retrieving attachment"):
            get_attachment(1)


def test_get_attachment_by_task_returns_list(app_instance):
    with app_instance.app_context():
        owner = User(name="Owner", email="owner2@example.com", role="STAFF")
        owner.set_password("password")
        task = Task(title="Task", status=TaskStatus.UNASSIGNED, owner=owner, duedate=date.today())
        db.session.add_all([owner, task])
        db.session.flush()
        a1 = Attachment(filename="file1", content=b"1", task=task)
        a2 = Attachment(filename="file2", content=b"2", task=task)
        db.session.add_all([a1, a2])
        db.session.commit()

        attachments = get_attachment_by_task(task.id)
        assert {att.filename for att in attachments} == {"file1", "file2"}
