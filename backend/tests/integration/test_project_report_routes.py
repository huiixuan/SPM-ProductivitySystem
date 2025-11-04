from datetime import date, datetime

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.models import db, User, Project, Task, TaskStatus, ProjectStatus


@pytest.fixture
def app_instance():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JWT_SECRET_KEY": "report-secret",
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
def seed_project_with_tasks(app_instance):
    with app_instance.app_context():
        owner = User(name="Owner", email="owner@example.com", role="STAFF")
        owner.set_password("password")
        collab = User(name="Collab", email="collab@example.com", role="STAFF")
        collab.set_password("password")
        outsider = User(name="Out", email="out@example.com", role="STAFF")
        outsider.set_password("password")

        project = Project(
            name="Alpha",
            description="Demo",
            deadline=date.today(),
            status=ProjectStatus.NOT_STARTED,
            owner=owner,
        )
        project.collaborators.append(collab)

        db.session.add_all([owner, collab, outsider, project])
        db.session.commit()

        # Create tasks in different statuses
        tasks = [
            Task(title="T1", duedate=date.today(), status=TaskStatus.UNASSIGNED, owner=owner, project=project, priority=1),
            Task(title="T2", duedate=date.today(), status=TaskStatus.ONGOING, owner=owner, project=project, priority=1),
            Task(title="T3", duedate=date.today(), status=TaskStatus.PENDING_REVIEW, owner=owner, project=project, priority=1),
            Task(title="T4", duedate=date.today(), status=TaskStatus.COMPLETED, owner=owner, project=project, priority=1),
            Task(title="T5", duedate=date.today(), status=TaskStatus.ONGOING, owner=owner, project=project, priority=1),
        ]
        db.session.add_all(tasks)
        db.session.commit()

        return {
            "project_id": project.id,
            "owner_id": owner.id,
            "collab_id": collab.id,
            "outsider_id": outsider.id,
            "project_name": project.name,
            "counts": {
                TaskStatus.UNASSIGNED.value: 1,
                TaskStatus.ONGOING.value: 2,
                TaskStatus.PENDING_REVIEW.value: 1,
                TaskStatus.COMPLETED.value: 1,
            },
        }


@pytest.fixture
def owner_headers(app_instance, seed_project_with_tasks):
    with app_instance.app_context():
        token = create_access_token(identity=str(seed_project_with_tasks["owner_id"]))
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def collab_headers(app_instance, seed_project_with_tasks):
    with app_instance.app_context():
        token = create_access_token(identity=str(seed_project_with_tasks["collab_id"]))
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def outsider_headers(app_instance, seed_project_with_tasks):
    with app_instance.app_context():
        token = create_access_token(identity=str(seed_project_with_tasks["outsider_id"]))
        return {"Authorization": f"Bearer {token}"}


def test_generate_report_allowed_for_collaborator(client, collab_headers, seed_project_with_tasks):
    project_id = seed_project_with_tasks["project_id"]
    resp = client.get(f"/api/project/get-report-data/{project_id}", headers=collab_headers)
    assert resp.status_code == 200


def test_generate_report_forbidden_for_non_member(client, outsider_headers, seed_project_with_tasks):
    project_id = seed_project_with_tasks["project_id"]
    resp = client.get(f"/api/project/get-report-data/{project_id}", headers=outsider_headers)
    assert resp.status_code == 403


def test_generate_report_project_not_found(client, owner_headers):
    resp = client.get("/api/project/get-report-data/9999", headers=owner_headers)
    # Could be 404 from route handler
    assert resp.status_code in (404, 500)
