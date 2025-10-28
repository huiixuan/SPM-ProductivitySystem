import io
from types import SimpleNamespace

import pytest

from app import create_app
from app.models import db
from app.routes import attachment as attachment_routes
from app.services import attachment_services


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
def client(app_instance):
    return app_instance.test_client()


def test_get_attachment_route_returns_file(client, monkeypatch):
    attachment = SimpleNamespace(filename="doc.pdf", content=b"filedata")
    monkeypatch.setattr(attachment_services, "get_attachment", lambda _id: attachment)

    response = client.get("/api/attachment/get-attachment/1")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data == b"filedata"


def test_get_attachment_route_not_found_returns_404(client, monkeypatch):
    monkeypatch.setattr(attachment_services, "get_attachment", lambda _id: None)

    response = client.get("/api/attachment/get-attachment/99")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Attachment not found."


def test_get_attachment_route_handles_exception(client, monkeypatch):
    monkeypatch.setattr(
        attachment_services,
        "get_attachment",
        lambda _id: (_ for _ in ()).throw(RuntimeError("fail")),
    )

    response = client.get("/api/attachment/get-attachment/1")
    assert response.status_code == 500
    assert response.get_json()["success"] is False


def test_get_attachment_by_task_route_raises_for_missing_return(client, monkeypatch):
    monkeypatch.setattr(attachment_services, "get_attachment_by_task", lambda task_id: [])
    with pytest.raises(TypeError):
        client.get("/api/attachment/get-task-attachments/1")
