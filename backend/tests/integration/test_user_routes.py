import pytest

from app import create_app
from app.models import db


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


def test_get_all_users_route_returns_data(client, monkeypatch):
    monkeypatch.setattr("app.routes.user.get_users_info", lambda: [{"email": "user@example.com"}])
    response = client.get("/api/user/get-all-users")
    assert response.status_code == 200
    assert response.get_json() == [{"email": "user@example.com"}]


def test_get_all_users_route_handles_exception(client, monkeypatch):
    def raise_error():
        raise RuntimeError("fail")

    monkeypatch.setattr("app.routes.user.get_users_info", raise_error)
    response = client.get("/api/user/get-all-users")
    assert response.status_code == 500
    assert response.get_json()["success"] is False
