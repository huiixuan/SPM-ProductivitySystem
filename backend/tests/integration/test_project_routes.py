import io
from types import SimpleNamespace

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.models import db
from app.routes import project as project_routes
from app.services import project_services
from app.models import ProjectStatus


@pytest.fixture
def app_instance():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JWT_SECRET_KEY": "project-secret",
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
def auth_headers(app_instance):
    with app_instance.app_context():
        token = create_access_token(identity="1")
    return {"Authorization": f"Bearer {token}"}


def test_create_project_route_success(client, auth_headers, monkeypatch):
    created_project = SimpleNamespace(id=123)

    def fake_create(**kwargs):  # noqa: ANN001
        return created_project

    monkeypatch.setattr(project_services, "create_project", fake_create)

    response = client.post(
        "/api/project/create-project",
        data={
            "name": "Project X",
            "description": "Desc",
            "deadline": "2025-01-01T00:00:00",
            "status": ProjectStatus.IN_PROGRESS.value,
            "owner": "owner@example.com",
            "collaborators": "member@example.com",
            "notes": "Important",
        },
        headers=auth_headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["project_id"] == 123


def test_create_project_route_handles_exception(client, auth_headers, monkeypatch):
    def raise_error(**_):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(project_services, "create_project", raise_error)

    response = client.post(
        "/api/project/create-project",
        data={"owner": "owner@example.com"},
        headers=auth_headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.get_json()["success"] is False


def test_get_all_projects_route_returns_serialized_projects(client, auth_headers, monkeypatch):
    project_obj = SimpleNamespace(to_dict=lambda: {"id": 1, "name": "Proj"})
    monkeypatch.setattr(project_services, "get_all_projects", lambda user_id: [project_obj])
    monkeypatch.setattr(project_routes, "get_jwt_identity", lambda: "1")

    response = client.get("/api/project/get-all-projects", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json() == [{"id": 1, "name": "Proj"}]


def test_get_all_projects_route_requires_user_identity(client, auth_headers, monkeypatch):
    monkeypatch.setattr(project_routes, "get_jwt_identity", lambda: None)

    response = client.get("/api/project/get-all-projects", headers=auth_headers)
    assert response.status_code == 401
    assert response.get_json()["error"] == "User not found or not logged in"


def test_get_project_route_success(client, auth_headers, monkeypatch):
    project_obj = SimpleNamespace(to_dict=lambda: {"id": 55, "name": "Detail"})
    monkeypatch.setattr(project_services, "get_project_by_id", lambda _: project_obj)

    response = client.get("/api/project/get-project/55", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["name"] == "Detail"


def test_get_project_route_catches_exception(client, auth_headers, monkeypatch):
    monkeypatch.setattr(project_services, "get_project_by_id", lambda _: (_ for _ in ()).throw(RuntimeError("fail")))

    response = client.get("/api/project/get-project/1", headers=auth_headers)
    assert response.status_code == 500
    assert response.get_json()["success"] is False


def test_get_project_users_route_success(client, auth_headers, monkeypatch):
    monkeypatch.setattr(project_services, "get_project_users", lambda _: [{"email": "user@example.com"}])

    response = client.get("/api/project/get-project-users/10", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json() == [{"email": "user@example.com"}]


def test_update_project_route_success(client, auth_headers, monkeypatch):
    project_obj = SimpleNamespace(to_dict=lambda: {"id": 99, "name": "Updated"})
    monkeypatch.setattr(project_services, "update_project", lambda *args, **kwargs: project_obj)

    response = client.put(
        "/api/project/update-project/99",
        data={"name": "Updated", "collaborators": "member@example.com"},
        headers=auth_headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["project"]["name"] == "Updated"


def test_update_project_route_handles_exception(client, auth_headers, monkeypatch):
    monkeypatch.setattr(project_services, "update_project", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))

    response = client.put(
        "/api/project/update-project/1",
        data={},
        headers=auth_headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.get_json()["success"] is False
