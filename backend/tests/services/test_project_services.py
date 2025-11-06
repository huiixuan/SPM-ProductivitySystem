import io
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.models import (
    db,
    User,
    Project,
    Attachment,
    ProjectStatus,
)
from app.services.project_services import (
    create_project,
    get_all_projects,
    get_project_by_id,
    get_project_users,
    update_project,
)


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
def session(app_instance):
    with app_instance.app_context():
        yield db.session


def make_user(email: str, name: str = "User") -> User:
    user = User(email=email, name=name, role="STAFF")
    user.set_password("password")
    return user



def test_create_project_with_collaborators(session, app_instance):
    with app_instance.app_context():
        owner = make_user("owner@example.com")
        collaborator = make_user("collab@example.com")
        created_by = make_user("creator@example.com")
        db.session.add_all([owner, collaborator, created_by])
        db.session.commit()

        with patch('flask_jwt_extended.get_jwt_identity', return_value=created_by.id), \
             patch('app.services.project_services.send_project_creation_email_notification') as mock_email, \
             patch('app.services.project_services.send_project_collaborator_added_email_notification') as mock_collab_email:
            project = create_project(
                name="Launch",
                description="New project",
                deadline=date(2025, 5, 1),
                status=ProjectStatus.IN_PROGRESS,
                owner_email=owner.email,
                collaborator_emails=[collaborator.email],
                attachments=None,
                notes="Important notes",
                created_by=created_by  
            )

            mock_email.assert_called_once()

        assert project.id is not None
        assert project.collaborators == [collaborator]
        assert project.notes == "Important notes"


def test_create_project_missing_owner_raises_value_error(app_instance):
    with app_instance.app_context():
        created_by = make_user("creator@example.com")
        db.session.add(created_by)
        db.session.commit()
        
        with pytest.raises(ValueError):
            create_project(
                name="Missing Owner",
                description="",
                deadline=None,
                status=ProjectStatus.NOT_STARTED,
                owner_email="ghost@example.com",
                collaborator_emails=[],
                attachments=None,
                notes=None,
                created_by=created_by 
            )


def test_create_project_database_error_rolls_back(monkeypatch, app_instance):
    with app_instance.app_context():
        owner = make_user("owner2@example.com")
        created_by = make_user("creator@example.com")
        db.session.add_all([owner, created_by])
        db.session.commit()

        original_commit = db.session.commit

        def raise_error():
            raise SQLAlchemyError("boom")

        monkeypatch.setattr(db.session, "commit", raise_error)

        with pytest.raises(RuntimeError, match="Database error while creating project"):
            create_project(
                name="Error Project",
                description="",
                deadline=None,
                status=ProjectStatus.NOT_STARTED,
                owner_email=owner.email,
                collaborator_emails=None,
                attachments=None,
                notes=None,
                created_by=created_by 
            )

        monkeypatch.setattr(db.session, "commit", original_commit)


def test_get_all_projects_includes_owned_and_collaborated(app_instance):
    with app_instance.app_context():
        owner = make_user("owner3@example.com")
        collaborator = make_user("collab3@example.com")
        other = make_user("other@example.com")
        db.session.add_all([owner, collaborator, other])

        owned = Project(name="Owned", owner=owner, status=ProjectStatus.IN_PROGRESS)
        collaborated = Project(name="Collaborated", owner=other)
        collaborated.collaborators.append(owner)
        unrelated = Project(name="Unrelated", owner=other)

        db.session.add_all([owned, collaborated, unrelated])
        db.session.commit()

        results = get_all_projects(owner.id)
        names = sorted(p.name for p in results)
        assert names == ["Collaborated", "Owned"]


def test_get_all_projects_returns_empty_when_user_missing(app_instance):
    with app_instance.app_context():
        assert get_all_projects(999) == []


def test_get_project_by_id_missing_raises_value_error(app_instance):
    with app_instance.app_context():
        with pytest.raises(ValueError):
            get_project_by_id(100)


def test_get_project_users_returns_owner_and_collaborators(app_instance):
    with app_instance.app_context():
        owner = make_user("owner4@example.com", name="Owner")
        collaborator = make_user("collab4@example.com", name="Collab")
        db.session.add_all([owner, collaborator])
        project = Project(name="Team", owner=owner)
        project.collaborators.append(collaborator)
        db.session.add(project)
        db.session.commit()

        users = get_project_users(project.id)
        assert {u["email"] for u in users} == {owner.email, collaborator.email}


def test_update_project_changes_core_fields_and_collaborators(app_instance):
    with app_instance.app_context():
        owner = make_user("owner5@example.com", name="Owner Five")
        new_owner = make_user("new-owner@example.com", name="New Owner")
        collaborator = make_user("collab5@example.com", name="Collaborator")
        db.session.add_all([owner, new_owner, collaborator])

        project = Project(
            name="Original",
            description="Desc",
            notes="Notes",
            status=ProjectStatus.NOT_STARTED,
            owner=owner,
            deadline=date(2025, 1, 1),
        )
        db.session.add(project)
        db.session.commit()

        data = {
            "name": "Updated",
            "description": "Updated desc",
            "notes": "Updated notes",
            "status": ProjectStatus.COMPLETED.value,
            "deadline": "2026-02-03T00:00:00Z",
            "owner": new_owner.email,
            "existing_attachments": "[]",
        }

        with patch("flask_jwt_extended.get_jwt_identity", return_value=owner.id), \
             patch("app.services.project_services.send_project_update_email_notification"), \
             patch("app.services.project_services.send_project_collaborator_added_email_notification"):
            updated = update_project(
                project.id,
                data,
                new_files=[],
                collaborator_emails=[collaborator.email],
                updated_by=owner 
            )

        assert updated.name == "Updated"
        assert updated.owner == new_owner
        assert updated.status == ProjectStatus.COMPLETED
        assert len(updated.collaborators) == 1
        assert updated.collaborators[0].email == collaborator.email
        assert {att.filename for att in updated.attachments} == set()


def test_update_project_invalid_status_raises_value_error(app_instance):
    with app_instance.app_context():
        owner = make_user("owner6@example.com")
        project = Project(name="Invalid", owner=owner)
        db.session.add_all([owner, project])
        db.session.commit()

        with pytest.raises(ValueError):
            update_project(
                project.id,
                {"status": "NOT_A_REAL_STATUS"},
                new_files=[],
                collaborator_emails=[],
                updated_by=owner 
            )